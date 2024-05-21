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

import os
import platform
import string
from pathlib import Path
from types import GeneratorType

import pytest
from hypothesis import given
from hypothesis.strategies import text

from zenml.constants import ENV_ZENML_CONFIG_PATH, REMOTE_FS_PREFIX
from zenml.utils import io_utils

TEMPORARY_FILE_NAME = "a_file.txt"
TEMPORARY_FILE_SEARCH_PREFIX = "a_f*.*"
ALPHABET = string.ascii_letters


def test_get_global_config_directory_works():
    """Tests global config directory."""
    gc_dir = io_utils.get_global_config_directory()
    assert gc_dir is not None
    assert isinstance(gc_dir, str)
    assert os.path.exists(gc_dir)
    assert os.path.isdir(gc_dir)


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="This specific test only works on Unix systems",
)
def test_get_global_config_directory_works_with_env_var():
    """Tests global config directory."""
    orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)
    try:
        os.environ[ENV_ZENML_CONFIG_PATH] = "/"
        gc_dir = io_utils.get_global_config_directory()
        assert gc_dir is not None
        assert isinstance(gc_dir, str)
        assert os.path.exists(gc_dir)
        assert os.path.isdir(gc_dir)
        assert gc_dir == "/"
    finally:
        if orig_config_path is not None:
            os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
        else:
            del os.environ[ENV_ZENML_CONFIG_PATH]


def test_write_file_contents_as_string_works(tmp_path):
    """Tests writing to file."""
    file_path = os.path.join(tmp_path, "test.txt")
    io_utils.write_file_contents_as_string(file_path, "test")
    assert os.path.exists(file_path)
    assert os.path.isfile(file_path)
    with open(file_path, "r") as f:
        assert f.read() == "test"


def test_write_file_contents_as_string_fails_with_non_string_types(tmp_path):
    """Tests writing to file."""
    file_path = os.path.join(tmp_path, "test.txt")
    with pytest.raises(ValueError):
        io_utils.write_file_contents_as_string(file_path, 1)


def test_read_file_contents_as_string_works(tmp_path):
    """Tests reading from file."""
    file_path = os.path.join(tmp_path, "test.txt")
    io_utils.write_file_contents_as_string(file_path, "aria_best_cat")
    assert io_utils.read_file_contents_as_string(file_path) == "aria_best_cat"


def test_read_file_contents_as_string_raises_error_when_file_not_exists(
    tmp_path,
):
    """Tests reading from file."""
    file_path = os.path.join(tmp_path, "test.txt")
    with pytest.raises(FileNotFoundError):
        io_utils.read_file_contents_as_string(file_path)


def test_copy_dir_works(tmp_path):
    """Tests copying directory."""
    dir_path = os.path.join(tmp_path, "test")
    io_utils.create_dir_if_not_exists(dir_path)
    file_path = os.path.join(dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path, "some_content_about_aria")

    new_dir_path = os.path.join(tmp_path, "test2")
    io_utils.copy_dir(dir_path, new_dir_path)
    assert os.path.exists(new_dir_path)
    assert os.path.isdir(new_dir_path)
    assert os.path.exists(os.path.join(new_dir_path, "test.txt"))
    assert os.path.isfile(os.path.join(new_dir_path, "test.txt"))
    with open(os.path.join(new_dir_path, "test.txt"), "r") as f:
        assert f.read() == "some_content_about_aria"


def test_copy_dir_overwriting_works(tmp_path):
    """Tests copying directory overwriting."""
    dir_path = os.path.join(tmp_path, "test")
    io_utils.create_dir_if_not_exists(dir_path)
    file_path1 = os.path.join(dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path1, "some_content_about_aria")

    new_dir_path = os.path.join(tmp_path, "test2")
    io_utils.create_dir_if_not_exists(new_dir_path)
    file_path2 = os.path.join(new_dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path2, "some_content_about_blupus")

    io_utils.copy_dir(dir_path, new_dir_path, overwrite=True)
    assert os.path.exists(new_dir_path)
    assert os.path.isdir(new_dir_path)
    assert os.path.exists(file_path2)
    assert os.path.isfile(file_path2)
    with open(file_path2, "r") as f:
        assert f.read() == "some_content_about_aria"


def test_copy_dir_throws_error_if_overwriting(tmp_path):
    """Tests copying directory throwing error if overwriting."""
    dir_path = os.path.join(tmp_path, "test")
    io_utils.create_dir_if_not_exists(dir_path)
    file_path1 = os.path.join(dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path1, "some_content_about_aria")

    new_dir_path = os.path.join(tmp_path, "test2")
    io_utils.create_dir_if_not_exists(new_dir_path)
    file_path2 = os.path.join(new_dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path2, "some_content_about_blupus")

    with pytest.raises(FileExistsError):
        io_utils.copy_dir(dir_path, new_dir_path, overwrite=False)

    assert (
        io_utils.read_file_contents_as_string(file_path1)
        == "some_content_about_aria"
    )

    assert (
        io_utils.read_file_contents_as_string(file_path2)
        == "some_content_about_blupus"
    )


def test_is_root_when_true():
    """Check is_root returns true if path is the root"""
    assert io_utils.is_root("/")


def test_is_root_when_false(tmp_path):
    """Check is_root returns false if path isn't the root"""
    assert io_utils.is_root(tmp_path) is False


def test_find_files_returns_generator_object_when_file_present(tmp_path):
    """find_files returns a generator object when it finds a file"""
    temp_file = os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    with open(temp_file, "w"):
        assert isinstance(
            io_utils.find_files(str(tmp_path), TEMPORARY_FILE_SEARCH_PREFIX),
            GeneratorType,
        )


