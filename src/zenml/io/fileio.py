#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import fnmatch
import os
import tarfile
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type

from tfx.dsl.io.filesystem import Filesystem, PathType

from zenml.constants import REMOTE_FS_PREFIX
from zenml.core.constants import ZENML_DIR_NAME
from zenml.exceptions import InitializationException
from zenml.io.fileio_registry import default_fileio_registry
from zenml.logger import get_logger

logger = get_logger(__name__)


def _get_filesystem(path: PathType) -> Type[Filesystem]:
    """Returns a filesystem class for a given path from the registry"""
    return default_fileio_registry.get_filesystem_for_path(path)


def open(path: PathType, mode: str = "r") -> Any:  # noqa
    """Open a file at the given path."""
    return _get_filesystem(path).open(path, mode=mode)


def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
    """Copy a file from the source to the destination."""
    src_fs = _get_filesystem(src)
    dst_fs = _get_filesystem(dst)
    if src_fs is dst_fs:
        src_fs.copy(src, dst, overwrite=overwrite)
    else:
        if not overwrite and file_exists(dst):
            raise FileExistsError(
                f"Destination file '{convert_to_str(dst)}' already exists "
                f"and `overwrite` is false."
            )
        contents = open(src, mode="rb").read()
        open(dst, mode="wb").write(contents)


def file_exists(path: PathType) -> bool:
    """Returns `True` if the given path exists."""
    return _get_filesystem(path).exists(path)


def remove(path: PathType) -> None:
    """Remove the file at the given path. Dangerous operation."""
    if not file_exists(path):
        raise FileNotFoundError(f"{convert_to_str(path)} does not exist!")
    _get_filesystem(path).remove(path)


def glob(pattern: PathType) -> List[PathType]:
    """Return the paths that match a glob pattern."""
    return _get_filesystem(pattern).glob(pattern)


def is_dir(path: PathType) -> bool:
    """Returns whether the given path points to a directory."""
    return _get_filesystem(path).isdir(path)


def is_root(path: str) -> bool:
    """Returns true if path has no parent in local filesystem.

    Args:
        path: Local path in filesystem.

    Returns:
        True if root, else False.
    """
    return Path(path).parent == Path(path)


def list_dir(dir_path: str, only_file_names: bool = False) -> List[str]:
    """Returns a list of files under dir.

    Args:
        dir_path: Path in filesystem.
        only_file_names: Returns only file names if True.

    Returns:
        List of full qualified paths.
    """
    try:
        return [
            os.path.join(dir_path, convert_to_str(f))
            if not only_file_names
            else convert_to_str(f)
            for f in _get_filesystem(dir_path).listdir(dir_path)
        ]
    except IOError:
        logger.debug(f"Dir {dir_path} not found.")
        return []


def make_dirs(path: PathType) -> None:
    """Make a directory at the given path, recursively creating parents."""
    _get_filesystem(path).makedirs(path)


def mkdir(path: PathType) -> None:
    """Make a directory at the given path; parent directory must exist."""
    _get_filesystem(path).mkdir(path)


def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
    """Rename source file to destination file.

    Args:
        src: The path of the file to rename.
        dst: The path to rename the source file to.
        overwrite: If a file already exists at the destination, this
            method will overwrite it if overwrite=`True` and
            raise a FileExistsError otherwise.

    Raises:
        FileExistsError: If a file already exists at the destination
            and overwrite is not set to `True`.
    """
    src_fs = _get_filesystem(src)
    dst_fs = _get_filesystem(dst)
    if src_fs is dst_fs:
        src_fs.rename(src, dst, overwrite=overwrite)
    else:
        raise NotImplementedError(
            f"Renaming from {convert_to_str(src)} to {convert_to_str(dst)} "
            f"using different filesystems plugins is currently not supported."
        )


def rm_dir(dir_path: str) -> None:
    """Deletes dir recursively. Dangerous operation.

    Args:
        dir_path: Dir to delete.
    """
    _get_filesystem(dir_path).rmtree(dir_path)


def stat(path: PathType) -> Any:
    """Return the stat descriptor for a given file path."""
    return _get_filesystem(path).stat(path)


