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
from io import FileIO
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


# @pytest.fixture(scope="module")
# @given(sample_file=text())
# def test_list_dir_returns_one_result_for_one_file(tmp_path, sample_file):
#     """list_dir should return only one result, when there is only
#     one file created"""
#     with open(sample_file, "w"):
#         assert len(fileio.list_dir(str(tmp_path))) == 1


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
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        fileio.copy(temp_file.name, os.path.join(tmp_path, "new_file.txt"))
        assert os.path.exists(os.path.join(tmp_path, "new_file.txt"))


def test_copy_raises_error_when_file_exists(tmp_path) -> None:
    """Test that copy raises an error when the file already exists in
    the desired location"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        fileio.copy(temp_file.name, os.path.join(tmp_path, "new_file.txt"))
        with pytest.raises(OSError):
            fileio.copy(temp_file.name, os.path.join(tmp_path, "new_file.txt"))


def test_file_exists_function(tmp_path) -> None:
    """Test that file_exists returns True when the file exists"""
    with NamedTemporaryFile(dir=tmp_path) as temp_file:
        assert fileio.file_exists(temp_file.name)


def test_file_exists_when_file_doesnt_exist(tmp_path) -> None:
    """Test that file_exists returns False when the file does not exist"""
    assert not fileio.file_exists(os.path.join(tmp_path, "not_a_file.txt"))


# def test_remove_function(tmp_path) -> None:
#     """Test that remove function actually removes a file"""
#     with NamedTemporaryFile(dir=tmp_path) as temp_file:
#         assert fileio.file_exists(temp_file.name)
#         fileio.remove(str(temp_file.name)
#         assert not os.path.exists(temp_file.name)


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
