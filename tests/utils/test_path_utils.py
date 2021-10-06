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

from tempfile import NamedTemporaryFile, TemporaryDirectory
from types import GeneratorType

from zenml.utils import path_utils


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