def walk(
    top: PathType,
    topdown: bool = True,
    onerror: Optional[Callable[..., None]] = None,
) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
    """Return an iterator that walks the contents of the given directory.

    Args:
        top: Path of directory to walk.
        topdown: Whether to walk directories topdown or bottom-up.
        onerror: Callable that gets called if an error occurs.

    Returns:
        An Iterable of Tuples, each of which contain the path of the current
        directory path, a list of directories inside the current directory
        and a list of files inside the current directory.
    """
    return _get_filesystem(top).walk(top, topdown=topdown, onerror=onerror)


def find_files(dir_path: PathType, pattern: str) -> Iterable[str]:
    # TODO [ENG-189]: correct docstring since 'None' is never returned
    """Find files in a directory that match pattern.

    Args:
        dir_path: Path to directory.
        pattern: pattern like *.png.

    Yields:
         All matching filenames if found, else None.
    """
    for root, dirs, files in walk(dir_path):
        for basename in files:
            if fnmatch.fnmatch(convert_to_str(basename), pattern):
                filename = os.path.join(
                    convert_to_str(root), convert_to_str(basename)
                )
                yield filename


def is_remote(path: str) -> bool:
    """Returns True if path exists remotely.

    Args:
        path: Any path as a string.

    Returns:
        True if remote path, else False.
    """
    return any(path.startswith(prefix) for prefix in REMOTE_FS_PREFIX)


def is_gcs_path(path: str) -> bool:
    """Returns True if path is on Google Cloud Storage.

    Args:
        path: Any path as a string.

    Returns:
        True if gcs path, else False.
    """
    return path.startswith("gs://")


def create_file_if_not_exists(
    file_path: str, file_contents: str = "{}"
) -> None:
    """Creates file if it does not exist.

    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.

    """
    # if not fileio.exists(file_path):
    #     fileio.(file_path, file_contents)
    full_path = Path(file_path)
    create_dir_recursive_if_not_exists(str(full_path.parent))
    with open(str(full_path), "w") as f:
        f.write(file_contents)


def append_file(file_path: str, file_contents: str) -> None:
    """Appends file_contents to file.

    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.
    """
    # with file_io.FileIO(file_path, mode='a') as f:
    #     f.write(file_contents)
    raise NotImplementedError


def create_dir_if_not_exists(dir_path: str) -> None:
    """Creates directory if it does not exist.

    Args:
        dir_path(str): Local path in filesystem.
    """
    if not is_dir(dir_path):
        mkdir(dir_path)


def create_dir_recursive_if_not_exists(dir_path: str) -> None:
    """Creates directory recursively if it does not exist.

    Args:
        dir_path: Local path in filesystem.
    """
    if not is_dir(dir_path):
        make_dirs(dir_path)


def resolve_relative_path(path: str) -> str:
    """Takes relative path and resolves it absolutely.

    Args:
      path: Local path in filesystem.

    Returns:
        Resolved path.
    """
    if is_remote(path):
        return path
    return str(Path(path).resolve())


def copy_dir(
    source_dir: str, destination_dir: str, overwrite: bool = False
) -> None:
    """Copies dir from source to destination.

    Args:
        source_dir: Path to copy from.
        destination_dir: Path to copy to.
        overwrite: Boolean. If false, function throws an error before overwrite.
    """
    for source_file in list_dir(source_dir):
        source_file_path = Path(source_file)
        destination_name = os.path.join(destination_dir, source_file_path.name)
        if is_dir(source_file):
            copy_dir(source_file, destination_name, overwrite)
        else:
            create_dir_recursive_if_not_exists(
                str(Path(destination_name).parent)
            )
            copy(str(source_file_path), str(destination_name), overwrite)


