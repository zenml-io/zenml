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
from typing import Any, Dict, List, Set, Tuple

import pytest
from numpy import ndarray
from typing_extensions import Annotated

from zenml.steps.utils import (
    parse_return_type_annotations,
    resolve_type_annotation,
)


def test_type_annotation_resolving():
    """Tests that resolving type annotations works as expected."""
    assert resolve_type_annotation(Dict) is dict
    assert resolve_type_annotation(List[int]) is list
    assert resolve_type_annotation(Set[str]) is set

    assert resolve_type_annotation(set) is set
    assert resolve_type_annotation(ndarray) is ndarray


def func_with_no_output_annotation_and_no_return(condition):
    if condition:
        return
    else:
        return None


def func_with_no_output_annotation_and_return(condition):
    if condition:
        return 1
    else:
        return


def func_with_single_output() -> int:
    return 1


def func_with_single_annotated_output() -> Annotated[int, "custom_output"]:
    return 1


def func_with_tuple_output() -> Tuple[int, ...]:
    return_value = (1, 2)
    return return_value


def func_with_annotated_tuple_output() -> (
    Annotated[Tuple[int, int], "custom_output"]
):
    return_value = (1, 2)
    return return_value


def func_with_multiple_outputs() -> Tuple[int, int]:
    return 1, 2


def func_with_multiple_annotated_outputs() -> (
    Tuple[Annotated[int, "custom_output"], int]
):
    return 1, 2


@pytest.mark.parametrize(
    "func,expected_output",
    [
        (func_with_no_output_annotation_and_no_return, {}),
        (func_with_no_output_annotation_and_return, {"output": Any}),
        (func_with_single_output, {"output": int}),
        (func_with_single_annotated_output, {"custom_output": int}),
        (func_with_tuple_output, {"output": tuple}),
        (func_with_annotated_tuple_output, {"custom_output": tuple}),
        (func_with_multiple_outputs, {"output_0": int, "output_1": int}),
        (
            func_with_multiple_annotated_outputs,
            {"custom_output": int, "output_1": int},
        ),
    ],
)
def test_step_output_annotation_parsing(func, expected_output):
    assert parse_return_type_annotations(func) == expected_output


def func_with_multiple_annotations() -> Annotated[int, "a", "b"]:
    return 1


def func_with_non_string_annotation() -> Annotated[int, 1]:
    return 1


def func_with_ellipsis_annotation() -> Tuple[int, ...]:
    return 1, 2, 3


def func_with_duplicate_output_name() -> (
    Tuple[Annotated[int, "custom_output"], Annotated[int, "custom_output"]]
):
    return 1, 1


@pytest.mark.parametrize(
    "func,exception",
    [
        (func_with_multiple_annotations, ValueError),
        (func_with_non_string_annotation, ValueError),
        (func_with_ellipsis_annotation, RuntimeError),
        (func_with_duplicate_output_name, RuntimeError),
    ],
)
def test_invalid_step_output_annotations(func, exception):
    with pytest.raises(exception):
        parse_return_type_annotations(func)
