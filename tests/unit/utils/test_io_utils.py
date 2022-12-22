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
