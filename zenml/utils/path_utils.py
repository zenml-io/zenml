#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

import os
import tarfile
from pathlib import Path
from typing import Text, Callable

from tensorflow.python.lib.io import file_io
from tfx.utils.io_utils import _REMOTE_FS_PREFIX, load_csv_column_names


# TODO: [TFX] [LOW] Unnecessary dependency here

def is_root(path: Text):
    """
    Returns true if path has no parent in local filesystem.

    Args:
        path (str): Local path in filesystem.
    """
    return Path(path).parent == Path(path)


def is_dir(dir_path: Text):
    """
    Returns true if dir_path points to a dir.

    Args:
        dir_path (str): Local path in filesystem.
    """
    return file_io.is_directory_v2(dir_path)


def is_remote(path: Text):
    """
    Returns True if path exists remotely.

    Args:
        path (str): Any path.
    """
    return any([path.startswith(prefix) for prefix in
                _REMOTE_FS_PREFIX])


def is_gcs_path(path: Text):
    """
    Returns True if path is on Google Cloud Storage.

    Args:
        path (str): Any path.
    """
    return path.startswith('gs://')


def list_dir(dir_path: Text, only_file_names: bool = False):
    """
    Returns a list of files under dir.

    Args:
        dir_path (str): Path in filesystem.
        only_file_names (bool): Returns only file names if True.
    """
    return [os.path.join(dir_path, f) if not only_file_names else f
            for f in file_io.list_directory_v2(dir_path)]


def create_file_if_not_exists(file_path: Text, file_contents: Text):
    """
    Creates directory if it does not exist.

    Args:
        file_path (str): Local path in filesystem.
        file_contents (str): Contents of file.
    """
    if not file_io.file_exists_v2(file_path):
        file_io.write_string_to_file(file_path, file_contents)


def append_file(file_path: Text, file_contents: Text):
    """
    Appends file_contents to file.

    Args:
        file_path (str): Local path in filesystem.
        file_contents (str): Contents of file.
    """
    with file_io.FileIO(file_path, mode='a') as f:
        f.write(file_contents)


def create_dir_if_not_exists(dir_path: Text):
    """
    Creates directory if it does not exist.

    Args:
        dir_path (str): Local path in filesystem.
    """
    if not file_io.is_directory_v2(dir_path):
        file_io.create_dir_v2(dir_path)


def create_dir_recursive_if_not_exists(dir_path: Text):
    """
    Creates directory recursively if it does not exist.

    Args:
        dir_path (str): Local path in filesystem.
    """
    if not file_io.is_directory_v2(dir_path):
        file_io.recursive_create_dir_v2(dir_path)


def resolve_relative_path(path: Text):
    """
    Takes relative path and resolves it absolutely.

    Args:
        path (str): Local path in filesystem.
    """
    if is_remote(path):
        return path
    return str(Path(path).resolve())


def file_exists(path: Text):
    """
    Returns true if file exists at path.

    Args:
        path (str): Local path in filesystem.
    """
    return file_io.file_exists_v2(path)


def copy(source: Text, destination: Text, overwrite: bool = False):
    """
    Copies dir from source to destination.

    Args:
        source (str): Path to copy from.
        destination (str): Path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    return file_io.copy_v2(source, destination, overwrite)


def copy_dir(source_dir: Text, destination_dir: Text, overwrite: bool = False):
    """
    Copies dir from source to destination.

    Args:
        source_dir (str): Path to copy from.
        destination_dir (str): Path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    for f in list_dir(source_dir):
        p = Path(f)
        destination_name = os.path.join(destination_dir, p.name)
        if is_dir(f):
            copy_dir(f, destination_name, overwrite)
        else:
            create_dir_recursive_if_not_exists(
                str(Path(destination_name).parent))
            copy(f, destination_name, overwrite)


def move(source: Text, destination: Text, overwrite: bool = False):
    """
    Moves dir from source to destination. Can be used to rename.

    Args:
        source (str): Local path to copy from.
        destination (str): Local path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    return file_io.rename_v2(source, destination, overwrite)


def rm_dir(dir_path: Text):
    """
    Deletes dir recursively. Dangerous operation.

    Args:
        dir_path (str): Dir to delete.
    """
    file_io.delete_recursively_v2(dir_path)


def rm_file(file_path: Text):
    """
    Deletes file. Dangerous operation.

    Args:
        file_path (str): Path of file to delete.
    """
    if not file_exists(file_path):
        raise Exception(f'{file_path} does not exist!')
    return file_io.delete_file_v2(file_path)


def read_file_contents(file_path: Text):
    """
    Reads contents of file.

    Args:
        file_path (str): Path to file.
    """
    if not file_exists(file_path):
        raise Exception(f'{file_path} does not exist!')
    return file_io.read_file_to_string(file_path)


def write_file_contents(file_path: Text, content: Text):
    """
    Writes contents of file.

    Args:
        file_path (str): Path to file.
        content (str): Contents of file.
    """
    return file_io.write_string_to_file(file_path, content)


def get_grandparent(dir_path: Text):
    """
    Get grandparent of dir.

    Args:
        dir_path (str): Path to directory.
    """
    return Path(dir_path).parent.stem


def get_parent(dir_path: Text):
    """
    Get parent of dir.

    Args:
        dir_path (str): Path to directory.
    """
    return Path(dir_path).stem


def load_csv_header(csv_path: Text):
    """
    Gets header column of csv and returns list.

    Args:
        csv_path (str): Path to csv file.
    """
    return load_csv_column_names(csv_path)


def create_tarfile(source_dir: Text, output_filename: Text = 'zipped.tar.gz',
                   exclude_function: Callable = None):
    """
    Create a compressed representation of source_dir.

    Args:
        source_dir: path to source dir
        output_filename: name of outputted gz
        exclude_function: function that determines whether to exclude file
    """
    if exclude_function is None:
        # default is to exclude the .zenml directory
        def exclude_function(tarinfo):
            filename = tarinfo.name
            if '.zenml/' in filename:
                return None
            elif 'venv/' in filename:
                return None
            else:
                return tarinfo

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname='', filter=exclude_function)


def extract_tarfile(source_tar: Text, output_dir: Text):
    """
    Untars a compressed tar file to output_dir.

    Args:
        source_tar: path to a tar compressed file
        output_dir: directory where to uncompress
    """
    if is_remote(source_tar):
        raise NotImplementedError('Use local tars for now.')

    with tarfile.open(source_tar, "r:gz") as tar:
        tar.extractall(output_dir)
