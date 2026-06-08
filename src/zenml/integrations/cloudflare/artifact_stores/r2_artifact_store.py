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
"""Implementation of the Cloudflare R2 Artifact Store."""

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from zenml.artifact_stores import BaseArtifactStore
from zenml.integrations.cloudflare.flavors.cloudflare_r2_artifact_store_flavor import (
    R2ArtifactStoreConfig,
)
from zenml.integrations.cloudflare.utils import strip_r2_scheme
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
)
from zenml.io.fileio import convert_to_str

PathType = Union[bytes, str]


class R2ArtifactStore(S3ArtifactStore):
    """Artifact Store for Cloudflare R2 based artifacts.

    R2 exposes an S3-compatible API, so this reuses the entire S3 filesystem
    stack (including the leak-safe ``ZenMLS3Filesystem`` and credential
    handling). The only differences are:

    - the ``r2://`` URI scheme, which ``s3fs`` does not understand and must be
      stripped before paths reach the filesystem (and re-added on the way out),
      and
    - R2 does not expose the S3 bucket versioning API, so the versioning probe
      that the S3 store performs on initialization is skipped.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the R2 artifact store.

        Args:
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        # Skip S3ArtifactStore.__init__, which probes S3 bucket versioning;
        # R2 does not support that API. R2 buckets are never versioned.
        BaseArtifactStore.__init__(self, *args, **kwargs)
        self._boto3_bucket_holder = None
        self.is_versioned = False

    @property
    def config(self) -> R2ArtifactStoreConfig:
        """Get the config of this artifact store.

        Returns:
            The config of this artifact store.
        """
        return cast(R2ArtifactStoreConfig, self._config)

    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file.

        Returns:
            A file-like object.
        """
        return super().open(strip_r2_scheme(convert_to_str(path)), mode)

    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file.

        Args:
            src: The path to copy from.
            dst: The path to copy to.
            overwrite: Whether to overwrite an existing destination file.
        """
        super().copyfile(
            strip_r2_scheme(convert_to_str(src)),
            strip_r2_scheme(convert_to_str(dst)),
            overwrite,
        )

    def exists(self, path: PathType) -> bool:
        """Check whether a path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        return super().exists(strip_r2_scheme(convert_to_str(path)))

    def glob(self, pattern: PathType) -> List[PathType]:
        """Return all paths that match the given glob pattern.

        Args:
            pattern: The glob pattern to match.

        Returns:
            A list of `r2://` paths that match the given glob pattern.
        """
        return [
            f"r2://{path}"
            for path in self.filesystem.glob(
                path=strip_r2_scheme(convert_to_str(pattern))
            )
        ]

    def isdir(self, path: PathType) -> bool:
        """Check whether a path is a directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a directory, False otherwise.
        """
        return super().isdir(strip_r2_scheme(convert_to_str(path)))

    def listdir(self, path: PathType) -> List[PathType]:
        """Return a list of files in a directory.

        Args:
            path: The path to list.

        Returns:
            A list of file names in the given directory.
        """
        return super().listdir(strip_r2_scheme(convert_to_str(path)))

    def makedirs(self, path: PathType) -> None:
        """Create a directory at the given path and any missing parents.

        Args:
            path: The path to create.
        """
        super().makedirs(strip_r2_scheme(convert_to_str(path)))

    def mkdir(self, path: PathType) -> None:
        """Create a directory at the given path.

        Args:
            path: The path to create.
        """
        super().mkdir(strip_r2_scheme(convert_to_str(path)))

    def remove(self, path: PathType) -> None:
        """Remove the file at the given path.

        Args:
            path: The path of the file to remove.
        """
        super().remove(strip_r2_scheme(convert_to_str(path)))

    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file.

        Args:
            src: The path of the file to rename.
            dst: The path to rename the source file to.
            overwrite: Whether to overwrite an existing destination file.
        """
        super().rename(
            strip_r2_scheme(convert_to_str(src)),
            strip_r2_scheme(convert_to_str(dst)),
            overwrite,
        )

    def rmtree(self, path: PathType) -> None:
        """Remove the given directory.

        Args:
            path: The path of the directory to remove.
        """
        super().rmtree(strip_r2_scheme(convert_to_str(path)))

    def stat(self, path: PathType) -> Dict[str, Any]:
        """Return stat info for the given path.

        Args:
            path: The path to get stat info for.

        Returns:
            A dictionary containing the stat info.
        """
        return super().stat(strip_r2_scheme(convert_to_str(path)))

    def size(self, path: PathType) -> int:
        """Get the size of a file in bytes.

        Args:
            path: The path to the file.

        Returns:
            The size of the file in bytes.
        """
        return super().size(strip_r2_scheme(convert_to_str(path)))

    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Walk the contents of the given directory.

        Args:
            top: Path of directory to walk.
            topdown: Unused argument to conform to interface.
            onerror: Unused argument to conform to interface.

        Yields:
            Tuples of (current `r2://` directory, subdirectories, files).
        """
        for directory, subdirectories, files in self.filesystem.walk(
            path=strip_r2_scheme(convert_to_str(top))
        ):
            yield f"r2://{directory}", subdirectories, files
