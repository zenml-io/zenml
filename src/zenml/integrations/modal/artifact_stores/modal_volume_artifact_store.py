#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Mounted fast-path implementation for Modal Volume artifact stores."""

import glob as glob_module
import os
import posixpath
import shutil
import tempfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    cast,
)

from zenml.artifact_stores import BaseArtifactStore
from zenml.artifact_stores.base_artifact_store import PathType
from zenml.constants import handle_bool_env_var
from zenml.integrations.modal import (
    MODAL_ORCHESTRATOR_FLAVOR,
    MODAL_STEP_OPERATOR_FLAVOR,
)
from zenml.integrations.modal.flavors.modal_volume_artifact_store_flavor import (
    ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX,
    MODAL_VOLUME_URI_SCHEME,
    ModalVolumeArtifactStoreConfig,
    parse_modal_volume_uri,
)
from zenml.io.fileio import convert_to_str
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.stack import Stack


class _ModalVolumeDownloadFile:
    """Temporary-file-backed reader for Modal SDK downloads."""

    def __init__(self, chunks: Iterable[bytes], mode: str) -> None:
        """Write SDK chunks to a local temp file and open it for reading.

        Args:
            chunks: Byte chunks returned by the Modal SDK.
            mode: File open mode.
        """
        temp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False
            ) as temp_file:
                temp_path = temp_file.name
                for chunk in chunks:
                    temp_file.write(chunk)

            self._temp_path = temp_path
            encoding = "utf-8" if "b" not in mode else None
            self._file = open(self._temp_path, mode=mode, encoding=encoding)
            self._closed = False
        except Exception:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def __getattr__(self, name: str) -> Any:
        """Delegate file operations to the temporary file."""
        return getattr(self._file, name)

    def __enter__(self) -> "_ModalVolumeDownloadFile":
        """Return the readable file object."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close and delete the temporary download file."""
        self.close()

    def close(self) -> None:
        """Close and delete the temporary download file."""
        if self._closed:
            return
        self._closed = True
        self._file.close()
        if os.path.exists(self._temp_path):
            os.remove(self._temp_path)


