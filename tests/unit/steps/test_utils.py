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
import logging
import typing
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
from numpy import ndarray
from typing_extensions import Annotated

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.enums import ArtifactType
from zenml.exceptions import StepInterfaceError
from zenml.orchestrators.step_runner import OutputSignature
from zenml.steps.utils import (
    get_resolved_signature,
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


def func_with_single_artifact_config_output() -> Annotated[
    int, ArtifactConfig(name="custom_output")
]:
    return 1


def func_with_single_output_with_both_name_and_artifact_config() -> Annotated[
    int, "custom_output", ArtifactConfig()
]:
    return 1


def func_with_tuple_output() -> Tuple[int, ...]:
    return_value = (1, 2)
    return return_value


def func_with_annotated_tuple_output() -> Annotated[
    Tuple[int, int], "custom_output"
]:
    return_value = (1, 2)
    return return_value


def func_with_multiple_outputs() -> Tuple[int, int]:
    return 1, 2


def func_with_multiple_annotated_outputs() -> Tuple[
    Annotated[int, "custom_output"], int
]:
    return 1, 2


def func_with_multiple_annotated_outputs_and_artifact_config() -> Tuple[
    Annotated[int, ArtifactConfig(name="custom_output")], int
]:
    return 1, 2


def func_with_multiple_annotated_outputs_and_model_artifact_config() -> Tuple[
    Annotated[
        int,
        ArtifactConfig(name="custom_output", artifact_type=ArtifactType.MODEL),
    ],
    int,
]:
    return 1, 2


def func_with_multiple_annotated_outputs_and_deployment_artifact_config() -> (
    Tuple[
        Annotated[
            int,
            ArtifactConfig(
                name="custom_output", artifact_type=ArtifactType.SERVICE
            ),
        ],
        int,
    ]
):
    return 1, 2


@pytest.mark.parametrize(
    "func,expected_output",
    [
        (func_with_no_output_annotation_and_no_return, {}),
        (
            func_with_no_output_annotation_and_return,
            {
                "output": OutputSignature(
                    resolved_annotation=Any,
                    artifact_config=None,
                    has_custom_name=False,
                )
            },
        ),
        (
            func_with_single_output,
            {
                "output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                )
            },
        ),
        (
            func_with_single_annotated_output,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(name="custom_output"),
                    has_custom_name=True,
                )
            },
        ),
        (
            func_with_single_artifact_config_output,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(name="custom_output"),
                    has_custom_name=True,
                )
            },
        ),
        (
            func_with_single_output_with_both_name_and_artifact_config,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(name="custom_output"),
                    has_custom_name=True,
                )
            },
        ),
        (
            func_with_tuple_output,
            {
                "output": OutputSignature(
                    resolved_annotation=tuple,
                    artifact_config=None,
                    has_custom_name=False,
                )
            },
        ),
        (
            func_with_annotated_tuple_output,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=tuple,
                    artifact_config=ArtifactConfig(name="custom_output"),
                    has_custom_name=True,
                )
            },
        ),
        (
            func_with_multiple_outputs,
            {
                "output_0": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                ),
                "output_1": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                ),
            },
        ),
        (
            func_with_multiple_annotated_outputs,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(name="custom_output"),
                    has_custom_name=True,
                ),
                "output_1": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                ),
            },
        ),
        (
            func_with_multiple_annotated_outputs_and_artifact_config,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(name="custom_output"),
                    has_custom_name=True,
                ),
                "output_1": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                ),
            },
        ),
        (
            func_with_multiple_annotated_outputs_and_model_artifact_config,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(
                        name="custom_output", artifact_type=ArtifactType.MODEL
                    ),
                    has_custom_name=True,
                ),
                "output_1": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                ),
            },
        ),
        (
            func_with_multiple_annotated_outputs_and_deployment_artifact_config,
            {
                "custom_output": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=ArtifactConfig(
                        name="custom_output",
                        artifact_type=ArtifactType.SERVICE,
                    ),
                    has_custom_name=True,
                ),
                "output_1": OutputSignature(
                    resolved_annotation=int,
                    artifact_config=None,
                    has_custom_name=False,
                ),
            },
        ),
    ],
)
def test_step_output_annotation_parsing(func, expected_output):
    assert parse_return_type_annotations(func, {}) == expected_output


def func_with_multiple_annotations() -> Annotated[int, "a", "b"]:
    return 1


