#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""The base interface to extend the ZenML artifact store."""

import inspect
import os
import textwrap
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic import Field, model_validator

from zenml.constants import (
    ENV_ZENML_SERVER,
    ENV_ZENML_SERVER_ALLOW_LOCAL_FILE_ACCESS,
    IN_MEMORY_ARTIFACT_URI_PREFIX,
    handle_bool_env_var,
)
from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError, IllegalOperationError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack import Flavor, StackComponent, StackComponentConfig
from zenml.utils import io_utils
from zenml.utils.pydantic_utils import before_validator_handler

logger = get_logger(__name__)

PathType = Union[bytes, str]


@dataclass(frozen=True)
class ObjectInfo:
    """Metadata for an object stored in an artifact store.

    Attributes:
        uri: Absolute artifact store URI/path for the object.
        relative_path: Object path relative to the listed prefix.
        size: Optional object size in bytes.
        etag: Optional provider object checksum/entity tag.
        generation: Optional provider generation identifier.
        version: Optional provider version identifier.
        last_modified: Optional provider modification timestamp.
    """

    uri: str
    relative_path: str
    size: Optional[int] = None
    etag: Optional[str] = None
    generation: Optional[str] = None
    version: Optional[str] = None
    last_modified: Optional[datetime] = None


@dataclass(frozen=True)
class ObjectDeleteFailure:
    """A failed object deletion attempt."""

    path: str
    error: Exception


@dataclass(frozen=True)
class BulkDeleteResult:
    """Result of deleting multiple objects from an artifact store."""

    deleted_paths: List[str]
    failures: List[ObjectDeleteFailure]

    @property
    def successful(self) -> bool:
        """Whether all requested objects were deleted successfully."""
        return not self.failures


def _allow_local_file_access() -> bool:
    """Return whether local artifact paths may be accessed."""
    if ENV_ZENML_SERVER in os.environ:
        return handle_bool_env_var(
            ENV_ZENML_SERVER_ALLOW_LOCAL_FILE_ACCESS, False
        )
    return True


def _validate_artifact_store_path(
    path: str,
    fixed_root_path: str,
    allow_local_file_access: bool,
) -> None:
    """Validate that a path stays within an artifact store root."""
    if path.startswith(IN_MEMORY_ARTIFACT_URI_PREFIX):
        return

    if not allow_local_file_access and not io_utils.is_remote(path):
        raise IllegalOperationError(
            "Files in a local artifact store cannot be accessed from the "
            "server."
        )

    if not path.startswith(fixed_root_path):
        raise FileNotFoundError(
            f"File `{path}` is outside of "
            f"artifact store bounds `{fixed_root_path}`"
        )


def _sanitize_artifact_store_path(
    potential_path: Any,
    fixed_root_path: str,
    allow_local_file_access: bool,
) -> Any:
    """Sanitize a potential artifact store path."""
    if isinstance(potential_path, bytes):
        path = fileio.convert_to_str(potential_path)
    elif isinstance(potential_path, str):
        path = potential_path
    else:
        return potential_path

    if path.startswith(IN_MEMORY_ARTIFACT_URI_PREFIX):
        return path

    if io_utils.is_remote(path):
        import ntpath
        import posixpath

        path = path.replace(ntpath.sep, posixpath.sep)
        _validate_artifact_store_path(
            path, fixed_root_path, allow_local_file_access
        )
    else:
        _validate_artifact_store_path(
            str(Path(path).absolute().resolve()),
            fixed_root_path,
            allow_local_file_access,
        )

    return path


def _get_relative_object_path(uri: str, prefix: str) -> str:
    """Get an object path relative to a listing prefix."""
    normalized_prefix = prefix.rstrip("/\\")
    if uri == normalized_prefix:
        return os.path.basename(uri)

    prefix_with_separator = f"{normalized_prefix}/"
    if uri.startswith(prefix_with_separator):
        return uri[len(prefix_with_separator) :]

    return os.path.basename(uri)


