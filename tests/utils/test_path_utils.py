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
from tempfile import NamedTemporaryFile, TemporaryDirectory
from types import GeneratorType

import pytest
from tfx.utils.io_utils import _REMOTE_FS_PREFIX

from zenml.utils import path_utils

BAD_REMOTE_PREFIXES = ["http://", "12345", "----"]


def test_walk_function_returns_a_generator_object():
    """Check walk function returns a generator object"""
    with TemporaryDirectory() as temp_dir:
        assert isinstance(path_utils.walk(temp_dir), GeneratorType)


def test_is_root_when_true():
    """Check function returns true if path is the root"""
    assert path_utils.is_root("/")


def test_is_root_when_false():
    """Check function returns false if path isn't the root"""
    with TemporaryDirectory() as temp_dir:
        assert path_utils.is_root(temp_dir) is False


def test_is_dir_when_true():
    """Returns true when path refers to a directory"""
    with TemporaryDirectory() as temp_dir:
        assert path_utils.is_dir(temp_dir)


def test_is_dir_when_false():
    """Returns false when path doesn't refer to a directory"""
    with NamedTemporaryFile() as temp_file:
        assert path_utils.is_dir(temp_file.name) is False


def test_find_files_returns_generator_object_when_file_present():
    """Check function finds a file within a temporary directory"""
    with TemporaryDirectory() as temp_dir:
        temp_file_name = "abcdefg.txt"
        temp_file_path = os.path.join(temp_dir, temp_file_name)
        open(temp_file_path, "x")
        assert isinstance(
            path_utils.find_files(temp_dir, "abc*.*"), GeneratorType
        )


def test_find_files_when_file_present():
    """Check function finds a file within a temporary directory"""
    with TemporaryDirectory() as temp_dir:
        temp_file_name = "abcdefg.txt"
        temp_file_path = os.path.join(temp_dir, temp_file_name)
        open(temp_file_path, "x")
        assert path_utils.find_files(temp_dir, "abc*.*")


def test_find_files_when_file_absent():
    """Function returns None when it doesn't find a file"""
    with TemporaryDirectory() as temp_dir:
        temp_file_name = "qqq.txt"
        temp_file_path = os.path.join(temp_dir, temp_file_name)
        open(temp_file_path, "x")
        assert path_utils.find_files(temp_dir, "abc*.*")


@pytest.mark.parametrize("filesystem", _REMOTE_FS_PREFIX)
def test_is_remote_when_using_remote_prefix(filesystem):
    """Returns true when path starts with one of the TFX remote file prefixes"""
    some_random_path = os.path.join(filesystem + "some_directory")
    assert path_utils.is_remote(some_random_path)


@pytest.mark.parametrize("filesystem", BAD_REMOTE_PREFIXES)
def test_is_remote_when_using_non_remote_prefix(filesystem):
    """"""
    some_random_path = os.path.join(filesystem + "some_directory")
    assert path_utils.is_remote(some_random_path) is False
