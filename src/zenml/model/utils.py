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
    Optional,
    Union,
)
from uuid import UUID

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.model.model_version import ModelVersion
from zenml.models import ModelVersionArtifactRequest
from zenml.new.steps.step_context import get_step_context

logger = get_logger(__name__)


def link_step_artifacts_to_model(
    artifact_version_ids: Dict[str, UUID],
) -> None:
    """Links the output artifacts of a step to the model.

    Args:
        artifact_version_ids: The IDs of the published output artifacts.

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

    for artifact_name, artifact_version_id in artifact_version_ids.items():
        artifact_config = step_context._get_output(
            artifact_name
        ).artifact_config

        # Implicit linking
        if artifact_config is None and model_version is not None:
            artifact_config = ArtifactConfig(name=artifact_name)
            logger.info(
                f"Implicitly linking artifact `{artifact_name}` to model "
                f"`{model_version.name}` version `{model_version.version}`."
            )

        if artifact_config:
            link_artifact_config_to_model_version(
                artifact_config=artifact_config,
                artifact_version_id=artifact_version_id,
                model_version=model_version,
            )


def link_artifact_config_to_model_version(
    artifact_config: ArtifactConfig,
    artifact_version_id: UUID,
    model_version: Optional["ModelVersion"] = None,
) -> None:
    """Link an artifact config to its model version.

    Args:
        artifact_config: The artifact config to link.
        artifact_version_id: The ID of the artifact to link.
        model_version: The model version from the step or pipeline context.
    """
    client = Client()

    # If the artifact config specifies a model itself then always use that
    if artifact_config.model_name is not None:
        from zenml.model.model_version import ModelVersion

        model_version = ModelVersion(
            name=artifact_config.model_name,
            version=artifact_config.model_version,
        )

    if model_version:
        model_version._get_or_create_model_version()
        model_version_response = model_version._get_model_version()
        request = ModelVersionArtifactRequest(
            user=client.active_user.id,
            workspace=client.active_workspace.id,
            artifact_version=artifact_version_id,
            model=model_version_response.model.id,
            model_version=model_version_response.id,
            is_model_artifact=artifact_config.is_model_artifact,
            is_deployment_artifact=artifact_config.is_deployment_artifact,
        )
        client.zen_store.create_model_version_artifact_link(request)


def log_model_version_metadata(
    metadata: Dict[str, "MetadataType"],
    model_name: Optional[str] = None,
    model_version: Optional[Union[ModelStages, int, str]] = None,
) -> None:
    """Log model version metadata.

    This function can be used to log metadata for existing model versions.

    Args:
        metadata: The metadata to log.
        model_name: The name of the model to log metadata for. Can
            be omitted when being called inside a step with configured
            `model_version` in decorator.
        model_version: The version of the model to log metadata for. Can
            be omitted when being called inside a step with configured
            `model_version` in decorator.

    Raises:
        ValueError: If no model name/version is provided and the function is not
            called inside a step with configured `model_version` in decorator.
    """
    mv = None
    try:
        step_context = get_step_context()
        mv = step_context.model_version
    except RuntimeError:
        step_context = None

    if not step_context and not (model_name and model_version):
        raise ValueError(
            "Model name and version must be provided unless the function is "
            "called inside a step with configured `model_version` in decorator."
        )
    if mv is None:
        from zenml import ModelVersion

        mv = ModelVersion(name=model_name, version=model_version)

    mv.log_metadata(metadata)