class _ModalVolumeUploadFile:
    """Temporary-file-backed writer for Modal SDK uploads."""

    def __init__(
        self,
        artifact_store: "ModalVolumeArtifactStore",
        path: PathType,
        mode: str,
    ) -> None:
        """Create a local temporary file that uploads on successful close.

        Args:
            artifact_store: Artifact store that owns the destination Volume.
            path: Modal Volume URI to upload to.
            mode: File open mode.
        """
        encoding = "utf-8" if "b" not in mode else None
        self._artifact_store = artifact_store
        self._path = path
        self._temp_file = tempfile.NamedTemporaryFile(
            mode=mode,
            delete=False,
            encoding=encoding,
        )
        self._closed = False

    def __getattr__(self, name: str) -> Any:
        """Delegate file operations to the temporary file."""
        return getattr(self._temp_file, name)

    def __enter__(self) -> "_ModalVolumeUploadFile":
        """Return the writable file object."""
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Upload only when the write context exits cleanly."""
        self.close(upload=exc_type is None)

    def close(self, upload: bool = True) -> None:
        """Close the temp file and optionally upload it to the Volume.

        Args:
            upload: Whether to upload the temporary file before deleting it.
        """
        if self._closed:
            return
        self._closed = True
        temp_path = self._temp_file.name
        self._temp_file.close()
        should_delete = not upload
        if upload:
            self._artifact_store._upload_local_file(temp_path, self._path)
            should_delete = True
        if should_delete and os.path.exists(temp_path):
            os.remove(temp_path)

    def write_existing_contents(self, chunks: Iterable[bytes]) -> None:
        """Write existing SDK file contents before appending new data.

        Args:
            chunks: Byte chunks returned by the Modal SDK.
        """
        binary_mode = "b" in self._temp_file.mode
        for chunk in chunks:
            if binary_mode:
                self._temp_file.write(chunk)
            else:
                self._temp_file.write(chunk.decode("utf-8"))


class ModalVolumeArtifactStore(BaseArtifactStore):
    """Artifact store that accesses a mounted Modal Volume with local IO."""

    @property
    def config(self) -> ModalVolumeArtifactStoreConfig:
        """Get the config of this artifact store.

        Returns:
            The Modal Volume artifact-store config.
        """
        return cast(ModalVolumeArtifactStoreConfig, self._config)

    @property
    def volume_name(self) -> str:
        """The Modal Volume name derived from the configured path.

        Returns:
            The Modal Volume name.
        """
        return self.config.volume_name

    @property
    def volume_prefix(self) -> str:
        """The Modal Volume prefix derived from the configured path.

        Returns:
            The prefix inside the mounted Modal Volume.
        """
        return self.config.volume_prefix

    @property
    def validator(self) -> StackValidator:
        """Validate that the stack can mount Modal Volumes at runtime.

        Returns:
            A stack validator that limits this artifact store to Modal-native
            execution paths.
        """

        def _validate_modal_runtime(stack: "Stack") -> Tuple[bool, str]:
            orchestrator = getattr(stack, "orchestrator", None)
            if (
                getattr(orchestrator, "flavor", None)
                != MODAL_ORCHESTRATOR_FLAVOR
            ):
                return False, (
                    "Modal Volume artifact stores are Modal-native storage, "
                    "not S3-compatible general cloud artifact storage. The "
                    "stack must use the Modal orchestrator so ZenML artifact "
                    "reads and writes run inside Modal sandboxes with the "
                    "Volume mounted. Local, Kubernetes, and other non-Modal "
                    "orchestrators are not supported until Modal SDK fallback "
                    "execution is implemented."
                )

            step_operators = getattr(stack, "step_operators", {}) or {}
            non_modal_step_operators = [
                step_operator.name
                for step_operator in step_operators.values()
                if step_operator.flavor != MODAL_STEP_OPERATOR_FLAVOR
            ]
            if non_modal_step_operators:
                return False, (
                    "Modal Volume artifact stores can only be used with "
                    "Modal runtimes in this release. Non-Modal step operators "
                    f"cannot mount Modal Volumes: {non_modal_step_operators}."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_modal_runtime
        )

    def _validate_runtime_mount_metadata(self) -> None:
        """Check that the mounted fast path matches this artifact store.

        Raises:
            RuntimeError: If the Modal runtime mounted a different Volume or
                artifact-store prefix.
        """
        expected_mount_path = posixpath.normpath(self.config.mount_path)
        runtime_values = {
            ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME: self.volume_name,
            ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX: self.volume_prefix,
            ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH: expected_mount_path,
        }

        for env_var, expected_value in runtime_values.items():
            actual_value = os.environ.get(env_var)
            if env_var == ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH:
                actual_value = (
                    posixpath.normpath(actual_value) if actual_value else None
                )

            if actual_value != expected_value:
                raise RuntimeError(
                    "The Modal Volume artifact store fast-path marker is set, "
                    "but the runtime mount metadata does not match this "
                    "artifact store. "
                    f"Expected {env_var}='{expected_value}', got "
                    f"'{actual_value}'. This sandbox may have mounted a "
                    "different Modal Volume artifact store."
                )

    def _is_mounted_fast_path_enabled(self) -> bool:
        """Check whether this process should use mounted Modal IO."""
        return handle_bool_env_var(
            ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH, default=False
        )

    def _require_mounted_fast_path(self) -> Path:
        """Return the mounted Volume path or fail with setup guidance.

        Returns:
            The resolved mount path.

        Raises:
            RuntimeError: If the runtime did not opt into mounted fast-path IO.
            FileNotFoundError: If the runtime marker is set but the mount is missing.
        """
        if not self._is_mounted_fast_path_enabled():
            raise RuntimeError(
                "The Modal Volume artifact store currently supports only the "
                "mounted Modal fast path. Set "
                f"{ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH}=1 in a Modal "
                "runtime where the Volume is mounted, or wait for the planned "
                "Modal SDK fallback implementation."
            )

        self._validate_runtime_mount_metadata()

        mount_path = Path(self.config.mount_path)
        if not mount_path.is_dir():
            raise FileNotFoundError(
                "The Modal Volume artifact store fast-path marker is set, but "
                f"the configured mount path '{self.config.mount_path}' does "
                f"not exist. Volume '{self.volume_name}' must be mounted at "
                "that path by the Modal runtime. The configured "
                f"create_if_missing value is {self.config.create_if_missing}."
            )

        return mount_path.resolve()

    def _uri_parts(self, uri: PathType) -> List[str]:
        """Return URI path segments and validate artifact-store bounds.

        Args:
            uri: A Modal Volume URI.

        Returns:
            The decoded path segments inside the Volume.

        Raises:
            FileNotFoundError: If the URI points outside this artifact store.
        """
        path = convert_to_str(uri)
        parsed = parse_modal_volume_uri(path)
        if parsed.volume_name != self.volume_name:
            raise FileNotFoundError(
                f"URI '{path}' uses Modal Volume '{parsed.volume_name}', but "
                f"this artifact store is configured for '{self.volume_name}'."
            )

        uri_parts = (
            parsed.volume_prefix.split("/") if parsed.volume_prefix else []
        )
        root_parts = (
            self.volume_prefix.split("/") if self.volume_prefix else []
        )
        if uri_parts[: len(root_parts)] != root_parts:
            raise FileNotFoundError(
                f"URI '{path}' is outside of artifact store bounds "
                f"'{self.path}'."
            )

        return uri_parts

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        """Check whether `path` is equal to or below `parent`.

        Args:
            path: The path to check.
            parent: The expected parent path.

        Returns:
            True if the path is below the parent.
        """
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True

    def _nearest_existing_path(self, path: Path) -> Path:
        """Find the nearest existing path, treating broken symlinks as existing.

        Args:
            path: The path to inspect.

        Returns:
            The nearest existing path or symlink.
        """
        current_path = path
        while not current_path.exists() and not current_path.is_symlink():
            if current_path == current_path.parent:
                return current_path
            current_path = current_path.parent
        return current_path

    def _artifact_store_root_path(self, mount_path: Path) -> Path:
        """Return the local path for the configured artifact-store prefix.

        Args:
            mount_path: The resolved Modal Volume mount path.

        Returns:
            The local artifact-store root path.
        """
        root_parts = (
            self.volume_prefix.split("/") if self.volume_prefix else []
        )
        return mount_path.joinpath(*root_parts) if root_parts else mount_path

    def _raise_path_escape_error(
        self, uri: PathType, boundary_name: str, boundary_path: Path
    ) -> None:
        """Raise a consistent error for paths outside an enforced boundary.

        Args:
            uri: The original Modal Volume URI.
            boundary_name: Human-readable boundary name.
            boundary_path: The resolved boundary path.

        Raises:
            FileNotFoundError: Always raised with path escape details.
        """
        raise FileNotFoundError(
            f"URI '{convert_to_str(uri)}' resolves outside the configured "
            f"{boundary_name} '{boundary_path}'."
        )

    def _validate_path_boundary(
        self,
        path: Path,
        boundary_path: Path,
        boundary_name: str,
        uri: PathType,
    ) -> None:
        """Reject paths whose real target escapes one boundary.

        Missing paths are allowed when their nearest existing parent is an
        ancestor of the boundary. This lets ZenML create a missing
        artifact-store root directory while still rejecting existing symlinks
        below that root that point elsewhere.

        Args:
            path: The candidate local path.
            boundary_path: The boundary path.
            boundary_name: Human-readable boundary name.
            uri: The original Modal Volume URI.
        """
        if not self._is_relative_to(path, boundary_path):
            self._raise_path_escape_error(uri, boundary_name, boundary_path)

        nearest_existing_path = self._nearest_existing_path(path)
        nearest_is_below_boundary = self._is_relative_to(
            nearest_existing_path, boundary_path
        )
        boundary_is_below_nearest = self._is_relative_to(
            boundary_path, nearest_existing_path
        )
        if not (nearest_is_below_boundary or boundary_is_below_nearest):
            self._raise_path_escape_error(uri, boundary_name, boundary_path)

        resolved_existing_path = nearest_existing_path.resolve(strict=False)
        if nearest_is_below_boundary and not self._is_relative_to(
            resolved_existing_path, boundary_path
        ):
            self._raise_path_escape_error(uri, boundary_name, boundary_path)

        if path.exists() or path.is_symlink():
            resolved_path = path.resolve(strict=False)
            if not self._is_relative_to(resolved_path, boundary_path):
                self._raise_path_escape_error(
                    uri, boundary_name, boundary_path
                )

    def _validate_mount_relative_path(
        self, path: Path, mount_path: Path, uri: PathType
    ) -> None:
        """Reject paths that escape the mount or artifact-store prefix.

        Args:
            path: The candidate local path.
            mount_path: The resolved Modal Volume mount path.
            uri: The original Modal Volume URI, used for error messages.
        """
        self._validate_path_boundary(
            path=path,
            boundary_path=mount_path,
            boundary_name="Modal Volume mount path",
            uri=uri,
        )
        self._validate_path_boundary(
            path=path,
            boundary_path=self._artifact_store_root_path(mount_path),
            boundary_name="artifact-store root path",
            uri=uri,
        )

    def _modal_environment_name(self) -> Optional[str]:
        """Return the Modal environment used for SDK Volume access."""
        from zenml.integrations.modal.sandbox_utils import (
            ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME,
        )

        if ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME in os.environ:
            return os.environ[ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME] or None
        return os.environ.get("MODAL_ENVIRONMENT") or None

    def _get_modal_volume(self) -> Any:
        """Look up the configured Modal Volume through the Modal SDK.

        Returns:
            The Modal SDK Volume object.

        Raises:
            RuntimeError: If Modal is unavailable or the Volume lookup fails.
        """
        cached_volume = getattr(self, "_modal_volume", None)
        if cached_volume is not None:
            return cached_volume

        try:
            import modal
        except ImportError as e:
            raise RuntimeError(
                "The Modal Volume artifact store needs the `modal` package "
                "installed when it is accessed outside a mounted Modal "
                "runtime. Install the ZenML Modal integration and configure "
                "Modal credentials for this process."
            ) from e

        modal_environment = self._modal_environment_name()
        try:
            volume = modal.Volume.from_name(
                self.volume_name,
                environment_name=modal_environment,
                create_if_missing=self.config.create_if_missing,
            )
        except Exception as e:
            environment_text = modal_environment or "the default Modal environment"
            raise RuntimeError(
                "Failed to access Modal Volume "
                f"'{self.volume_name}' in {environment_text} through the "
                "Modal SDK. Ensure Modal credentials are configured for this "
                "process and that the Volume exists, or set "
                "create_if_missing=True."
            ) from e

        object.__setattr__(self, "_modal_volume", volume)
        return volume

    def _sdk_path(self, uri: PathType) -> str:
        """Translate a Modal Volume URI into an SDK path.

        Args:
            uri: A Modal Volume URI.

        Returns:
            The absolute path used by Modal SDK Volume file APIs.
        """
        parts = self._uri_parts(uri)
        return "/" + "/".join(parts) if parts else "/"

    @staticmethod
    def _is_modal_not_found_error(error: Exception) -> bool:
        """Check whether a Modal SDK exception means a path is missing."""
        return error.__class__.__name__ == "NotFoundError"

    @staticmethod
    def _entry_is_directory(entry: Any) -> bool:
        """Return whether a Modal Volume FileEntry describes a directory."""
        return getattr(getattr(entry, "type", None), "name", "") == "DIRECTORY"

    def _get_sdk_entry(self, path: PathType) -> Optional[Any]:
        """Find the Modal SDK directory entry for a path.

        Args:
            path: Modal Volume URI to inspect.

        Returns:
            The matching Modal SDK FileEntry, or `None` when missing.
        """
        sdk_path = posixpath.normpath(self._sdk_path(path))
        if sdk_path == "/":
            return None

        parent = posixpath.dirname(sdk_path) or "/"
        name = posixpath.basename(sdk_path)
        try:
            entries = self._get_modal_volume().listdir(
                parent, recursive=False
            )
        except Exception as e:
            if self._is_modal_not_found_error(e):
                return None
            raise

        for entry in entries:
            entry_path = posixpath.normpath(
                "/" + str(getattr(entry, "path", "")).lstrip("/")
            )
            if entry_path == sdk_path or posixpath.basename(entry_path) == name:
                return entry
        return None

    def _upload_local_file(self, local_path: str, dst: PathType) -> None:
        """Upload a local file to the configured Modal Volume.

        Args:
            local_path: Local file path to upload.
            dst: Modal Volume URI destination.
        """
        with self._get_modal_volume().batch_upload(force=True) as batch:
            batch.put_file(local_path, self._sdk_path(dst))

    def _local_path(self, uri: PathType) -> str:
        """Translate a Modal Volume URI into a mounted local filesystem path.

        Args:
            uri: A Modal Volume URI.

        Returns:
            The corresponding local path below the configured mount path.
        """
        mount_path = self._require_mounted_fast_path()
        parts = self._uri_parts(uri)
        local_path = mount_path.joinpath(*parts) if parts else mount_path
        self._validate_mount_relative_path(local_path, mount_path, uri)
        return str(local_path)

    def _uri_from_local_path(
        self, local_path: str, mount_path: Optional[Path] = None
    ) -> str:
        """Translate a mounted local filesystem path back into a Modal URI.

        Args:
            local_path: A local path below the configured mount path.
            mount_path: The resolved mount path to use, if already available.

        Returns:
            The corresponding Modal Volume URI.
        """
        if mount_path is None:
            mount_path = self._require_mounted_fast_path()
        path = Path(local_path).resolve()
        artifact_store_root_path = self._artifact_store_root_path(mount_path)
        if not self._is_relative_to(path, artifact_store_root_path):
            raise FileNotFoundError(
                f"Local path '{local_path}' resolves outside the configured "
                f"artifact-store root path '{artifact_store_root_path}'."
            )
        relative_path = path.relative_to(mount_path)
        relative = relative_path.as_posix()
        if relative == ".":
            return f"{MODAL_VOLUME_URI_SCHEME}{self.volume_name}"
        return f"{MODAL_VOLUME_URI_SCHEME}{self.volume_name}/{relative}"

    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file.

        Returns:
            A file-like object.
        """
        if self._is_mounted_fast_path_enabled():
            encoding = "utf-8" if "b" not in mode else None
            return open(self._local_path(path), mode=mode, encoding=encoding)

        if "+" in mode:
            raise NotImplementedError(
                "Modal Volume SDK fallback does not support read/write "
                "update modes yet."
            )

        if "r" in mode:
            chunks = self._get_modal_volume().read_file(self._sdk_path(path))
            try:
                return _ModalVolumeDownloadFile(chunks, mode)
            except Exception as e:
                if self._is_modal_not_found_error(e):
                    raise FileNotFoundError(convert_to_str(path)) from e
                raise

        if "a" in mode:
            write_mode = mode.replace("a", "w")
            file = _ModalVolumeUploadFile(self, path, write_mode)
            try:
                if self.exists(path):
                    chunks = self._get_modal_volume().read_file(
                        self._sdk_path(path)
                    )
                    file.write_existing_contents(chunks)
            except Exception:
                file.close(upload=False)
                raise
            return file

        if "w" in mode or "x" in mode:
            if "x" in mode and self.exists(path):
                raise FileExistsError(
                    f"Destination file '{convert_to_str(path)}' already "
                    "exists."
                )
            return _ModalVolumeUploadFile(self, path, mode)

        raise ValueError(f"Unsupported file mode for Modal Volume: {mode}")

    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file.

        Args:
            src: The path to copy from.
            dst: The path to copy to.
            overwrite: If a file already exists at the destination, overwrite it.

        Raises:
            FileExistsError: If the destination exists and overwrite is false.
        """
        if not self._is_mounted_fast_path_enabled():
            if overwrite:
                raise NotImplementedError(
                    "Modal Volume SDK fallback does not support overwriting "
                    "copy destinations safely yet."
                )
            if self.exists(dst):
                raise FileExistsError(
                    f"Destination file '{convert_to_str(dst)}' already "
                    "exists. Set `overwrite=True` to copy anyway."
                )
            self._get_modal_volume().copy_files(
                [self._sdk_path(src)], self._sdk_path(dst), recursive=False
            )
            return

        local_src = self._local_path(src)
        local_dst = self._local_path(dst)
        if not overwrite and os.path.exists(local_dst):
            raise FileExistsError(
                f"Destination file '{convert_to_str(dst)}' already exists. "
                "Set `overwrite=True` to copy anyway."
            )
        shutil.copyfile(local_src, local_dst)

    def exists(self, path: PathType) -> bool:
        """Check whether a path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        if not self._is_mounted_fast_path_enabled():
            if posixpath.normpath(self._sdk_path(path)) == "/":
                return True
            return self._get_sdk_entry(path) is not None
        return os.path.exists(self._local_path(path))

    def glob(self, pattern: PathType) -> List[PathType]:
        """Return all paths that match the given glob pattern.

        Args:
            pattern: The glob pattern to match.

        Returns:
            A list of matching Modal Volume URIs.
        """
        mount_path = self._require_mounted_fast_path()
        local_pattern = self._local_path(pattern)
        return [
            self._uri_from_local_path(path, mount_path=mount_path)
            for path in glob_module.glob(local_pattern)
        ]

    def isdir(self, path: PathType) -> bool:
        """Check whether a path is a directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a directory, False otherwise.
        """
        if not self._is_mounted_fast_path_enabled():
            if posixpath.normpath(self._sdk_path(path)) == "/":
                return True
            entry = self._get_sdk_entry(path)
            return bool(entry and self._entry_is_directory(entry))
        return os.path.isdir(self._local_path(path))

    def listdir(self, path: PathType) -> List[PathType]:
        """Return a list of bare names in a directory.

        Args:
            path: The path to list.

        Returns:
            A list of direct child names.
        """
        if not self._is_mounted_fast_path_enabled():
            try:
                entries = self._get_modal_volume().listdir(
                    self._sdk_path(path), recursive=False
                )
            except Exception as e:
                if self._is_modal_not_found_error(e):
                    raise FileNotFoundError(convert_to_str(path)) from e
                raise
            return [
                posixpath.basename(str(entry.path)) for entry in entries
            ]
        return os.listdir(self._local_path(path))  # type: ignore[return-value]

    def makedirs(self, path: PathType) -> None:
        """Create a directory and any missing parent directories.

        Args:
            path: The path to create.
        """
        if not self._is_mounted_fast_path_enabled():
            # Modal Volumes create parent directories implicitly during file
            # upload. This SDK fallback only validates the path; it does not
            # create empty directories in the Volume.
            self._uri_parts(path)
            return
        os.makedirs(self._local_path(path), exist_ok=True)

    def mkdir(self, path: PathType) -> None:
        """Create a directory.

        Args:
            path: The path to create.
        """
        if not self._is_mounted_fast_path_enabled():
            self.makedirs(path)
            return
        os.mkdir(self._local_path(path))

    def remove(self, path: PathType) -> None:
        """Remove a file.

        Args:
            path: The path to remove.
        """
        if not self._is_mounted_fast_path_enabled():
            try:
                self._get_modal_volume().remove_file(
                    self._sdk_path(path), recursive=False
                )
            except Exception as e:
                if self._is_modal_not_found_error(e):
                    raise FileNotFoundError(convert_to_str(path)) from e
                raise
            return
        os.remove(self._local_path(path))

    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file.

        Args:
            src: The path of the file to rename.
            dst: The destination path.
            overwrite: If a file already exists at the destination, overwrite it.

        Raises:
            FileExistsError: If the destination exists and overwrite is false.
        """
        local_src = self._local_path(src)
        local_dst = self._local_path(dst)
        if not overwrite and os.path.exists(local_dst):
            raise FileExistsError(
                f"Destination file '{convert_to_str(dst)}' already exists. "
                "Set `overwrite=True` to rename anyway."
            )
        os.rename(local_src, local_dst)

    def rmtree(self, path: PathType) -> None:
        """Remove a directory recursively.

        Args:
            path: The path to remove.
        """
        if not self._is_mounted_fast_path_enabled():
            try:
                self._get_modal_volume().remove_file(
                    self._sdk_path(path), recursive=True
                )
            except Exception as e:
                if self._is_modal_not_found_error(e):
                    raise FileNotFoundError(convert_to_str(path)) from e
                raise
            return
        shutil.rmtree(self._local_path(path))

    def stat(self, path: PathType) -> Any:
        """Return stat info for the given path.

        Args:
            path: The path to get stat info for.

        Returns:
            The stat result.
        """
        return os.stat(self._local_path(path))

    def size(self, path: PathType) -> int:
        """Get the size of a file or directory in bytes.

        Args:
            path: The path to size.

        Returns:
            The size in bytes.
        """
        mount_path = self._require_mounted_fast_path()
        local_path = self._local_path(path)
        if not os.path.isdir(local_path):
            return os.path.getsize(local_path)

        total_size = 0
        for root, dirs, files in os.walk(local_path):
            root_path = Path(root)
            self._validate_mount_relative_path(root_path, mount_path, path)
            for dir_name in dirs:
                self._validate_mount_relative_path(
                    root_path / dir_name, mount_path, path
                )
            for file_name in files:
                file_path = root_path / file_name
                self._validate_mount_relative_path(file_path, mount_path, path)
                total_size += os.path.getsize(file_path)
        return total_size

    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Walk a directory tree.

        Args:
            top: Path of directory to walk.
            topdown: Whether to walk directories topdown or bottom-up.
            onerror: Callable that gets called if an error occurs.

        Yields:
            Tuples containing the current Modal URI, directory names, and file names.
        """
        mount_path = self._require_mounted_fast_path()
        for root, dirs, files in os.walk(
            self._local_path(top), topdown=topdown, onerror=onerror
        ):
            root_path = Path(root)
            self._validate_mount_relative_path(root_path, mount_path, top)
            for dir_name in dirs:
                self._validate_mount_relative_path(
                    root_path / dir_name, mount_path, top
                )
            for file_name in files:
                self._validate_mount_relative_path(
                    root_path / file_name, mount_path, top
                )
            yield (
                self._uri_from_local_path(root, mount_path=mount_path),
                dirs,
                files,
            )
