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
import os
import shutil

from zenml.artifacts.data_artifact import DataArtifact
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)


def _test_materialization(
    type_,
    example,
):
    materializer_class = default_materializer_registry[type_]
    mock_artifact = DataArtifact()
    materializer = materializer_class(mock_artifact)
    data_path = os.path.abspath(mock_artifact.uri)
    existing_files = os.listdir(data_path)
    try:
        materializer.handle_return(example)
        new_files = os.listdir(data_path)
        assert len(new_files) > len(existing_files)  # something was written
        loaded_data = materializer.handle_input(type_)
        assert isinstance(loaded_data, type_)  # correct type
        assert loaded_data == example  # correct content
    finally:
        new_files = os.listdir(data_path)
        created_files = [
            filename for filename in new_files if filename not in existing_files
        ]
        for filename in created_files:
            full_path = os.path.join(data_path, filename)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)


def test_basic_type_materialization():
    """Test materialization for `bool`, `float`, `int`, `str` objects."""
    for type_, example in [
        (bool, True),
        (float, 0.0),
        (int, 0),
        (str, ""),
    ]:
        _test_materialization(type_=type_, example=example)


def test_bytes_materialization():
    """Test materialization for `bytes` objects.

    This is a separate test since `bytes` is not JSON serializable.
    """
    _test_materialization(type_=bytes, example=b"")


def test_empty_dict_list_tuple_materialization():
    """Test materialization for empty `dict`, `list`, `tuple` objects."""
    _test_materialization(type_=dict, example={})
    _test_materialization(type_=list, example=[])
    _test_materialization(type_=tuple, example=())


def test_simple_dict_list_tuple_materialization():
    """Test materialization for `dict`, `list`, `tuple` with data."""
    _test_materialization(type_=dict, example={"a": 0, "b": 1, "c": 2})
    _test_materialization(type_=list, example=[0, 1, 2])
    _test_materialization(type_=tuple, example=(0, 1, 2))


def test_list_of_bytes_materialization():
    """Test materialization for lists of bytes."""
    _test_materialization(type_=list, example=[b"0", b"1", b"2"])


def test_dict_of_bytes_materialization():
    """Test materialization for dicts of bytes."""
    _test_materialization(type_=dict, example={"a": b"0", "b": b"1", "c": b"2"})


def test_tuple_of_bytes_materialization():
    """Test materialization for tuples of bytes."""
    _test_materialization(type_=tuple, example=(b"0", b"1", b"2"))


def test_set_materialization():
    """Test materialization for `set` objects."""
    _test_materialization(type_=set, example=set())
    _test_materialization(type_=set, example={1, 2, 3})
    _test_materialization(type_=set, example={b"0", b"1", b"2"})


def test_mixture_of_all_builtin_types():
    """Test a mixture of built-in types as the ultimate stress test."""
    example = [
        {
            "a": (42, 1.0, "aa", True),  # tuple of serializable basic types
            "b": {
                "ba": ["baa", "bab"],
                "bb": [3.7, 1.8],
            },  # dict of lists of serializable basic types
            "c": b"ca",  # bytes (non-serializable)
        },  # non-serializable dict
        {1.0, 2.0, 4, 4},  # set of serializable types
    ]  # non-serializable list
    _test_materialization(type_=list, example=example)
