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

from typing import Dict, Optional, Union
from uuid import UUID

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.model.model import Model
from zenml.models import (
    ModelVersionArtifactRequest,
    ServiceUpdate,
)
from zenml.steps.step_context import get_step_context

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
        model = step_context.model
    except StepContextError:
        model = None
        logger.debug("No model context found, unable to auto-link artifacts.")

    for artifact_name, artifact_version_id in artifact_version_ids.items():
        artifact_config = step_context._get_output(
            artifact_name
        ).artifact_config

        if artifact_config is None and model is not None:
            artifact_config = ArtifactConfig(name=artifact_name)

        if artifact_config:
            link_artifact_config_to_model(
                artifact_config=artifact_config,
                artifact_version_id=artifact_version_id,
                model=model,
            )


def link_artifact_config_to_model(
    artifact_config: ArtifactConfig,
    artifact_version_id: UUID,
    model: "Model",
) -> None:
    """Link an artifact config to its model version.

    Args:
        artifact_config: The artifact config to link.
        artifact_version_id: The ID of the artifact to link.
        model: The model to link the artifact to.
    """
    client = Client()

    logger.debug(
        f"Linking artifact `{artifact_config.name}` to model "
        f"`{model.name}` version `{model.version}` using config "
        f"`{artifact_config}`."
    )
    request = ModelVersionArtifactRequest(
        user=client.active_user.id,
        workspace=client.active_workspace.id,
        artifact_version=artifact_version_id,
        model=model.model_id,
        model_version=model.id,
        is_model_artifact=artifact_config.is_model_artifact,
        is_deployment_artifact=artifact_config.is_deployment_artifact,
    )
    client.zen_store.create_model_version_artifact_link(request)


def log_model_metadata(
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
            `model` in decorator.
        model_version: The version of the model to log metadata for. Can
            be omitted when being called inside a step with configured
            `model` in decorator.

    Raises:
        ValueError: If no model name/version is provided and the function is not
            called inside a step with configured `model` in decorator.
    """
    if model_name and model_version:
        from zenml import Model

        mv = Model(name=model_name, version=model_version)
    else:
        try:
            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                "Model name and version must be provided unless the function is "
                "called inside a step with configured `model` in decorator."
            )
        mv = step_context.model

    mv.log_metadata(metadata)


def link_artifact_to_model(
    artifact_version_id: UUID,
    model: Optional["Model"] = None,
    is_model_artifact: bool = False,
    is_deployment_artifact: bool = False,
) -> None:
    """Link the artifact to the model.

    Args:
        artifact_version_id: The ID of the artifact version.
        model: The model to link to.
        is_model_artifact: Whether the artifact is a model artifact.
        is_deployment_artifact: Whether the artifact is a deployment artifact.

    Raises:
        RuntimeError: If called outside of a step.
    """
    if not model:
        is_issue = False
        try:
            step_context = get_step_context()
            model = step_context.model
        except StepContextError:
            is_issue = True

        if model is None or is_issue:
            raise RuntimeError(
                "`link_artifact_to_model` called without `model` parameter "
                "and configured model context cannot be identified. Consider "
                "passing the `model` explicitly or configuring it in "
                "@step or @pipeline decorator."
            )

    link_artifact_config_to_model(
        artifact_config=ArtifactConfig(
            is_model_artifact=is_model_artifact,
            is_deployment_artifact=is_deployment_artifact,
        ),
        artifact_version_id=artifact_version_id,
        model=model,
    )


def link_service_to_model(
    service_id: UUID,
    model: Optional["Model"] = None,
    model_version_id: Optional[UUID] = None,
) -> None:
    """Links a service to a model.

    Args:
        service_id: The ID of the service to link to the model.
        model: The model to link the service to.
        model_version_id: The ID of the model version to link the service to.

    Raises:
        RuntimeError: If no model is provided and the model context cannot be
            identified.
    """
    client = Client()

    # If no model is provided, try to get it from the context
    if not model and not model_version_id:
        is_issue = False
        try:
            step_context = get_step_context()
            model = step_context.model
        except StepContextError:
            is_issue = True

        if model is None or is_issue:
            raise RuntimeError(
                "`link_service_to_model` called without `model` parameter "
                "and configured model context cannot be identified. Consider "
                "passing the `model` explicitly or configuring it in "
                "@step or @pipeline decorator."
            )

    model_version_id = (
        model_version_id or model._get_or_create_model_version().id
        if model
        else None
    )
    update_service = ServiceUpdate(model_version_id=model_version_id)
    client.zen_store.update_service(
        service_id=service_id, update=update_service
    )
