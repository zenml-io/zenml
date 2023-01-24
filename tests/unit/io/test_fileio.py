#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

import os
import string
from collections.abc import Iterable
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import GeneratorType

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.strategies import text

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils

logger = get_logger(__name__)

TEMPORARY_FILE_NAME = "a_file.txt"
TEMPORARY_FILE_SEARCH_PREFIX = "a_f*.*"
ALPHABET = string.ascii_letters


def test_convert_to_str_converts_to_string(tmp_path) -> None:
    """Test that convert_to_str converts bytes to a string."""
    assert isinstance(
        fileio.convert_to_str(bytes(str(tmp_path), "ascii")), str
    )
    assert fileio.convert_to_str(bytes(str(tmp_path), "ascii")) == str(
        tmp_path
    )


def test_isdir_when_true(tmp_path):
    """is_dir returns true when path refers to a directory."""
    assert fileio.isdir(str(tmp_path))


def test_isdir_when_false(tmp_path):
    """isdir returns false when path doesn't refer to a directory."""
    assert (
        fileio.isdir(os.path.join(str(tmp_path) + TEMPORARY_FILE_NAME))
        is False
    )


def test_listdir_returns_a_list_of_file_names(tmp_path):
    """listdir should return a list of file names inside the queried dir."""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.listdir(str(tmp_path)) == [Path(temp_file.name).name]


def test_listdir_returns_one_result_for_one_file(tmp_path):
    """list_dir should return only one result, when there is only one file created."""
    io_utils.create_file_if_not_exists(
        os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    )
    assert len(fileio.listdir(str(tmp_path))) == 1


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(sample_file=text(min_size=1, alphabet=ALPHABET))
def test_listdir_returns_empty_list_when_dir_doesnt_exist(
    sample_file, tmp_path
):
    """list_dir should return an empty list when the directory doesn't exist."""
    not_a_real_dir = os.path.join(tmp_path, sample_file)
    assert fileio.listdir(not_a_real_dir) == []


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(not_a_file=text(min_size=1, alphabet=ALPHABET))
def test_open_returns_error_when_file_nonexistent(
    tmp_path, not_a_file: str
) -> None:
    """Test that open returns a file object."""
    with pytest.raises(FileNotFoundError):
        fileio.open(os.path.join(tmp_path, not_a_file), "rb")


def test_copy_moves_file_to_new_location(tmp_path) -> None:
    """Test that copy moves the file to the new location."""
    src = os.path.join(tmp_path, "test_file.txt")
    dst = os.path.join(tmp_path, "test_file2.txt")
    io_utils.create_file_if_not_exists(src)
    assert not os.path.exists(dst)
    fileio.copy(src, dst)
    assert os.path.exists(dst)


def test_copy_raises_error_when_file_exists(tmp_path) -> None:
    """Test that copy raises an error when the file already exists in the desired location."""
    src = os.path.join(tmp_path, "test_file.txt")
    dst = os.path.join(tmp_path, "test_file2.txt")
    io_utils.create_file_if_not_exists(src)
    io_utils.create_file_if_not_exists(dst)
    assert os.path.exists(src)
    assert os.path.exists(dst)
    with pytest.raises(FileExistsError):
        fileio.copy(src, dst)


def test_file_exists_function(tmp_path) -> None:
    """Test that file_exists returns True when the file exists."""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.exists(temp_file.name)


def test_file_exists_when_file_doesnt_exist(tmp_path) -> None:
    """Test that file_exists returns False when the file does not exist."""
    assert not fileio.exists(os.path.join(tmp_path, "not_a_file.txt"))


def test_remove_function(tmp_path) -> None:
    """Test that remove function actually removes a file."""
    new_file_path = os.path.join(tmp_path, "test_file.txt")
    io_utils.create_file_if_not_exists(new_file_path)
    assert fileio.exists(new_file_path)
    fileio.remove(new_file_path)
    assert not os.path.exists(new_file_path)


def test_glob_function(tmp_path) -> None:
    """Test that glob returns a list of files."""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        files = fileio.glob(f"{str(tmp_path)}/*")
        assert isinstance(files, list)
        assert temp_file.name in files