def func_with_multiple_artifact_configs() -> Annotated[
    int, ArtifactConfig(), ArtifactConfig()
]:
    return 1


def func_with_ambiguous_output_name() -> Annotated[
    int, "a", ArtifactConfig(name="b")
]:
    return 1


def func_with_non_string_annotation() -> Annotated[int, 1]:
    return 1


def func_with_ellipsis_annotation() -> Tuple[int, ...]:
    return 1, 2, 3


def func_with_duplicate_output_name() -> Tuple[
    Annotated[int, "custom_output"], Annotated[int, "custom_output"]
]:
    return 1, 1


@pytest.mark.parametrize(
    "func,exception",
    [
        (func_with_multiple_annotations, ValueError),
        (func_with_non_string_annotation, ValueError),
        (func_with_multiple_artifact_configs, ValueError),
        (func_with_ambiguous_output_name, ValueError),
        (func_with_ellipsis_annotation, RuntimeError),
        (func_with_duplicate_output_name, RuntimeError),
    ],
)
def test_invalid_step_output_annotations(func, exception):
    with pytest.raises(exception):
        parse_return_type_annotations(func, {})


def test_get_resolved_signature_resolves_stringized_parameter():
    def f(x: "int") -> None:
        pass

    sig = get_resolved_signature(f)
    assert sig.parameters["x"].annotation is int


def test_get_resolved_signature_resolves_stringized_return():
    def f() -> "int":
        return 1

    sig = get_resolved_signature(f)
    assert sig.return_annotation is int


def test_get_resolved_signature_preserves_annotated_string_metadata():
    def f() -> "Annotated[int, 'custom_name']":
        return 1

    sig = get_resolved_signature(f)
    assert sig.return_annotation == Annotated[int, "custom_name"]


def test_get_resolved_signature_preserves_annotated_artifact_config():
    def f() -> "Annotated[int, ArtifactConfig(name='custom_name')]":
        return 1

    sig = get_resolved_signature(f)
    args = typing.get_args(sig.return_annotation)
    assert args[0] is int
    assert isinstance(args[1], ArtifactConfig)
    assert args[1].name == "custom_name"


def test_get_resolved_signature_resolves_stringized_tuple():
    def f() -> "Tuple[int, str]":
        return 1, "x"

    sig = get_resolved_signature(f)
    assert sig.return_annotation == Tuple[int, str]


def test_get_resolved_signature_resolves_stringized_optional():
    def f(x: "Optional[int]") -> None:
        pass

    sig = get_resolved_signature(f)
    assert sig.parameters["x"].annotation == Optional[int]


def test_get_resolved_signature_preserves_unannotated_parameter():
    def f(x, y: "int") -> None:
        pass

    sig = get_resolved_signature(f)
    assert sig.parameters["x"].annotation is inspect.Parameter.empty
    assert sig.parameters["y"].annotation is int


def test_get_resolved_signature_falls_back_to_any_for_unresolvable_parameter(
    caplog,
):
    def f(x: "MissingType") -> None:  # noqa: F821
        pass

    with caplog.at_level(logging.WARNING):
        sig = get_resolved_signature(f)

    assert sig.parameters["x"].annotation is Any
    assert any("MissingType" in record.message for record in caplog.records)


def test_get_resolved_signature_raises_for_unresolvable_return():
    def my_step_fn() -> "MissingType":  # noqa: F821
        raise NotImplementedError

    with pytest.raises(StepInterfaceError) as exc_info:
        get_resolved_signature(my_step_fn)

    assert "my_step_fn" in str(exc_info.value)
    assert "MissingType" in str(exc_info.value)


def test_get_resolved_signature_passes_through_live_annotations():
    def f(x: int) -> int:
        return x

    sig = get_resolved_signature(f)
    assert sig.parameters["x"].annotation is int
    assert sig.return_annotation is int


def test_get_resolved_signature_preserves_missing_return_annotation():
    def f(x: "int"):
        pass

    sig = get_resolved_signature(f)
    assert sig.return_annotation is inspect.Signature.empty


def test_stringized_none_return_produces_no_outputs():
    """Regression test: `-> "None"` (as under `from __future__ import
    annotations`) must produce no output artifact, same as `-> None`."""

    def f() -> "None":
        return None

    assert parse_return_type_annotations(f) == {}
