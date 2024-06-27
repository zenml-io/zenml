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

import pathlib
import sys
from contextlib import ExitStack as does_not_raise
from types import BuiltinFunctionType, FunctionType
from uuid import uuid4

import pytest

from tests.unit.pipelines.test_build_utils import (
    StubLocalRepositoryContext,
)
from zenml.config.source import CodeRepositorySource, Source, SourceType
from zenml.utils import code_repository_utils, source_utils

CURRENT_MODULE_PARENT_DIR = str(pathlib.Path(__file__).resolve().parent)


class EmptyClass:
    class NestedClass:
        pass


empty_class_instance = EmptyClass()


def empty_function():
    pass


def test_basic_source_loading():
    """Tests basic source loading."""
    from zenml import client

    assert source_utils.load("zenml.client.Client") is client.Client
    client_source = Source(
        module="zenml.client", attribute="Client", type=SourceType.UNKNOWN
    )
    assert source_utils.load(client_source) is client.Client

    client_module_source = Source(
        module="zenml.client", attribute=None, type=SourceType.INTERNAL
    )
    assert source_utils.load(client_module_source) is client

    function_type_source = Source(
        module=FunctionType.__module__,
        attribute=FunctionType.__name__,
        type=SourceType.BUILTIN,
    )
    assert source_utils.load(function_type_source) is FunctionType

    builtin_function_type_source = Source(
        module=BuiltinFunctionType.__module__,
        attribute=BuiltinFunctionType.__name__,
        type=SourceType.BUILTIN,
    )
    assert (
        source_utils.load(builtin_function_type_source) is BuiltinFunctionType
    )

    with pytest.raises(ModuleNotFoundError):
        source_utils.load("zenml.not_a_module.Class")

    with pytest.raises(AttributeError):
        source_utils.load("zenml.client.NotAClass")


def test_user_source_loading_prepends_source_root(mocker, tmp_path):
    """Tests that user source loading prepends the source root to the python
    path before importing."""
    mocker.patch.object(
        source_utils,
        "get_source_root",
        return_value=str(tmp_path),
    )
    mocker.patch.object(sys, "path", [])

    module_path = tmp_path / "test_module_name.py"
    module_path.write_text("test = 1")

    wrong_source = Source(
        module="test_module_name", attribute="test", type=SourceType.BUILTIN
    )
    with pytest.raises(ModuleNotFoundError):
        source_utils.load(wrong_source)

    # Source of type user prepends the source root to the python path before
    # importing
    correct_source = Source(
        module="test_module_name", attribute="test", type=SourceType.USER
    )
    assert source_utils.load(correct_source) == 1

    # Source of type code repo prepends the source root to the python path
    # before importing
    correct_code_repo_source = CodeRepositorySource(
        module="test_module_name",
        attribute="test",
        type=SourceType.CODE_REPOSITORY,
        repository_id=uuid4(),
        commit="",
        subdirectory="",
    )
    assert source_utils.load(correct_code_repo_source) == 1


def test_basic_source_resolving(mocker):
    """Tests basic source resolving."""
    assert source_utils.resolve(int) == Source(
        module=int.__module__, attribute=int.__name__, type=SourceType.BUILTIN
    )
    assert source_utils.resolve(int) == Source(
        module=int.__module__,
        attribute=int.__name__,
        type=SourceType.BUILTIN,
    )
    assert source_utils.resolve(source_utils) == Source(
        module=source_utils.__name__,
        attribute=None,
        type=SourceType.INTERNAL,
    )
    assert source_utils.resolve(pytest) == Source(
        module=pytest.__name__,
        attribute=None,
        package_name="pytest",
        version=pytest.__version__,
        type=SourceType.DISTRIBUTION_PACKAGE,
    )
    assert source_utils.resolve(type(empty_function)) == Source(
        module=FunctionType.__module__,
        attribute=FunctionType.__name__,
        type=SourceType.BUILTIN,
    )
    assert source_utils.resolve(type(len)) == Source(
        module=BuiltinFunctionType.__module__,
        attribute=BuiltinFunctionType.__name__,
        type=SourceType.BUILTIN,
    )

    # User sources
    mocker.patch.object(
        source_utils,
        "get_source_root",
        return_value=CURRENT_MODULE_PARENT_DIR,
    )

    expected_module_name = __name__.split(".")[-1]

    current_module = sys.modules[__name__]
    assert source_utils.resolve(current_module) == Source(
        module=expected_module_name, attribute=None, type=SourceType.USER
    )
    assert source_utils.resolve(EmptyClass) == Source(
        module=expected_module_name,
        attribute=EmptyClass.__name__,
        type=SourceType.USER,
    )
    assert source_utils.resolve(empty_function) == Source(
        module=expected_module_name,
        attribute=empty_function.__name__,
        type=SourceType.USER,
    )

    # Code repo sources
    clean_local_context = StubLocalRepositoryContext(
        root=CURRENT_MODULE_PARENT_DIR, commit="commit"
    )
    mocker.patch.object(
        code_repository_utils,
        "find_active_code_repository",
        return_value=clean_local_context,
    )

    assert source_utils.resolve(empty_function) == CodeRepositorySource(
        module=expected_module_name,
        attribute=empty_function.__name__,
        type=SourceType.CODE_REPOSITORY,
        repository_id=clean_local_context.code_repository_id,
        commit=clean_local_context.current_commit,
        subdirectory=".",
    )

    dirty_local_context = StubLocalRepositoryContext(
        root=CURRENT_MODULE_PARENT_DIR, commit="commit", has_local_changes=True
    )
    mocker.patch.object(
        code_repository_utils,
        "find_active_code_repository",
        return_value=dirty_local_context,
    )

    assert source_utils.resolve(empty_function) == Source(
        module=expected_module_name,
        attribute=empty_function.__name__,
        type=SourceType.USER,
    )


