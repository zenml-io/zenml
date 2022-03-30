#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import inspect
import os
import sys
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.repository import Repository
from zenml.utils import source_utils


def test_is_third_party_module():
    """Tests that third party modules get detected correctly."""
    third_party_file = inspect.getfile(pytest.Cache)
    assert source_utils.is_third_party_module(third_party_file)

    non_third_party_file = inspect.getfile(source_utils)
    assert not source_utils.is_third_party_module(non_third_party_file)


def test_get_source():
    """Tests if source of objects is gotten properly."""
    assert source_utils.get_source(pytest.Cache)


def test_get_hashed_source():
    """Tests if hash of objects is computed properly."""
    assert source_utils.get_hashed_source(pytest.Cache)


def test_prepend_python_path():
    """Tests that the context manager prepends an element to the pythonpath and
    removes it again after the context is exited."""
    path_element = "definitely_not_part_of_pythonpath"

    assert path_element not in sys.path
    with source_utils.prepend_python_path(path_element):
        assert sys.path[0] == path_element

    assert path_element not in sys.path


def test_loading_class_by_path_prepends_repo_path(clean_repo, mocker, tmp_path):
    """Tests that loading a class always prepends the active repository root to
    the python path."""

    os.chdir(str(tmp_path))

    Repository.initialize()
    clean_repo.activate_root()

    python_file = clean_repo.root / "some_directory" / "python_file.py"
    python_file.parent.mkdir()
    python_file.write_text("test = 1")

    mocker.patch.object(sys, "path", [])

    with does_not_raise():
        # the repo root should be in the python path right now, so this file
        # can be imported
        source_utils.load_source_path_class("some_directory.python_file.test")

    with pytest.raises(ModuleNotFoundError):
        # the subdirectory will not be in the python path and therefore this
        # import should not work
        source_utils.load_source_path_class("python_file.test")
