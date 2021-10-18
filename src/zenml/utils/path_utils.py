#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""File utilities"""
# TODO: [TFX] [LOW] Unnecessary dependency here

import fnmatch
import os
import tarfile
from pathlib import Path
from typing import Any, Callable, Iterable, List, Tuple

from tfx.dsl.io.filesystem import PathType
from tfx.utils.io_utils import _REMOTE_FS_PREFIX, fileio, load_csv_column_names

from zenml.core.constants import ZENML_DIR_NAME
from zenml.exceptions import InitializationException
from zenml.logger import get_logger

logger = get_logger(__name__)


def walk(
    dir_path,
) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
    """Walks down the dir_path.

    Args:
        dir_path: Path of dir to walk down.

    Returns:
        Iterable of tuples to walk down.
    """
    return fileio.walk(dir_path)


def is_root(path: str) -> bool:
    """Returns true if path has no parent in local filesystem.

    Args:
        path: Local path in filesystem.

    Returns:
        True if root, else False.
    """
    return Path(path).parent == Path(path)


def is_dir(dir_path: str) -> bool:
    """Returns true if dir_path points to a dir.

    Args:
        dir_path: Local path in filesystem.

    Returns:
        True if is dir, else False.
    """
    return fileio.isdir(dir_path)


def find_files(dir_path, pattern) -> List[str]:
    # TODO [LOW]: correct docstring since 'None' is never returned
    """Find files in a directory that match pattern.

    Args:
        dir_path: Path to directory.
        pattern: pattern like *.png.

    Yields:
         All matching filenames if found, else None.
    """
    for root, dirs, files in walk(dir_path):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def is_remote(path: str) -> bool:
    """Returns True if path exists remotely.

    Args:
        path: Any path as a string.

    Returns:
        True if remote path, else False.
    """
    return any([path.startswith(prefix) for prefix in _REMOTE_FS_PREFIX])


def is_gcs_path(path: str) -> bool:
    """Returns True if path is on Google Cloud Storage.

    Args:
        path: Any path as a string.

    Returns:
        True if gcs path, else False.
    """
    return path.startswith("gs://")


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
            os.path.join(dir_path, f) if not only_file_names else f
            for f in fileio.listdir(dir_path)
        ]
    except fileio.NotFoundError:
        logger.debug(f"Dir {dir_path} not found.")
        return []


def create_file_if_not_exists(file_path: str, file_contents: str = "{}"):
    """Creates directory if it does not exist.

    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.

    """
    # if not fileio.exists(file_path):
    #     fileio.(file_path, file_contents)
    full_path = Path(file_path)
    create_dir_recursive_if_not_exists(str(full_path.parent))
    with fileio.open(str(full_path), "w") as f:
        f.write(file_contents)


def append_file(file_path: str, file_contents: str):
    """Appends file_contents to file.

    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.
    """
    # with file_io.FileIO(file_path, mode='a') as f:
    #     f.write(file_contents)
    raise NotImplementedError


def create_dir_if_not_exists(dir_path: str):
    """Creates directory if it does not exist.

    Args:
        dir_path(str): Local path in filesystem.
    """
    if not fileio.isdir(dir_path):
        fileio.mkdir(dir_path)


def create_dir_recursive_if_not_exists(dir_path: str):
    """Creates directory recursively if it does not exist.

    Args:
        dir_path: Local path in filesystem.
    """
    if not fileio.isdir(dir_path):
        fileio.mkdir(dir_path)  # TODO [LOW]:  check if working recursively


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


def file_exists(path: str) -> bool:
    """Returns true if file exists at path.

    Args:
        path: Local path in filesystem.

    Returns:
        True if file exists, else False.
    """
    return fileio.exists(path)


def copy(source: str, destination: str, overwrite: bool = False):
    """Copies dir from source to destination.

    Args:
        source(str): Path to copy from.
        destination(str): Path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    return fileio.copy(source, destination, overwrite)


def copy_dir(source_dir: str, destination_dir: str, overwrite: bool = False):
    """Copies dir from source to destination.

    Args:
        source_dir: Path to copy from.
        destination_dir: Path to copy to.
        overwrite: Boolean, if false, then throws an error before overwrite.
    """
    for f in list_dir(source_dir):
        p = Path(f)
        destination_name = os.path.join(destination_dir, p.name)
        if is_dir(f):
            copy_dir(f, destination_name, overwrite)
        else:
            create_dir_recursive_if_not_exists(
                str(Path(destination_name).parent)
            )
            copy(f, destination_name, overwrite)


def move(source: str, destination: str, overwrite: bool = False):
    """Moves dir from source to destination. Can be used to rename.

    Args:
        source: Local path to copy from.
        destination: Local path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    return fileio.rename(source, destination, overwrite)


def rm_dir(dir_path: str):
    """Deletes dir recursively. Dangerous operation.

    Args:
        dir_path: Dir to delete.
    """
    fileio.rmtree(dir_path)


def rm_file(file_path: str):
    """Deletes file. Dangerous operation.

    Args:
        file_path: Path of file to delete.
    """
    if not file_exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist!")
    return fileio.remove(file_path)


def read_file_contents_as_string(file_path: str):
    """Reads contents of file.

    Args:
        file_path: Path to file.
    """
    if file_exists(file_path):
        return fileio.open(file_path).read()


def write_file_contents_as_string(file_path: str, content: str):
    """Writes contents of file.

    Args:
        file_path: Path to file.
        content: Contents of file.
    """
    with fileio.open(file_path, "w") as f:
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


def load_csv_header(csv_path: str) -> List[str]:
    """Gets header column of csv and returns list.

    Args:
        csv_path: Path to csv file.
    """
    if file_exists(csv_path):
        return load_csv_column_names(csv_path)
    else:
        raise FileNotFoundError(f"{csv_path} does not exist!")


def create_tarfile(
    source_dir: str,
    output_filename: str = "zipped.tar.gz",
    exclude_function: Callable = None,
):
    """Create a compressed representation of source_dir.

    Args:
        source_dir: Path to source dir.
        output_filename: Name of outputted gz.
        exclude_function: Function that determines whether to exclude file.
    """
    if exclude_function is None:
        # default is to exclude the .zenml directory
        def exclude_function(tarinfo: Any):
            """Exclude files from tar.

            Args:
              tarinfo: Any

            Returns:
                tarinfo required for exclude.
            """
            filename = tarinfo.name
            if ".zenml/" in filename:
                return None
            elif "venv/" in filename:
                return None
            else:
                return tarinfo

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname="", filter=exclude_function)


def extract_tarfile(source_tar: str, output_dir: str):
    """Untars a compressed tar file to output_dir.

    Args:
        source_tar: Path to a tar compressed file.
        output_dir: Directory where to uncompress.
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
    if is_dir(config_dir_path):
        return True
    return False


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