def test_source_resolving_fails_for_non_toplevel_classes_and_functions(mocker):
    """Tests that source resolving fails for classes and functions that are
    not defined at the module top level."""
    mocker.patch.object(
        source_utils,
        "get_source_root",
        return_value=CURRENT_MODULE_PARENT_DIR,
    )

    def inline_function():
        pass

    with pytest.raises(RuntimeError):
        source_utils.resolve(EmptyClass.NestedClass)

    with pytest.raises(RuntimeError):
        source_utils.resolve(inline_function)


def test_module_type_detection(mocker):
    """Tests detecting the correct source type for a module/file."""
    builtin_module = sys.modules[int.__module__]
    assert source_utils.get_source_type(builtin_module) == SourceType.BUILTIN

    standard_lib_module = sys.modules[int.__module__]
    assert (
        source_utils.get_source_type(standard_lib_module) == SourceType.BUILTIN
    )

    internal_module = sys.modules[source_utils.__name__]
    assert source_utils.get_source_type(internal_module) == SourceType.INTERNAL
    assert source_utils.is_internal_module(internal_module.__name__)

    distribution_package_module = sys.modules[pytest.__name__]
    assert (
        source_utils.get_source_type(distribution_package_module)
        == SourceType.DISTRIBUTION_PACKAGE
    )
    assert source_utils.is_distribution_package_file(
        distribution_package_module.__file__,
        module_name=distribution_package_module.__name__,
    )

    mocker.patch.object(
        source_utils,
        "get_source_root",
        return_value=CURRENT_MODULE_PARENT_DIR,
    )

    user_module = sys.modules[EmptyClass.__module__]
    assert source_utils.get_source_type(user_module) == SourceType.USER
    assert source_utils.is_user_file(user_module.__file__)


def test_prepend_python_path():
    """Tests that the context manager prepends an element to the pythonpath
    and removes it again after the context is exited."""
    path = "definitely_not_part_of_pythonpath"

    assert path not in sys.path
    with source_utils.prepend_python_path(path):
        assert sys.path[0] == path

    assert path not in sys.path


def test_setting_a_custom_source_root():
    """Tests setting and resetting a custom source root."""
    initial_source_root = source_utils.get_source_root()
    source_utils.set_custom_source_root(source_root="custom_source_root")
    assert source_utils.get_source_root() == "custom_source_root"
    source_utils.set_custom_source_root(source_root=None)
    assert source_utils.get_source_root() == initial_source_root


def test_validating_source_classes(mocker):
    """Tests validating the class of a source."""
    mocker.patch.object(
        source_utils,
        "get_source_root",
        return_value=CURRENT_MODULE_PARENT_DIR,
    )

    instance_source = f"{__name__}.empty_class_instance"

    with pytest.raises(TypeError):
        source_utils.load_and_validate_class(
            instance_source, expected_class=EmptyClass
        )

    assert not source_utils.validate_source_class(
        instance_source, expected_class=EmptyClass
    )

    class_source = f"{__name__}.{EmptyClass.__name__}"
    with pytest.raises(TypeError):
        source_utils.load_and_validate_class(class_source, expected_class=int)

    assert not source_utils.validate_source_class(
        class_source, expected_class=int
    )

    with does_not_raise():
        source_utils.load_and_validate_class(
            class_source, expected_class=EmptyClass
        )

    assert source_utils.validate_source_class(
        class_source, expected_class=EmptyClass
    )


def test_package_utility_functions():
    """Tests getting package name and version."""
    from pytest import ExitCode

    assert (
        source_utils._get_package_for_module(module_name=ExitCode.__module__)
        == "pytest"
    )
    assert (
        source_utils._get_package_version(package_name="pytest")
        == pytest.__version__
    )

    assert (
        source_utils._get_package_for_module(
            module_name="non_existent_module.submodule"
        )
        is None
    )
    assert (
        source_utils._get_package_version(package_name="non_existent_package")
        is None
    )
