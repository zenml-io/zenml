#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
from contextlib import ExitStack as does_not_raise
from typing import Optional

from zenml.steps.entrypoint_function_utils import EntrypointFunctionDefinition


class CustomType:
    pass


def test_passing_none_for_optional_artifact() -> None:
    entrypoint_function_definition = EntrypointFunctionDefinition(
        inputs={
            "key": inspect.Parameter(
                name="key",
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=Optional[CustomType],
            )
        },
        outputs={},
    )

    with does_not_raise():
        entrypoint_function_definition.validate_input(key="key", value=None)


# ---------------------------------------------------------------------------
# Tests for string annotation resolution (from __future__ import annotations)
# ---------------------------------------------------------------------------
from zenml.steps.entrypoint_function_utils import validate_entrypoint_function


def func_with_string_input_annotation(x: "int") -> "str":
    return str(x)


def test_string_input_annotation_is_resolved():
    """validate_entrypoint_function should resolve string input annotations.

    When ``from __future__ import annotations`` is used, parameter annotations
    become plain strings.  The function must resolve them to real types so
    that Pydantic input validation works correctly.
    """
    definition = validate_entrypoint_function(func_with_string_input_annotation)
    assert definition.inputs["x"].annotation is int


def test_string_return_annotation_is_resolved_via_entrypoint():
    """validate_entrypoint_function should yield a resolved output annotation."""
    definition = validate_entrypoint_function(func_with_string_input_annotation)
    assert definition.outputs["output"].resolved_annotation is str