def test_find_files_when_file_present(tmp_path):
    """find_files locates a file within a temporary directory"""
    temp_file = os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    with open(temp_file, "w"):
        assert (
            next(
                io_utils.find_files(
                    str(tmp_path), TEMPORARY_FILE_SEARCH_PREFIX
                )
            )
            is not None
        )


def test_find_files_when_file_absent(tmp_path):
    """find_files returns None when it doesn't find a file"""
    temp_file = os.path.join(tmp_path, TEMPORARY_FILE_NAME)
    with open(temp_file, "w"):
        with pytest.raises(StopIteration):
            assert next(io_utils.find_files(str(tmp_path), "abc*.*"))


@pytest.mark.parametrize("filesystem", REMOTE_FS_PREFIX)
def test_is_remote_when_using_remote_prefix(filesystem):
    """is_remote returns True when path starts with one of
    the ZenML remote file prefixes"""
    some_random_path = os.path.join(f"{filesystem}some_directory")
    assert io_utils.is_remote(some_random_path)


@given(text())
def test_is_remote_when_using_non_remote_prefix(filesystem):
    """is_remote returns False when path doesn't start with
    a remote prefix"""
    some_random_path = os.path.join(f"{filesystem}some_directory")
    assert io_utils.is_remote(some_random_path) is False


def test_create_file_if_not_exists(tmp_path) -> None:
    """Test that create_file_if_not_exists creates a file"""
    io_utils.create_file_if_not_exists(os.path.join(tmp_path, "new_file.txt"))
    assert os.path.exists(os.path.join(tmp_path, "new_file.txt"))


def test_create_file_if_not_exists_does_not_overwrite(tmp_path) -> None:
    """Test that create_file_if_not_exists doesn't overwrite an existing file"""
    temporary_file = os.path.join(tmp_path, "new_file.txt")
    io_utils.create_file_if_not_exists(temporary_file)
    with open(temporary_file, "w") as f:
        f.write("Aria is a good cat")
    io_utils.create_file_if_not_exists(temporary_file)
    with open(temporary_file, "r") as f:
        assert f.read() == "Aria is a good cat"


def test_create_dir_if_not_exists(tmp_path) -> None:
    """Test that create_dir_if_not_exists creates a directory"""
    io_utils.create_dir_if_not_exists(os.path.join(tmp_path, "new_dir"))
    assert os.path.exists(os.path.join(tmp_path, "new_dir"))


def test_create_dir_recursive_if_not_exists(tmp_path) -> None:
    """Test that create_dir_recursive_if_not_exists creates a directory"""
    io_utils.create_dir_recursive_if_not_exists(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    assert os.path.exists(os.path.join(tmp_path, "new_dir/new_dir2"))


def test_resolve_relative_path(tmp_path) -> None:
    """Test that resolve_relative_path resolves a relative path"""
    current_working_directory = os.getcwd()
    assert current_working_directory == io_utils.resolve_relative_path(".")


def test_copy_dir_copies_dir_from_source_to_destination(tmp_path) -> None:
    """Test that copy_dir copies a directory from source to destination"""
    source_dir = os.path.join(tmp_path)
    target_dir = os.path.join(tmp_path, "test_dir_copy")
    source_file = os.path.join(source_dir, "new_file.txt")
    target_file = os.path.join(target_dir, "new_file.txt")
    io_utils.create_file_if_not_exists(source_file)
    assert os.path.exists(source_file)
    assert not os.path.exists(target_dir)
    io_utils.copy_dir(source_dir, target_dir)
    assert os.path.exists(target_dir)
    assert os.path.exists(target_file)


def test_move_moves_a_file_from_source_to_destination(tmp_path) -> None:
    """Test that move moves a file from source to destination"""
    io_utils.create_file_if_not_exists(os.path.join(tmp_path, "new_file.txt"))
    io_utils.move(
        os.path.join(tmp_path, "new_file.txt"),
        os.path.join(tmp_path, "new_file_moved.txt"),
    )
    assert os.path.exists(os.path.join(tmp_path, "new_file_moved.txt"))
    assert not os.path.exists(os.path.join(tmp_path, "new_file.txt"))


def test_move_moves_a_directory_from_source_to_destination(tmp_path) -> None:
    """Test that move moves a directory from source to destination"""
    io_utils.create_file_if_not_exists(
        os.path.join(tmp_path, "new_folder/new_file.txt")
    )
    io_utils.move(
        os.path.join(tmp_path, "new_folder"),
        os.path.join(tmp_path, "test_dir_moved"),
    )
    assert os.path.exists(os.path.join(tmp_path, "test_dir_moved"))
    assert os.path.exists(
        os.path.join(tmp_path, "test_dir_moved/new_file.txt")
    )


def test_get_grandparent_gets_the_grandparent_directory(tmp_path) -> None:
    """Test that get_grandparent gets the grandparent directory"""
    io_utils.create_dir_recursive_if_not_exists(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    grandparent = io_utils.get_grandparent(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    assert grandparent == Path(tmp_path).stem


def test_get_parent_gets_the_parent_directory(tmp_path) -> None:
    """Test that get_parent gets the parent directory"""
    io_utils.create_dir_recursive_if_not_exists(
        os.path.join(tmp_path, "new_dir/new_dir2")
    )
    parent = io_utils.get_parent(os.path.join(tmp_path, "new_dir/new_dir2"))
    assert parent == "new_dir"
