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

import pytest

from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.utils import io_utils


def test_get_global_config_directory_works():
    """Tests global config directory."""
    gc_dir = io_utils.get_global_config_directory()
    assert gc_dir is not None
    assert isinstance(gc_dir, str)
    assert os.path.exists(gc_dir)
    assert os.path.isdir(gc_dir)


def test_get_global_config_directory_works_with_env_var():
    """Tests global config directory."""
    os.environ[ENV_ZENML_CONFIG_PATH] = "/"
    gc_dir = io_utils.get_global_config_directory()
    assert gc_dir is not None
    assert isinstance(gc_dir, str)
    assert os.path.exists(gc_dir)
    assert os.path.isdir(gc_dir)
    assert gc_dir == "/"


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


def find_files_works(tmp_path):
    """Tests finding files."""
    file_path = os.path.join(tmp_path, "test.txt")
    buried_file_path = os.path.join(tmp_path, "test", "buried.txt")

    io_utils.write_file_contents_as_string(file_path, "aria_best_cat")
    io_utils.write_file_contents_as_string(buried_file_path, "aria_best_cat")

    assert io_utils.find_files(tmp_path, "test.txt") == [file_path]
    assert io_utils.find_files(tmp_path, "test*") == [file_path]
    assert io_utils.find_files(tmp_path, "test") == [file_path]
    assert io_utils.find_files(tmp_path, "buried.txt") == [buried_file_path]
    assert io_utils.find_files(tmp_path, "buried*") == [buried_file_path]
    assert io_utils.find_files(tmp_path, "buried") == [buried_file_path]
    assert io_utils.find_files(tmp_path, "txt") == [
        file_path,
        buried_file_path,
    ]
    assert io_utils.find_files(tmp_path, "*") == [
        file_path,
        buried_file_path,
    ]
    assert io_utils.find_files(tmp_path, "") == [
        file_path,
        buried_file_path,
    ]
    assert len(io_utils.find_files(tmp_path, "*")) == 2

    assert len(io_utils.find_files(tmp_path, "not_a_file.txt")) == 0


def test_is_remote_works():
    """Tests remote file detection."""
    assert io_utils.is_remote("gs://test")
    assert io_utils.is_remote("s3://test")
    assert io_utils.is_remote("hdfs://test")
    assert io_utils.is_remote("az://test")
    assert io_utils.is_remote("abfs://test")
    assert not io_utils.is_remote("test")
    assert not io_utils.is_remote("file://test")
    assert not io_utils.is_remote("file:///test")
    assert not io_utils.is_remote("/test")
    assert not io_utils.is_remote("test.txt")
    assert isinstance(io_utils.is_remote("test.txt"), bool)


def test_create_file_if_not_exists_works(tmp_path):
    """Tests file creation."""
    file_path = os.path.join(tmp_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path, "some_content_about_aria")
    assert os.path.exists(file_path)
    assert os.path.isfile(file_path)
    with open(file_path, "r") as f:
        assert f.read() == "some_content_about_aria"

    io_utils.create_file_if_not_exists(file_path, "some_content_about_blupus")
    assert os.path.exists(file_path)
    assert os.path.isfile(file_path)
    with open(file_path, "r") as f:
        assert f.read() == "some_content_about_aria"


def test_create_dir_if_not_exists_works(tmp_path):
    """Tests directory creation."""
    dir_path = os.path.join(tmp_path, "test")
    io_utils.create_dir_if_not_exists(dir_path)
    assert os.path.exists(dir_path)
    assert os.path.isdir(dir_path)


def test_create_dir_recursive_if_not_exists_works(tmp_path):
    """Tests directory creation."""
    dir_path = os.path.join(tmp_path, "test", "test2")
    io_utils.create_dir_recursive_if_not_exists(dir_path)
    assert os.path.exists(dir_path)
    assert os.path.isdir(dir_path)


def test_resolve_relative_path_works(tmp_path):
    """Tests resolving relative path."""
    file_path = os.path.join(tmp_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path, "some_content_about_aria")
    relative_path = os.path.relpath(file_path)
    assert relative_path != file_path
    assert io_utils.resolve_relative_path(relative_path) == file_path


def test_resolving_relative_remote_path_returns_path():
    """Tests resolving relative remote path for remote paths."""
    relative_path = "s3://test/test.txt"
    assert io_utils.resolve_relative_path(relative_path) == relative_path
