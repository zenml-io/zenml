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

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.enums import ArtifactType
from zenml.orchestrators.step_runner import OutputSignature
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


# ---------------------------------------------------------------------------
# Tests for string annotation resolution (from __future__ import annotations)
# ---------------------------------------------------------------------------


def func_with_string_return_annotation() -> "int":
    return 1


def func_with_string_tuple_return_annotation() -> "Tuple[int, str]":
    return 1, "a"


def test_string_return_annotation_is_resolved():
    """parse_return_type_annotations should resolve plain string annotations.

    String annotations arise when ``from __future__ import annotations`` is
    active (PEP 563) or when the annotation is written as an explicit string
    literal.  Without resolution the materializer look-up would fail with an
    AttributeError on '__mro__'.
    """
    output_signatures = parse_return_type_annotations(
        func_with_string_return_annotation
    )
    assert output_signatures["output"].resolved_annotation is int


def test_get_resolved_type_hints_returns_empty_on_failure():
    """get_resolved_type_hints must not propagate exceptions."""
    from zenml.steps.utils import get_resolved_type_hints

    class _Unresolvable:
        """A callable whose annotations cannot be resolved."""
        __annotations__ = {"return": "NonExistentType123"}
        __globals__ = {}

        def __call__(self) -> None:  # noqa: D401
            pass

    # Should return empty dict rather than raising
    result = get_resolved_type_hints(_Unresolvable())
    assert isinstance(result, dict)
