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
)
from uuid import UUID

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.model.model_config import ModelConfig
from zenml.models.model_models import (
    ModelVersionArtifactFilterModel,
    ModelVersionArtifactRequestModel,
)
from zenml.new.steps.step_context import get_step_context

logger = get_logger(__name__)


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
            "`link_artifacts_to_model` can only be called from within a step."
        )
    try:
        model_config = step_context.model_config
    except StepContextError:
        model_config = None
        logger.debug("No model context found, unable to auto-link artifacts.")

    for artifact_name in artifact_ids:
        artifact_id = artifact_ids[artifact_name]
        artifact_config = step_context._get_output(
            artifact_name
        ).artifact_config
        if artifact_config is None and model_config is not None:
            artifact_config = ArtifactConfig(
                name=artifact_name,
                model_name=model_config.name,
                model_version=model_config.version,
            )
            logger.info(
                f"Implicitly linking artifact `{artifact_name}` to model "
                f"`{model_config.name}` version `{model_config.version}`."
            )

        if artifact_config and model_config:
            _link_artifact_config_to_model(
                artifact_config=artifact_config,
                artifact_name=artifact_name,
                artifact_id=artifact_id,
                model_config=model_config,
            )


def _link_artifact_config_to_model(
    artifact_config: ArtifactConfig,
    model_config: "ModelConfig",
    artifact_name: str,
    artifact_id: UUID,
) -> None:
    """Link an artifact config to a model version.

    Args:
        artifact_config: The artifact config to link.
        model_config: The model config to link the artifact to.
        artifact_name: The name of the artifact to link.
        artifact_id: The ID of the artifact to link.
    """
    from zenml.client import Client

    client = Client()
    step_context = get_step_context()

    artifact_name = artifact_config.name or artifact_name
    if artifact_name is None:
        artifact = client.zen_store.get_artifact(artifact_id=artifact_id)
        artifact_name = artifact.name

    pipeline_name = step_context.pipeline.name
    step_name = step_context.step_run.name
    model_version = model_config._get_model_version()
    model_id = model_version.model.id
    model_version_id = model_version.id
    is_model_object = artifact_config.is_model_artifact
    is_deployment = artifact_config.is_deployment_artifact

    # Create a request model for the model version artifact link
    request = ModelVersionArtifactRequestModel(
        user=client.active_user.id,
        workspace=client.active_workspace.id,
        name=artifact_name,
        artifact=artifact_id,
        model=model_id,
        model_version=model_version_id,
        is_model_object=is_model_object,
        is_deployment=is_deployment,
        overwrite=artifact_config.overwrite_model_link,
        pipeline_name=pipeline_name,
        step_name=step_name,
    )

    # Create the model version artifact link using the ZenML client
    existing_links = client.list_model_version_artifact_links(
        ModelVersionArtifactFilterModel(
            user_id=client.active_user.id,
            workspace_id=client.active_workspace.id,
            name=artifact_name,
            model_id=model_id,
            model_version_id=model_version_id,
            only_artifacts=not (is_model_object or is_deployment),
            only_deployments=is_deployment,
            only_model_objects=is_model_object,
        )
    )
    if len(existing_links):
        if artifact_config.overwrite_model_link:
            logger.info(
                f"Deleting existing artifact link(s) for artifact "
                f"`{artifact_name}`."
            )
            client.zen_store.delete_model_version_artifact_link(
                model_name_or_id=model_id,
                model_version_name_or_id=model_version_id,
                model_version_artifact_link_name_or_id=artifact_name,
            )
        else:
            logger.info(
                f"Artifact link `{artifact_name}` already exists, adding "
                "new version."
            )
    client.zen_store.create_model_version_artifact_link(request)
