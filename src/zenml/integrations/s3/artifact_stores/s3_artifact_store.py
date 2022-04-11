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


from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

import s3fs

from zenml.artifact_stores import BaseArtifactStore
from zenml.io.utils import convert_to_str
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

PathType = Union[bytes, str]


@register_stack_component_class
class S3ArtifactStore(BaseArtifactStore):
    """Artifact Store for Amazon S3 based artifacts."""

    # Class variables
    FLAVOR: ClassVar[str] = "s3"
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}
    FILESYSTEM: ClassVar[s3fs.S3FileSystem] = None

    @classmethod
    def _ensure_filesystem_set(cls) -> None:
        """Ensures that the filesystem is set."""
        if cls.FILESYSTEM is None:
            cls.FILESYSTEM = s3fs.S3FileSystem()

    @staticmethod
    def open(path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.
        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently, only
                'rb' and 'wb' to read and write binary files are supported.
        """
        S3ArtifactStore._ensure_filesystem_set()
        return S3ArtifactStore.FILESYSTEM.open(path=path, mode=mode)

    @staticmethod
    def copyfile(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Copy a file.
        Args:
            src: The path to copy from.
            dst: The path to copy to.
            overwrite: If a file already exists at the destination, this
                method will overwrite it if overwrite=`True` and
                raise a FileExistsError otherwise.
        Raises:
            FileNotFoundError: If the source file does not exist.
            FileExistsError: If a file already exists at the destination
                and overwrite is not set to `True`.
        """
        S3ArtifactStore._ensure_filesystem_set()
        if not overwrite and S3ArtifactStore.FILESYSTEM.exists(dst):
            raise FileExistsError(
                f"Unable to copy to destination '{convert_to_str(dst)}', "
                f"file already exists. Set `overwrite=True` to copy anyway."
            )

        # TODO [ENG-151]: Check if it works with overwrite=True or if we need to
        #  manually remove it first
        S3ArtifactStore.FILESYSTEM.copy(path1=src, path2=dst)

    @staticmethod
    def exists(path: PathType) -> bool:
        """Check whether a path exists."""
        S3ArtifactStore._ensure_filesystem_set()
        return S3ArtifactStore.FILESYSTEM.exists(path=path)  # type: ignore[no-any-return]

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        """Return all paths that match the given glob pattern.
        The glob pattern may include:
        - '*' to match any number of characters
        - '?' to match a single character
        - '[...]' to match one of the characters inside the brackets
        - '**' as the full name of a path component to match to search
          in subdirectories of any depth (e.g. '/some_dir/**/some_file)
        Args:
            pattern: The glob pattern to match, see details above.
        Returns:
            A list of paths that match the given glob pattern.
        """
        S3ArtifactStore._ensure_filesystem_set()
        return [
            f"s3://{path}"
            for path in S3ArtifactStore.FILESYSTEM.glob(path=pattern)
        ]

    @staticmethod
    def isdir(path: PathType) -> bool:
        """Check whether a path is a directory."""
        S3ArtifactStore._ensure_filesystem_set()
        return S3ArtifactStore.FILESYSTEM.isdir(path=path)  # type: ignore[no-any-return]

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        """Return a list of files in a directory."""
        S3ArtifactStore._ensure_filesystem_set()
        # remove s3 prefix if given, so we can remove the directory later as
        # this method is expected to only return filenames
        path = convert_to_str(path)
        if path.startswith("s3://"):
            path = path[5:]

        def _extract_basename(file_dict: Dict[str, Any]) -> str:
            """Extracts the basename from a file info dict returned by the S3
            filesystem."""
            file_path = cast(str, file_dict["Key"])
            base_name = file_path[len(path) :]
            return base_name.lstrip("/")

        return [
            _extract_basename(dict_)
            for dict_ in S3ArtifactStore.FILESYSTEM.listdir(path=path)
            # s3fs.listdir also returns the root directory, so we filter
            # it out here
            if _extract_basename(dict_)
        ]

    @staticmethod
    def makedirs(path: PathType) -> None:
        """Create a directory at the given path. If needed also
        create missing parent directories."""
        S3ArtifactStore._ensure_filesystem_set()
        S3ArtifactStore.FILESYSTEM.makedirs(path=path, exist_ok=True)

    @staticmethod
    def mkdir(path: PathType) -> None:
        """Create a directory at the given path."""
        S3ArtifactStore._ensure_filesystem_set()
        S3ArtifactStore.FILESYSTEM.makedir(path=path)

    @staticmethod
    def remove(path: PathType) -> None:
        """Remove the file at the given path."""
        S3ArtifactStore._ensure_filesystem_set()
        S3ArtifactStore.FILESYSTEM.rm_file(path=path)

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Rename source file to destination file.
        Args:
            src: The path of the file to rename.
            dst: The path to rename the source file to.
            overwrite: If a file already exists at the destination, this
                method will overwrite it if overwrite=`True` and
                raise a FileExistsError otherwise.
        Raises:
            FileNotFoundError: If the source file does not exist.
            FileExistsError: If a file already exists at the destination
                and overwrite is not set to `True`.
        """
        S3ArtifactStore._ensure_filesystem_set()
        if not overwrite and S3ArtifactStore.FILESYSTEM.exists(dst):
            raise FileExistsError(
                f"Unable to rename file to '{convert_to_str(dst)}', "
                f"file already exists. Set `overwrite=True` to rename anyway."
            )

        # TODO [ENG-152]: Check if it works with overwrite=True or if we need
        #  to manually remove it first
        S3ArtifactStore.FILESYSTEM.rename(path1=src, path2=dst)

    @staticmethod
    def rmtree(path: PathType) -> None:
        """Remove the given directory."""
        S3ArtifactStore._ensure_filesystem_set()
        S3ArtifactStore.FILESYSTEM.delete(path=path, recursive=True)

    @staticmethod
    def stat(path: PathType) -> Dict[str, Any]:
        """Return stat info for the given path."""
        S3ArtifactStore._ensure_filesystem_set()
        return S3ArtifactStore.FILESYSTEM.stat(path=path)  # type: ignore[no-any-return]

    @staticmethod
    def walk(
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory.
        Args:
            top: Path of directory to walk.
            topdown: Unused argument to conform to interface.
            onerror: Unused argument to conform to interface.
        Returns:
            An Iterable of Tuples, each of which contain the path of the current
            directory path, a list of directories inside the current directory
            and a list of files inside the current directory.
        """
        S3ArtifactStore._ensure_filesystem_set()
        # TODO [ENG-153]: Additional params
        for directory, subdirectories, files in S3ArtifactStore.FILESYSTEM.walk(
            path=top
        ):
            yield f"s3://{directory}", subdirectories, files
