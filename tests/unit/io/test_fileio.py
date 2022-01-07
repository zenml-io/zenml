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

import os
from collections.abc import Iterable
from io import FileIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import GeneratorType

import pytest
from hypothesis import given
from hypothesis.strategies import text
from tfx.dsl.io.filesystem import NotFoundError
from tfx.dsl.io.plugins.local import LocalFilesystem

import zenml.io.utils
from zenml.constants import REMOTE_FS_PREFIX
from zenml.io import fileio
from zenml.logger import get_logger

logger = get_logger(__name__)

TEMPORARY_FILE_NAME = "a_file.txt"
TEMPORARY_FILE_SEARCH_PREFIX = "a_f*.*"


def test_walk_function_returns_a_generator_object(tmp_path):
    """Check walk function returns a generator object"""
    assert isinstance(fileio.walk(str(tmp_path)), GeneratorType)


def test_is_root_when_true():
    """Check is_root returns true if path is the root"""
    assert fileio.is_root("/")


def test_is_root_when_false(tmp_path):
    """Check is_root returns false if path isn't the root"""
    assert fileio.is_root(tmp_path) is False


def test_is_dir_when_true(tmp_path):
    """is_dir returns true when path refers to a directory"""
    assert fileio.is_dir(str(tmp_path))


def test_is_dir_when_false(tmp_path):
    """is_dir returns false when path doesn't refer to a directory"""
    assert (
        fileio.is_dir(os.path.join(str(tmp_path) + TEMPORARY_FILE_NAME))
        is False
    )


def test_find_files_returns_generator_object_when_file_present(tmp_path):
    """find_files returns a generator object when it finds a file"""
    temp_file = os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    with open(temp_file, "w"):
        assert isinstance(
            fileio.find_files(str(tmp_path), TEMPORARY_FILE_SEARCH_PREFIX),
            GeneratorType,
        )


def test_find_files_when_file_present(tmp_path):
    """find_files locates a file within a temporary directory"""
    temp_file = os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    with open(temp_file, "w"):
        assert (
            next(fileio.find_files(str(tmp_path), TEMPORARY_FILE_SEARCH_PREFIX))
            is not None
        )


def test_find_files_when_file_absent(tmp_path):
    """find_files returns None when it doesn't find a file"""
    temp_file = os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    with open(temp_file, "w"):
        with pytest.raises(StopIteration):
            assert next(fileio.find_files(str(tmp_path), "abc*.*"))


@pytest.mark.parametrize("filesystem", REMOTE_FS_PREFIX)
def test_is_remote_when_using_remote_prefix(filesystem):
    """is_remote returns True when path starts with one of
    the TFX remote file prefixes"""
    some_random_path = os.path.join(filesystem + "some_directory")
    assert fileio.is_remote(some_random_path)


@given(text())
def test_is_remote_when_using_non_remote_prefix(filesystem):
    """is_remote returns False when path doesn't start with
    a remote prefix"""
    some_random_path = os.path.join(filesystem + "some_directory")
    assert fileio.is_remote(some_random_path) is False


@given(text())
def test_gcs_path_when_true(filename):
    """is_gcs checks if a file begins with the prefix `gs`"""
    gs_prefix = "gs://"
    sample_file_path = gs_prefix + filename
    assert zenml.io.utils.is_gcs_path(sample_file_path)


@given(text())
def test_gcs_path_when_false(filesystem):
    """is_gcs checks that false is returned when file has no `gs` prefix"""
    sample_file_path = filesystem + "test_file.txt"
    assert zenml.io.utils.is_gcs_path(sample_file_path) is False


def test_list_dir_returns_a_list_of_file_names(tmp_path):
    """list_dir should return a list of file names inside the queried directory"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.list_dir(str(tmp_path)) == [temp_file.name]


def test_list_dir_returns_a_list_of_file_paths(tmp_path):
    """list_dir should return a list of file paths inside
    the queried directory"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.list_dir(str(tmp_path)) == [
            os.path.join(tmp_path, temp_file.name)
        ]


def test_list_dir_returns_one_result_for_one_file(tmp_path):
    """list_dir should return only one result, when there is only
    one file created"""
    fileio.create_file_if_not_exists(
        os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    )
    assert len(fileio.list_dir(str(tmp_path))) == 1


@pytest.fixture(scope="module")
@given(sample_file=text())
def test_list_dir_returns_empty_list_when_dir_doesnt_exist(
    sample_file, tmp_path
):
    """list_dir should return an empty list when the directory"""
    """doesn't exist"""
    not_a_real_dir = os.path.join(tmp_path, sample_file)
    assert isinstance(fileio.list_dir(not_a_real_dir), list)


