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
from unittest.mock import MagicMock

import pytest

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.exceptions import StepInterfaceError
from zenml.steps.entrypoint_function_utils import (
    EntrypointFunctionDefinition,
    StepArtifact,
)
from zenml.steps.utils import OutputSignature


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


def _unmaterialized_step_artifact() -> StepArtifact:
    return StepArtifact(
        invocation_id="producer",
        output_name="output",
        annotation=OutputSignature(
            resolved_annotation=int,
            artifact_config=ArtifactConfig(materialize=False),
        ),
        pipeline=MagicMock(),
    )


def _definition_with_annotation(annotation) -> EntrypointFunctionDefinition:
    return EntrypointFunctionDefinition(
        inputs={
            "key": inspect.Parameter(
                name="key",
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=annotation,
            )
        },
        outputs={},
    )


def test_passing_unmaterialized_output_as_input() -> None:
    """Test that unmaterialized step outputs are rejected as step inputs."""
    entrypoint_function_definition = _definition_with_annotation(int)

    with pytest.raises(StepInterfaceError):
        entrypoint_function_definition.validate_input(
            key="key", value=_unmaterialized_step_artifact()
        )

    with pytest.raises(StepInterfaceError):
        entrypoint_function_definition.validate_input(
            key="key", value=[_unmaterialized_step_artifact()]
        )


def test_passing_unmaterialized_output_as_unmaterialized_input() -> None:
    """Test that unmaterialized step outputs are allowed as inputs that are
    annotated as `UnmaterializedArtifact`."""
    entrypoint_function_definition = _definition_with_annotation(
        UnmaterializedArtifact
    )

    with does_not_raise():
        entrypoint_function_definition.validate_input(
            key="key", value=_unmaterialized_step_artifact()
        )
