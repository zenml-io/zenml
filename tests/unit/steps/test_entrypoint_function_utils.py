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
from typing import Any, Optional

import pytest

from zenml.exceptions import StepInterfaceError
from zenml.steps.entrypoint_function_utils import (
    EntrypointFunctionDefinition,
    validate_entrypoint_function,
)


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


def test_validate_resolves_stringized_param_and_return() -> None:
    """Stringized input and return annotations resolve end-to-end."""
    from tests.unit.steps import future_annotations_module as m

    definition = validate_entrypoint_function(m.func_stringized_param)
    assert definition.inputs["x"].annotation is int
    assert definition.outputs["output"].resolved_annotation is int

    definition = validate_entrypoint_function(m.func_stringized_return)
    assert definition.outputs["output"].resolved_annotation is int


def test_validate_resolves_stringized_annotated_name() -> None:
    """`Annotated[T, "name"]` survives PEP 563 stringization."""
    from tests.unit.steps import future_annotations_module as m

    definition = validate_entrypoint_function(m.func_stringized_annotated_name)
    assert "named" in definition.outputs
    assert definition.outputs["named"].resolved_annotation is int
    assert definition.outputs["named"].has_custom_name


def test_validate_resolves_stringized_artifact_config() -> None:
    """`Annotated[T, ArtifactConfig(...)]` survives PEP 563 stringization."""
    from tests.unit.steps import future_annotations_module as m

    definition = validate_entrypoint_function(
        m.func_stringized_artifact_config
    )
    assert "ac_named" in definition.outputs
    output = definition.outputs["ac_named"]
    assert output.resolved_annotation is int
    assert output.artifact_config is not None
    assert output.artifact_config.name == "ac_named"


def test_validate_resolves_stringized_multi_output() -> None:
    """Multi-output `Tuple[...]` resolves under PEP 563."""
    from tests.unit.steps import future_annotations_module as m

    definition = validate_entrypoint_function(m.func_stringized_multi_output)
    assert definition.outputs["output_0"].resolved_annotation is int
    assert definition.outputs["output_1"].resolved_annotation is str


def test_validate_resolves_stringized_optional() -> None:
    """`Optional[T]` input resolves under PEP 563."""
    from tests.unit.steps import future_annotations_module as m

    definition = validate_entrypoint_function(m.func_stringized_optional)
    assert definition.inputs["x"].annotation == Optional[int]


def test_validate_unresolvable_input_falls_back_to_any() -> None:
    """An unresolvable input annotation degrades to `Any`."""
    from tests.unit.steps import future_annotations_module as m

    definition = validate_entrypoint_function(m.func_with_unresolved_input)
    assert definition.inputs["x"].annotation is Any
    # Validation should now accept any value because annotation is `Any`.
    with does_not_raise():
        definition.validate_input(key="x", value=42)
        definition.validate_input(key="x", value="anything")


def test_validate_unresolvable_return_raises() -> None:
    """An unresolvable return annotation raises StepInterfaceError."""
    from tests.unit.steps import future_annotations_module as m

    with pytest.raises(StepInterfaceError) as exc_info:
        validate_entrypoint_function(m.func_with_unresolved_return)

    assert "func_with_unresolved_return" in str(exc_info.value)
    assert "Decimal" in str(exc_info.value)