def test_get_filesystem() -> None:
    """Test the right filesystem is returned for local paths"""
    assert issubclass(fileio._get_filesystem("/"), LocalFilesystem)


@pytest.fixture(scope="module")
@given(not_a_file=text(min_size=1))
def test_open_returns_error_when_file_nonexistent(
    tmp_path, not_a_file: str
) -> None:
    """Test that open returns a file object"""
    with pytest.raises(NotFoundError):
        fileio.open(os.path.join(tmp_path, not_a_file), "rb")


@pytest.fixture(scope="module")
@given(random_file=text(min_size=1))
def test_open_returns_file_object_when_file_exists(
    tmp_path, random_file: str
) -> None:
    """Test that open returns a file object"""
    with fileio.open(os.path.join(tmp_path, random_file), "w") as _:
        assert isinstance(
            fileio.open(os.path.join(tmp_path, random_file), "rb"),
            FileIO,
        )


def test_copy_moves_file_to_new_location(tmp_path) -> None:
    """Test that copy moves the file to the new location"""
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "test_file.txt"))
    fileio.copy(
        os.path.join(tmp_path, "test_file.txt"),
        os.path.join(tmp_path, "test_file2.txt"),
    )
    assert os.path.exists(os.path.join(tmp_path, "test_file2.txt"))


def test_copy_raises_error_when_file_exists(tmp_path) -> None:
    """Test that copy raises an error when the file already exists in
    the desired location"""
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "test_file.txt"))
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "test_file2.txt"))
    with pytest.raises(OSError):
        fileio.copy(
            os.path.join(tmp_path, "test_file.txt"),
            os.path.join(tmp_path, "test_file2.txt"),
        )


