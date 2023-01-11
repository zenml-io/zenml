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
from zenml.io import fileio
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


def test_copy_dir_works(tmp_path):
    """Tests copying directory."""
    dir_path = os.path.join(tmp_path, "test")
    fileio.create_dir_if_not_exists(dir_path)
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
    fileio.create_dir_if_not_exists(dir_path)
    file_path1 = os.path.join(dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path1, "some_content_about_aria")

    new_dir_path = os.path.join(tmp_path, "test2")
    fileio.create_dir_if_not_exists(new_dir_path)
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
    fileio.create_dir_if_not_exists(dir_path)
    file_path1 = os.path.join(dir_path, "test.txt")
    io_utils.create_file_if_not_exists(file_path1, "some_content_about_aria")

    new_dir_path = os.path.join(tmp_path, "test2")
    fileio.create_dir_if_not_exists(new_dir_path)
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
