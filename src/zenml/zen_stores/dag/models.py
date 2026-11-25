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
"""DAG helper models."""

from typing import Any, Dict, NamedTuple, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.config.step_configurations import GroupInfo, StepSpec
from zenml.enums import StepType


class DAGStepConfigView(BaseModel):
    """Step configuration projection for DAG generation."""

    model_config = ConfigDict(extra="ignore")

    step_type: Optional[StepType] = None
    group: Optional[GroupInfo] = None
    substitutions: Dict[str, str] = {}
    outputs: Dict[str, Any] = {}
    client_lazy_loaders: Dict[str, Any] = {}
    model_artifacts_or_metadata: Dict[str, Any] = {}
    external_input_artifacts: Dict[str, Any] = {}


class DAGStepView(BaseModel):
    """Step projection for DAG generation."""

    model_config = ConfigDict(extra="ignore")

    spec: StepSpec
    config: DAGStepConfigView

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        substitutions: Dict[str, str],
    ) -> "DAGStepView":
        """Build a lightweight step view from stored step config data.

        Args:
            data: The step data.
            substitutions: The pipeline substitutions.

        Returns:
            The step view.
        """
        config_data = (
            data["config"]
            if "config" in data
            else data["step_config_overrides"]
        )
        config_data = {
            **config_data,
            "substitutions": {
                **substitutions,
                **(config_data.get("substitutions") or {}),
            },
        }
        return cls.model_validate(
            {"spec": data["spec"], "config": config_data}
        )


class InputArtifactRow(NamedTuple):
    """Input artifact row."""

    step_id: UUID
    name: str
    artifact_id: UUID
    type: str
    input_index: int
    chunk_index: Optional[int]
    chunk_size: Optional[int]
    artifact_type: str
    artifact_data_type: str
    artifact_save_type: str


class OutputArtifactRow(NamedTuple):
    """Output artifact row."""

    step_id: UUID
    name: str
    artifact_id: UUID
    artifact_type: str
    artifact_data_type: str
    artifact_save_type: str
