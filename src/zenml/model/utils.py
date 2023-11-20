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

from typing import (
    Dict,
)
from uuid import UUID

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.model.model_version import ModelVersion
from zenml.models.model_models import (
    ModelVersionArtifactRequestModel,
)
from zenml.new.steps.step_context import get_step_context

logger = get_logger(__name__)


def link_step_artifacts_to_model(
    artifact_ids: Dict[str, UUID],
) -> None:
    """Links the output artifacts of a step to the model.

    Args:
        artifact_ids: The IDs of the published output artifacts.

    Raises:
        RuntimeError: If called outside of a step.
    """
    try:
        step_context = get_step_context()
    except StepContextError:
        raise RuntimeError(
            "`link_step_artifacts_to_model` can only be called from within a "
            "step."
        )
    try:
        model_version = step_context.model_version
    except StepContextError:
        model_version = None
        logger.debug("No model context found, unable to auto-link artifacts.")

    for artifact_name in artifact_ids:
        artifact_id = artifact_ids[artifact_name]
        artifact_config = step_context._get_output(
            artifact_name
        ).artifact_config
        if artifact_config is None and model_version is not None:
            artifact_config = ArtifactConfig(
                name=artifact_name,
                model_name=model_version.name,
                model_version=model_version.version,
            )
            logger.info(
                f"Implicitly linking artifact `{artifact_name}` to model "
                f"`{model_version.name}` version `{model_version.version}`."
            )

        if artifact_config and model_version:
            link_artifact_config_to_model_version(
                artifact_config=artifact_config,
                artifact_id=artifact_id,
                model_version=model_version,
            )


def link_artifact_config_to_model_version(
    artifact_config: ArtifactConfig,
    model_version: "ModelVersion",
    artifact_id: UUID,
) -> None:
    """Link an artifact config to a model version.

    Args:
        artifact_config: The artifact config to link.
        model_version: The model version to link the artifact to.
        artifact_id: The ID of the artifact to link.
    """
    client = Client()
    model_version_response = model_version._get_model_version()
    request = ModelVersionArtifactRequestModel(
        user=client.active_user.id,
        workspace=client.active_workspace.id,
        artifact=artifact_id,
        model=model_version_response.model.id,
        model_version=model_version_response.id,
        is_model_artifact=artifact_config.is_model_artifact,
        is_endpoint_artifact=artifact_config.is_endpoint_artifact,
    )
    client.zen_store.create_model_version_artifact_link(request)