class _sanitize_paths:
    """Sanitizes path inputs before calling the original function.

    Extra decoration layer is needed to pass in fixed artifact store root
    path for static methods that are called on filesystems directly.
    """

    def __init__(self, func: Callable[..., Any], fixed_root_path: str) -> None:
        """Initializes the decorator.

        Args:
            func: The function to decorate.
            fixed_root_path: The fixed artifact store root path.
        """
        self.func = func
        self.fixed_root_path = fixed_root_path
        self.allow_local_file_access = _allow_local_file_access()

        self.path_args: List[int] = []
        self.path_kwargs: List[str] = []
        for i, param in enumerate(
            inspect.signature(self.func).parameters.values()
        ):
            if param.annotation == PathType:
                self.path_kwargs.append(param.name)
                if param.default == inspect.Parameter.empty:
                    self.path_args.append(i)

    def _validate_path(self, path: str) -> None:
        """Validates a path.

        Args:
            path: The path to validate.

        Raises:
            FileNotFoundError: If the path is outside of the artifact store
                bounds.
            IllegalOperationError: If the path is a local file and the server
                is not configured to allow local file access.
        """
        _validate_artifact_store_path(
            path, self.fixed_root_path, self.allow_local_file_access
        )

    def _sanitize_potential_path(self, potential_path: Any) -> Any:
        """Sanitizes the input if it is a path.

        If the input is a **remote** path, this function replaces backslash path
        separators by forward slashes.

        Args:
            potential_path: Value that potentially refers to a (remote) path.

        Returns:
            The original input or a sanitized version of it in case of a remote
            path.
        """
        return _sanitize_artifact_store_path(
            potential_path, self.fixed_root_path, self.allow_local_file_access
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Decorator function that sanitizes paths before calling the original function.

        Args:
            *args: Positional args.
            **kwargs: Keyword args.

        Returns:
            Output of the input function called with sanitized paths.
        """
        # verify if `self` is part of the args
        has_self = bool(args and isinstance(args[0], BaseArtifactStore))

        # sanitize inputs for relevant args and kwargs, keep rest unchanged
        args = tuple(
            self._sanitize_potential_path(
                arg,
            )
            if i + has_self in self.path_args
            else arg
            for i, arg in enumerate(args)
        )
        kwargs = {
            key: self._sanitize_potential_path(
                value,
            )
            if key in self.path_kwargs
            else value
            for key, value in kwargs.items()
        }

        return self.func(*args, **kwargs)


class BaseArtifactStoreConfig(StackComponentConfig):
    """Config class for `BaseArtifactStore`.

    Base configuration for artifact storage backends.
    Field descriptions are defined inline using Field() descriptors.
    """

    path: str = Field(
        description="Root path for artifact storage. Must be a valid URI supported by the "
        "specific artifact store implementation. Examples: 's3://my-bucket/artifacts', "
        "'/local/storage/path', 'gs://bucket-name/zenml-artifacts', 'azure://container/path'. "
        "Path must be accessible with the configured credentials and permissions"
    )

    SUPPORTED_SCHEMES: ClassVar[Set[str]]
    IS_IMMUTABLE_FILESYSTEM: ClassVar[bool] = False

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _ensure_artifact_store(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validator function for the Artifact Stores.

        Checks whether supported schemes are defined and the given path is
        supported.

        Args:
            data: the input data to construct the artifact store.

        Returns:
            The validated values.

        Raises:
            ArtifactStoreInterfaceError: If the scheme is not supported.
        """
        try:
            getattr(cls, "SUPPORTED_SCHEMES")
        except AttributeError:
            raise ArtifactStoreInterfaceError(
                textwrap.dedent(
                    """
                    When you are working with any classes which subclass from
                    zenml.artifact_store.BaseArtifactStore please make sure
                    that your class has a ClassVar named `SUPPORTED_SCHEMES`
                    which should hold a set of supported file schemes such
                    as {"s3://"} or {"gcs://"}.

                    Example:

                    class MyArtifactStoreConfig(BaseArtifactStoreConfig):
                        ...
                        # Class Variables
                        SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}
                        ...
                    """
                )
            )

        if "path" in data:
            data["path"] = data["path"].strip("'\"`")
            if not any(
                data["path"].startswith(i) for i in cls.SUPPORTED_SCHEMES
            ):
                raise ArtifactStoreInterfaceError(
                    f"The path: '{data['path']}' you defined for your "
                    f"artifact store is not supported by the implementation of "
                    f"{cls.schema()['title']}, because it does not start with "
                    f"one of its supported schemes: {cls.SUPPORTED_SCHEMES}."
                )

        return data


class BaseArtifactStore(StackComponent):
    """Base class for all ZenML artifact stores."""

    @property
    def config(self) -> BaseArtifactStoreConfig:
        """Returns the `BaseArtifactStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseArtifactStoreConfig, self._config)

    @property
    def path(self) -> str:
        """The path to the artifact store.

        Returns:
            The path.
        """
        return self.config.path

    @property
    def custom_cache_key(self) -> Optional[bytes]:
        """Custom cache key.

        Any artifact store can override this property in case they need
        additional control over the caching behavior.

        Returns:
            Custom cache key.
        """
        return None

    # --- User interface ---
    @abstractmethod
    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: The path of the file to open.
            mode: The mode to open the file.

        Returns:
            The file object.
        """

    @abstractmethod
    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file from the source to the destination.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.
        """

    @abstractmethod
    def exists(self, path: PathType) -> bool:
        """Checks if a path exists.

        Args:
            path: The path to check.

        Returns:
            `True` if the path exists.
        """

    @abstractmethod
    def glob(self, pattern: PathType) -> List[PathType]:
        """Gets the paths that match a glob pattern.

        Args:
            pattern: The glob pattern.

        Returns:
            The list of paths that match the pattern.
        """

    @abstractmethod
    def isdir(self, path: PathType) -> bool:
        """Returns whether the given path points to a directory.

        Args:
            path: The path to check.

        Returns:
            `True` if the path points to a directory.
        """

    @abstractmethod
    def listdir(self, path: PathType) -> List[PathType]:
        """Returns a list of files under a given directory in the filesystem.

        Args:
            path: The path to list.

        Returns:
            The list of files under the given path.
        """

    @abstractmethod
    def makedirs(self, path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents.

        Args:
            path: The path to create.
        """

    @abstractmethod
    def mkdir(self, path: PathType) -> None:
        """Make a directory at the given path; parent directory must exist.

        Args:
            path: The path to create.
        """

    @abstractmethod
    def remove(self, path: PathType) -> None:
        """Remove the file at the given path. Dangerous operation.

        Args:
            path: The path to remove.
        """

    @abstractmethod
    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.
        """

    @abstractmethod
    def rmtree(self, path: PathType) -> None:
        """Deletes dir recursively. Dangerous operation.

        Args:
            path: The path to delete.
        """

    @abstractmethod
    def stat(self, path: PathType) -> Any:
        """Return the stat descriptor for a given file path.

        Args:
            path: The path to check.

        Returns:
            The stat descriptor.
        """

    @abstractmethod
    def size(self, path: PathType) -> Optional[int]:
        """Get the size of a file in bytes.

        Args:
            path: The path to the file.

        Returns:
            The size of the file in bytes or `None` if the artifact store
            does not implement the `size` method.
        """
        logger.warning(
            "Cannot get size of file '%s' since the artifact store %s does not "
            "implement the `size` method.",
            path,
            self.__class__.__name__,
        )
        return None

    @abstractmethod
    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory.

        Args:
            top: The path to walk.
            topdown: Whether to walk the top-down or bottom-up.
            onerror: The error handler.

        Returns:
            The iterator that walks the contents of the given directory.
        """

    def _sanitize_path(self, path: PathType) -> str:
        """Sanitize a path for optional non-abstract helper methods.

        Optional artifact-store hooks are intentionally not abstract so custom
        stores remain compatible. They therefore do not get wrapped by the
        abstract-method sanitizer and must validate path inputs explicitly.

        Args:
            path: The path to sanitize.

        Returns:
            The sanitized path as a string.
        """
        return cast(
            str,
            _sanitize_artifact_store_path(
                path, self.path, _allow_local_file_access()
            ),
        )

    def _get_object_info(self, uri: str, prefix: str) -> ObjectInfo:
        """Build object metadata using portable artifact-store methods."""
        return ObjectInfo(
            uri=uri,
            relative_path=_get_relative_object_path(uri, prefix),
            size=self.size(uri),
        )

    def list_objects(
        self, prefix: PathType, recursive: bool = False
    ) -> Iterable[ObjectInfo]:
        """List objects below a prefix with optional metadata.

        Artifact stores can override this to use provider-native paginated
        listing APIs. The default fallback uses the existing mandatory
        filesystem-like methods.

        Args:
            prefix: The file or directory/prefix to list.
            recursive: Whether to recursively list objects below directories.

        Returns:
            An iterable of object metadata.
        """
        sanitized_prefix = self._sanitize_path(prefix)

        if not self.exists(sanitized_prefix):
            return []

        if not self.isdir(sanitized_prefix):
            return [self._get_object_info(sanitized_prefix, sanitized_prefix)]

        if recursive:
            objects: List[ObjectInfo] = []
            for directory, _, files in self.walk(sanitized_prefix):
                for file_name in files:
                    uri = os.path.join(str(directory), str(file_name))
                    objects.append(
                        self._get_object_info(uri, sanitized_prefix)
                    )
            return objects

        objects = []
        for file_name in self.listdir(sanitized_prefix):
            uri = os.path.join(sanitized_prefix, str(file_name))
            if not self.isdir(uri):
                objects.append(self._get_object_info(uri, sanitized_prefix))
        return objects

    def delete_objects(self, paths: Iterable[PathType]) -> BulkDeleteResult:
        """Delete multiple objects from the artifact store.

        Artifact stores can override this to use provider-native bulk deletion.
        The default fallback loops over the existing ``remove`` method and
        captures per-path failures instead of failing the whole batch.

        Args:
            paths: Object paths to delete.

        Returns:
            Per-object deletion results.
        """
        deleted_paths: List[str] = []
        failures: List[ObjectDeleteFailure] = []

        for path in paths:
            sanitized_path = self._sanitize_path(path)
            try:
                self.remove(sanitized_path)
            except Exception as e:
                failures.append(
                    ObjectDeleteFailure(path=sanitized_path, error=e)
                )
            else:
                deleted_paths.append(sanitized_path)

        return BulkDeleteResult(deleted_paths=deleted_paths, failures=failures)

    def read_range(
        self, path: PathType, offset: int, length: Optional[int] = None
    ) -> bytes:
        """Read a byte range from an object.

        Artifact stores can override this to use provider-native range reads.
        The default fallback uses ``open`` and ``seek``.

        Args:
            path: Object path to read.
            offset: Zero-based byte offset to start reading from.
            length: Optional maximum number of bytes to read.

        Returns:
            The requested bytes.

        Raises:
            ValueError: If ``offset`` or ``length`` is negative.
        """
        if offset < 0:
            raise ValueError("Range read offset must be non-negative.")
        if length is not None and length < 0:
            raise ValueError("Range read length must be non-negative.")

        sanitized_path = self._sanitize_path(path)
        with self.open(sanitized_path, "rb") as file:
            file.seek(offset)
            if length is None:
                return cast(bytes, file.read())
            return cast(bytes, file.read(length))

    def compose_objects(
        self,
        sources: Sequence[PathType],
        destination: PathType,
        overwrite: bool = False,
    ) -> bool:
        """Compose source objects into one destination object.

        Artifact stores can override this for server-side object composition.
        The default returns ``False`` so callers can fall back to the portable
        Python merge path.

        Args:
            sources: Ordered source object paths.
            destination: Destination object path.
            overwrite: Whether an existing destination may be overwritten.

        Returns:
            Whether composition happened successfully.
        """
        for source in sources:
            self._sanitize_path(source)
        self._sanitize_path(destination)
        return False

    def download_objects_to_directory(
        self,
        objects: Iterable[ObjectInfo],
        local_dir: PathType,
        max_workers: Optional[int] = None,
    ) -> bool:
        """Download objects into a local directory.

        Artifact stores can override this to use provider transfer managers.
        The default returns ``False`` so callers can keep their existing
        streaming download behavior.

        Args:
            objects: Objects to download.
            local_dir: Local directory to download into.
            max_workers: Optional provider-specific worker count.

        Returns:
            Whether the provider handled the downloads.
        """
        for object_info in objects:
            self._sanitize_path(object_info.uri)
        local_path = fileio.convert_to_str(local_dir)
        if io_utils.is_remote(local_path):
            raise ValueError("Download directory must be a local path.")
        return False

    # --- Internal interface ---
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initiate the Pydantic object and register the corresponding filesystem.

        Args:
            *args: The positional arguments to pass to the Pydantic object.
            **kwargs: The keyword arguments to pass to the Pydantic object.
        """
        super(BaseArtifactStore, self).__init__(*args, **kwargs)
        self._add_path_sanitization()

        # If running in a ZenML server environment, we don't register
        # the filesystems. We always use the artifact stores directly.
        if ENV_ZENML_SERVER not in os.environ:
            self._register()

    def _add_path_sanitization(self) -> None:
        """Add path sanitization to the artifact store."""
        for method_name, method in inspect.getmembers(BaseArtifactStore):
            if getattr(method, "__isabstractmethod__", False):
                method_implementation = getattr(self, method_name)
                sanitized_method = _sanitize_paths(
                    method_implementation, self.path
                )
                setattr(self, method_name, sanitized_method)

    def _register(self) -> None:
        """Create and register a filesystem within the filesystem registry."""
        from zenml.io.filesystem import BaseFilesystem
        from zenml.io.filesystem_registry import default_filesystem_registry
        from zenml.io.local_filesystem import LocalFilesystem

        # Local filesystem is always registered, no point in doing it again.
        if isinstance(self, LocalFilesystem):
            return

        overloads: Dict[str, Any] = {
            "SUPPORTED_SCHEMES": self.config.SUPPORTED_SCHEMES,
        }
        for method_name, method in inspect.getmembers(BaseArtifactStore):
            if getattr(method, "__isabstractmethod__", False):
                method_implementation = getattr(self, method_name)
                overloads[method_name] = staticmethod(method_implementation)

        filesystem_class = type(
            self.__class__.__name__, (BaseFilesystem,), overloads
        )

        default_filesystem_registry.register(filesystem_class)

    def _remove_previous_file_versions(self, path: PathType) -> None:
        """Remove all file versions but the latest in the given path.

        Method is useful for logs stored in versioned file systems
        like AWS S3.

        Args:
            path: The path to the file.
        """
        return


class BaseArtifactStoreFlavor(Flavor):
    """Base class for artifact store flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.ARTIFACT_STORE

    @property
    def config_class(self) -> Type[StackComponentConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return BaseArtifactStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseArtifactStore"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
