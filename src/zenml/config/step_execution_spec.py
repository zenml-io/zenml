#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Step execution specifications."""

import json
from typing import List

from pydantic import Field, field_validator

from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.utils.enum_utils import StrEnum


class StepExecutionLanguage(StrEnum):
    """Supported languages for step body execution."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"


class StepExecutionProtocol(StrEnum):
    """Supported protocols for step body execution."""

    ZENML_PYTHON_STEP_V1 = "zenml-python-step-v1"
    ZENML_PORTABLE_JSON_V1 = "zenml-portable-json-v1"


class StepExecutionSpec(FrozenBaseModel):
    """Specification for executing a step body.

    A missing execution spec means the step follows the existing Python
    ``BaseStep`` path. A non-null execution spec gives ZenML enough stable
    identity to route and cache a deliberately portable step body.
    """

    language: StepExecutionLanguage
    protocol: StepExecutionProtocol
    command: List[str] = Field(
        description="Exact argv to execute inside the step container."
    )
    source_identity: str = Field(
        description="Stable display, debug and cache identity for the step body."
    )

    @field_validator("command")
    @classmethod
    def _validate_command(cls, command: List[str]) -> List[str]:
        """Validate the portable step command.

        Args:
            command: The argv list to validate.

        Raises:
            ValueError: If the command is empty or contains empty arguments.

        Returns:
            The validated command.
        """
        if not command:
            raise ValueError("Step execution command must not be empty.")

        if any(not argument for argument in command):
            raise ValueError(
                "Step execution command arguments must not be empty."
            )

        return command

    @field_validator("source_identity")
    @classmethod
    def _validate_source_identity(cls, source_identity: str) -> str:
        """Validate the source identity.

        Args:
            source_identity: The source identity to validate.

        Raises:
            ValueError: If the source identity is empty.

        Returns:
            The validated source identity.
        """
        if not source_identity:
            raise ValueError(
                "Step execution source identity must not be empty."
            )

        return source_identity

    @property
    def cache_key_fragment(self) -> str:
        """Stable JSON fragment for cache key computation.

        Returns:
            A deterministic JSON string representing the execution identity.
        """
        return json.dumps(self.model_dump(mode="json"), sort_keys=True)