def test_file_exists_function(tmp_path) -> None:
    """Test that file_exists returns True when the file exists"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.file_exists(temp_file.name)


def test_file_exists_when_file_doesnt_exist(tmp_path) -> None:
    """Test that file_exists returns False when the file does not exist"""
    assert not fileio.file_exists(os.path.join(tmp_path, "not_a_file.txt"))


def test_remove_function(tmp_path) -> None:
    """Test that remove function actually removes a file"""
    new_file_path = os.path.join(tmp_path, "test_file.txt")
    fileio.create_file_if_not_exists(new_file_path)
    assert fileio.file_exists(new_file_path)
    fileio.remove(new_file_path)
    assert not os.path.exists(new_file_path)


def test_glob_function(tmp_path) -> None:
    """Test that glob returns a list of files"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        files = fileio.glob(str(tmp_path) + "/*")
        assert isinstance(files, list)
        assert temp_file.name in files


def test_make_dirs(tmp_path) -> None:
    """Test that make_dirs creates a directory"""
    fileio.make_dirs(os.path.join(tmp_path, "not_a_dir"))
    assert os.path.exists(os.path.join(tmp_path, "not_a_dir"))


def test_make_dirs_when_recursive(tmp_path) -> None:
    """Test that make_dirs creates a directory"""
    fileio.make_dirs(os.path.join(tmp_path, "not_a_dir/still_not_a_dir"))
    assert os.path.exists(os.path.join(tmp_path, "not_a_dir/still_not_a_dir"))


def test_mkdir_function(tmp_path) -> None:
    """Test that mkdir creates a directory"""
    fileio.mkdir(os.path.join(tmp_path, "not_a_dir"))
    assert os.path.exists(os.path.join(tmp_path, "not_a_dir"))


def test_mkdir_function_when_parent_doesnt_exist(tmp_path) -> None:
    """Test that mkdir creates a directory"""
    with pytest.raises(NotFoundError):
        fileio.mkdir(os.path.join(tmp_path, "not_a_dir/still_not_a_dir"))


def test_rename_function(tmp_path) -> None:
    """Test that rename renames a file"""
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "test_file.txt"))
    fileio.rename(
        os.path.join(tmp_path, "test_file.txt"),
        os.path.join(tmp_path, "new_file.txt"),
    )
    assert os.path.exists(os.path.join(tmp_path, "new_file.txt"))
    assert not os.path.exists(os.path.join(tmp_path, "test_file.txt"))


def test_rename_function_raises_error_if_file_already_exists(tmp_path) -> None:
    """Test that rename raises an error if the file already exists"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.file_exists(temp_file.name)
        with pytest.raises(OSError):
            with NamedTemporaryFile(dir=tmp_path) as temp_file2:
                fileio.rename(temp_file.name, temp_file2.name)


def test_rm_dir_function(tmp_path) -> None:
    """Test that rm_dir removes a directory"""
    fileio.mkdir(os.path.join(tmp_path, "not_a_dir"))
    fileio.rm_dir(os.path.join(tmp_path, "not_a_dir"))
    assert not os.path.exists(os.path.join(tmp_path, "not_a_dir"))


def test_rm_dir_function_works_recursively(tmp_path) -> None:
    """Test that rm_dir removes a directory recursively"""
    fileio.make_dirs(os.path.join(tmp_path, "not_a_dir/also_not_a_dir"))
    fileio.rm_dir(os.path.join(tmp_path, "not_a_dir/also_not_a_dir"))
    assert not os.path.exists(
        os.path.join(tmp_path, "not_a_dir/also_not_a_dir")
    )


def test_stat_returns_a_stat_result_object(tmp_path) -> None:
    """Test that stat returns a stat result object"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert isinstance(fileio.stat(temp_file.name), os.stat_result)


def test_stat_raises_error_when_file_doesnt_exist(tmp_path) -> None:
    """Test that stat raises an error when the file doesn't exist"""
    with pytest.raises(NotFoundError):
        fileio.stat(os.path.join(tmp_path, "not_a_file.txt"))


def test_walk_returns_an_iterator(tmp_path) -> None:
    """Test that walk returns an iterator"""
    assert isinstance(fileio.walk(str(tmp_path)), Iterable)


def test_create_file_if_not_exists(tmp_path) -> None:
    """Test that create_file_if_not_exists creates a file"""
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "new_file.txt"))
    assert os.path.exists(os.path.join(tmp_path, "new_file.txt"))


def test_create_dir_if_not_exists(tmp_path) -> None:
    """Test that create_dir_if_not_exists creates a directory"""
    fileio.create_dir_if_not_exists(os.path.join(tmp_path, "new_dir"))
    assert os.path.exists(os.path.join(tmp_path, "new_dir"))


def test_create_dir_recursive_if_not_exists(tmp_path) -> None:
    """Test that create_dir_recursive_if_not_exists creates a directory"""
    fileio.create_dir_recursive_if_not_exists(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    assert os.path.exists(os.path.join(tmp_path, "new_dir/new_dir2"))


def test_resolve_relative_path(tmp_path) -> None:
    """Test that resolve_relative_path resolves a relative path"""
    current_working_directory = os.getcwd()
    assert current_working_directory == fileio.resolve_relative_path(".")


def test_copy_dir_copies_dir_from_source_to_destination(tmp_path) -> None:
    """Test that copy_dir copies a directory from source to destination"""
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "new_file.txt"))
    fileio.copy_dir(
        os.path.join(tmp_path),
        os.path.join(tmp_path, "test_dir_copy"),
    )
    assert os.path.exists(os.path.join(tmp_path, "test_dir_copy"))
    assert os.path.exists(os.path.join(tmp_path, "test_dir_copy/new_file.txt"))


def test_move_moves_a_file_from_source_to_destination(tmp_path) -> None:
    """Test that move moves a file from source to destination"""
    fileio.create_file_if_not_exists(os.path.join(tmp_path, "new_file.txt"))
    fileio.move(
        os.path.join(tmp_path, "new_file.txt"),
        os.path.join(tmp_path, "new_file_moved.txt"),
    )
    assert os.path.exists(os.path.join(tmp_path, "new_file_moved.txt"))
    assert not os.path.exists(os.path.join(tmp_path, "new_file.txt"))


def test_move_moves_a_directory_from_source_to_destination(tmp_path) -> None:
    """Test that move moves a directory from source to destination"""
    fileio.create_file_if_not_exists(
        os.path.join(tmp_path, "new_folder/new_file.txt")
    )
    fileio.move(
        os.path.join(tmp_path, "new_folder"),
        os.path.join(tmp_path, "test_dir_moved"),
    )
    assert os.path.exists(os.path.join(tmp_path, "test_dir_moved"))
    assert os.path.exists(os.path.join(tmp_path, "test_dir_moved/new_file.txt"))


def test_get_grandparent_gets_the_grandparent_directory(tmp_path) -> None:
    """Test that get_grandparent gets the grandparent directory"""
    fileio.create_dir_recursive_if_not_exists(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    grandparent = fileio.get_grandparent(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    assert grandparent == Path(tmp_path).stem


def test_get_parent_gets_the_parent_directory(tmp_path) -> None:
    """Test that get_parent gets the parent directory"""
    fileio.create_dir_recursive_if_not_exists(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    parent = fileio.get_parent(os.path.join(tmp_path, "new_dir/new_dir2"))
    assert parent == "new_dir"


def test_convert_to_str_converts_to_string(tmp_path) -> None:
    """Test that convert_to_str converts bytes to a string"""
    assert isinstance(fileio.convert_to_str(bytes(str(tmp_path), "ascii")), str)
    assert fileio.convert_to_str(bytes(str(tmp_path), "ascii")) == str(tmp_path)
