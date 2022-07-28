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

from zenml.artifacts.data_artifact import DataArtifact
from zenml.materializers.built_in_materializer import (
    BuiltInMaterializer,
    BytesMaterializer,
)


def _test_materialization(
    type_,
    example,
    materializer_class=BuiltInMaterializer,
):
    materializer = materializer_class(DataArtifact())
    data_path = materializer.data_path  # assumes materializer has this defined
    try:
        assert not os.path.exists(data_path)
        materializer.handle_return(example)
        assert os.path.exists(data_path)
        materializer.handle_input(type_)
    finally:
        if os.path.exists(data_path):
            os.remove(data_path)


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
    _test_materialization(
        type_=bytes, example=b"", materializer_class=BytesMaterializer
    )


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