def test_make_dirs(tmp_path) -> None:
    """Test that make_dirs creates a directory."""
    fileio.makedirs(os.path.join(tmp_path, "not_a_dir"))
    assert os.path.exists(os.path.join(tmp_path, "not_a_dir"))


def test_make_dirs_when_recursive(tmp_path) -> None:
    """Test that make_dirs creates a directory."""
    fileio.makedirs(os.path.join(tmp_path, "not_a_dir/still_not_a_dir"))
    assert os.path.exists(os.path.join(tmp_path, "not_a_dir/still_not_a_dir"))


def test_mkdir_function(tmp_path) -> None:
    """Test that mkdir creates a directory."""
    fileio.mkdir(os.path.join(tmp_path, "not_a_dir"))
    assert os.path.exists(os.path.join(tmp_path, "not_a_dir"))


def test_mkdir_function_when_parent_doesnt_exist(tmp_path) -> None:
    """Test that mkdir creates a directory."""
    with pytest.raises(FileNotFoundError):
        fileio.mkdir(os.path.join(tmp_path, "not_a_dir/still_not_a_dir"))


def test_rename_function(tmp_path) -> None:
    """Test that renames a file."""
    io_utils.create_file_if_not_exists(os.path.join(tmp_path, "test_file.txt"))
    fileio.rename(
        os.path.join(tmp_path, "test_file.txt"),
        os.path.join(tmp_path, "new_file.txt"),
    )
    assert os.path.exists(os.path.join(tmp_path, "new_file.txt"))
    assert not os.path.exists(os.path.join(tmp_path, "test_file.txt"))


def test_rename_function_raises_error_if_file_already_exists(tmp_path) -> None:
    """Test that rename raises an error if the file already exists."""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.exists(temp_file.name)
        with pytest.raises(OSError):
            with NamedTemporaryFile(dir=tmp_path) as temp_file2:
                fileio.rename(temp_file.name, temp_file2.name)


def test_rm_dir_function(tmp_path) -> None:
    """Test that rm_dir removes a directory."""
    fileio.mkdir(os.path.join(tmp_path, "not_a_dir"))
    fileio.rmtree(os.path.join(tmp_path, "not_a_dir"))
    assert not os.path.exists(os.path.join(tmp_path, "not_a_dir"))


def test_rm_dir_function_works_recursively(tmp_path) -> None:
    """Test that rm_dir removes a directory recursively."""
    fileio.makedirs(os.path.join(tmp_path, "not_a_dir/also_not_a_dir"))
    fileio.rmtree(os.path.join(tmp_path, "not_a_dir/also_not_a_dir"))
    assert not os.path.exists(
        os.path.join(tmp_path, "not_a_dir/also_not_a_dir")
    )


def test_stat_returns_a_stat_result_object(tmp_path) -> None:
    """Test that stat returns a stat result object."""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert isinstance(fileio.stat(temp_file.name), os.stat_result)


def test_stat_raises_error_when_file_doesnt_exist(tmp_path) -> None:
    """Test that stat raises an error when the file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        fileio.stat(os.path.join(tmp_path, "not_a_file.txt"))


def test_size_returns_int_for_file(tmp_path):
    """Test that size returns an int for a file input"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        file_size = fileio.size(temp_file.name)
        assert isinstance(file_size, int)
        assert file_size == os.path.getsize(temp_file.name)


def test_size_returns_int_for_dir(tmp_path):
    """Test that size returns an int for a directory input"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        dir_size = fileio.size(str(tmp_path))
        assert isinstance(dir_size, int)
        assert dir_size == os.path.getsize(temp_file.name)  # only one file


def test_size_returns_zero_for_empty_dir(tmp_path):
    """Test that size returns zero for an empty directory"""
    assert fileio.size(str(tmp_path)) == 0


def test_size_returns_zero_for_non_existent_file(tmp_path):
    """Test that size returns zero for a non-existent file"""
    assert fileio.size(os.path.join(tmp_path, "not_a_file.txt")) == 0


def test_walk_returns_an_iterator(tmp_path) -> None:
    """Test that walk returns an iterator."""
    assert isinstance(fileio.walk(str(tmp_path)), Iterable)


def test_walk_function_returns_a_generator_object(tmp_path):
    """Check walk function returns a generator object."""
    assert isinstance(fileio.walk(str(tmp_path)), GeneratorType)
