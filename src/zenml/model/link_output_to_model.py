#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Utility functions for linking step outputs to model versions."""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from zenml.model.artifact_config import ArtifactConfig


def link_output_to_model(
    artifact_config: "ArtifactConfig",
    output_name: Optional[str] = None,
) -> None:
    """Log artifact metadata.

    Args:
        output_name: The output name of the artifact to log metadata for. Can
            be omitted if there is only one output artifact.
        artifact_config: The ArtifactConfig of how to link this output.
    """
    from zenml.new.steps.step_context import get_step_context

    step_context = get_step_context()
    step_context._set_artifact_config(
        output_name=output_name, artifact_config=artifact_config
    )