def move(source: str, destination: str, overwrite: bool = False) -> None:
    """Moves dir or file from source to destination. Can be used to rename.

    Args:
        source: Local path to copy from.
        destination: Local path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    rename(source, destination, overwrite)


def read_file_contents_as_string(file_path: str) -> str:
    """Reads contents of file.

    Args:
        file_path: Path to file.
    """
    if not file_exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist!")
    return open(file_path).read()  # type: ignore[no-any-return]


def write_file_contents_as_string(file_path: str, content: str) -> None:
    """Writes contents of file.

    Args:
        file_path: Path to file.
        content: Contents of file.
    """
    with open(file_path, "w") as f:
        f.write(content)


def get_grandparent(dir_path: str) -> str:
    """Get grandparent of dir.

    Args:
        dir_path: Path to directory.

    Returns:
        The input paths parents parent.
    """
    return Path(dir_path).parent.stem


def get_parent(dir_path: str) -> str:
    """Get parent of dir.

    Args:
        dir_path(str): Path to directory.

    Returns:
        Parent (stem) of the dir as a string.
    """
    return Path(dir_path).stem


def load_csv_column_names(csv_file: str) -> List[str]:
    """Parse the first line of a csv file as column names."""
    with open(csv_file) as f:
        return f.readline().strip().split(",")  # type: ignore[no-any-return]


def load_csv_header(csv_path: str) -> List[str]:
    """Gets header column of csv and returns list.

    Args:
        csv_path: Path to csv file.
    """
    if not file_exists(csv_path):
        raise FileNotFoundError(f"{csv_path} does not exist!")
    return load_csv_column_names(csv_path)


def create_tarfile(
    source_dir: str,
    output_filename: str = "zipped.tar.gz",
    exclude_function: Optional[
        Callable[[tarfile.TarInfo], Optional[tarfile.TarInfo]]
    ] = None,
) -> None:
    """Create a compressed representation of source_dir.

    Args:
        source_dir: Path to source dir.
        output_filename: Name of outputted gz.
        exclude_function: Function that determines whether to exclude file.
    """
    if exclude_function is None:
        # default is to exclude the .zenml directory
        def exclude_function(
            tarinfo: tarfile.TarInfo,
        ) -> Optional[tarfile.TarInfo]:
            """Exclude files from tar.

            Args:
              tarinfo: Any

            Returns:
                tarinfo required for exclude.
            """
            filename = tarinfo.name
            if ".zenml/" in filename or "venv/" in filename:
                return None
            else:
                return tarinfo

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname="", filter=exclude_function)


def extract_tarfile(source_tar: str, output_dir: str) -> None:
    """Extracts all files in a compressed tar file to output_dir.

    Args:
        source_tar: Path to a tar compressed file.
        output_dir: Directory where to extract.
    """
    if is_remote(source_tar):
        raise NotImplementedError("Use local tars for now.")

    with tarfile.open(source_tar, "r:gz") as tar:
        tar.extractall(output_dir)


def is_zenml_dir(path: str) -> bool:
    """Check if dir is a zenml dir or not.

    Args:
        path: Path to the root.

    Returns:
        True if path contains a zenml dir, False if not.
    """
    config_dir_path = os.path.join(path, ZENML_DIR_NAME)
    return bool(is_dir(config_dir_path))


def get_zenml_dir(path: str = os.getcwd()) -> str:
    """Recursive function to find the zenml config starting from path.

    Args:
        path (Default value = os.getcwd()): Path to check.

    Returns:
        The full path with the resolved zenml directory.

    Raises:
        InitializationException if directory not found until root of OS.
    """
    if is_zenml_dir(path):
        return path

    if is_root(path):
        raise InitializationException(
            "Looks like you used ZenML outside of a ZenML repo. "
            "Please init a ZenML repo first before you using "
            "the framework."
        )
    return get_zenml_dir(str(Path(path).parent))


def get_zenml_config_dir(path: str = os.getcwd()) -> str:
    """Recursive function to find the zenml config starting from path.

    Args:
        path (Default value = os.getcwd()): Path to check.

    Returns:
        The full path with the resolved zenml directory.

    Raises:
        InitializationException if directory not found until root of OS.
    """
    return os.path.join(get_zenml_dir(str(Path(path))), ZENML_DIR_NAME)


def convert_to_str(path: PathType) -> str:
    """Converts a PathType to a str using UTF-8."""
    if isinstance(path, str):
        return path
    else:
        return path.decode("utf-8")
