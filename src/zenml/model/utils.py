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

from zenml.client import Client
from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.model.model import Model
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)
from zenml.models import (
    ArtifactVersionResponse,
    ModelVersionArtifactRequest,
    ModelVersionResponse,
    ServiceUpdate,
)
from zenml.steps.step_context import get_step_context

logger = get_logger(__name__)


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
        ValueError: If the function is not called with proper input.
    """
    logger.warning(
        "The `log_model_metadata` function is deprecated and will soon be "
        "removed. Instead, you can consider using: "
        "`log_metadata(metadata={...}, infer_model=True)` instead. For more "
        "info: https://docs.zenml.io/concepts/metadata#attaching-metadata-to-models"
    )

    from zenml import log_metadata

    if model_name and model_version:
        log_metadata(
            metadata=metadata,
            model_version=model_version,
            model_name=model_name,
        )
    elif model_name is None and model_version is None:
        log_metadata(
            metadata=metadata,
            infer_model=True,
        )
    else:
        raise ValueError(
            "You can call `log_model_metadata` by either providing both "
            "`model_name` and `model_version` or keeping both of them None."
        )


def _maybe_register_model_artifact_to_registry(
    artifact_version: ArtifactVersionResponse,
    model_version: ModelVersionResponse,
) -> None:
    """Register model artifact to external model registry if configured.

    This function checks if:
    1. The artifact is a MODEL type artifact
    2. The model has save_models_to_registry=True
    3. There's a model registry in the active stack

    If all conditions are met, it automatically registers the model to the
    external model registry.

    Args:
        artifact_version: The artifact version to potentially register.
        model_version: The model version this artifact belongs to.
    """
    try:
        # Check if this is a model artifact
        if artifact_version.type != "ModelArtifact":
            return

        # Get the parent model
        client = Client()
        model_response = client.get_model(model_version.model.id)

        # Check if save_models_to_registry is enabled
        if not model_response.save_models_to_registry:
            logger.debug(
                f"save_models_to_registry=False for model '{model_response.name}', "
                "skipping external registry registration"
            )
            return

        # Check if there's a model registry in the stack
        model_registry = client.active_stack.model_registry
        if not model_registry:
            logger.debug(
                "No model registry in stack, skipping external registration"
            )
            return

        # Prepare metadata - only include ZenML version now
        # (pipeline/run/step fields removed as one model version can have multiple runs)
        metadata = ModelRegistryModelMetadata()

        # Get ZenML version
        from zenml import __version__

        metadata.zenml_version = __version__

        # Generate ZenML model version URL for bidirectional linking
        zenml_model_url = None
        try:
            # Get server URL from the client's server info
            server_info = client.zen_store.get_store_info()
            dashboard_url = server_info.dashboard_url

            if dashboard_url:
                # dashboard_url already includes /workspaces/{workspace}
                # Just append projects and model version
                model_version_id = model_version.id
                project = model_version.project
                project_name = project.name

                zenml_model_url = (
                    f"{dashboard_url.rstrip('/')}/"
                    f"projects/{project_name}/model-versions/{model_version_id}?tab=overview"
                )
                logger.info(f"Generated ZenML model URL: {zenml_model_url}")
            else:
                logger.warning("No dashboard URL available")
        except Exception as e:
            logger.warning(f"Could not generate ZenML model URL: {e}")

        # Register to external model registry
        logger.info(
            f"Auto-registering model '{model_response.name}' "
            f"version '{model_version.number}' to {model_registry.flavor} "
            f"model registry..."
        )

        model_registry.register_model_version(
            name=model_response.name,
            version=str(model_version.number),
            model_source_uri=artifact_version.uri,
            description=model_version.description,
            metadata=metadata,
            zenml_model_url=zenml_model_url,
        )

        logger.info(
            f"✓ Successfully auto-registered to {model_registry.flavor} registry"
        )

    except Exception as e:
        logger.warning(
            f"Failed to auto-register model to external registry: {e}. "
            "You can manually register using the model registry CLI or step."
        )


def link_artifact_version_to_model_version(
    artifact_version: ArtifactVersionResponse,
    model_version: ModelVersionResponse,
) -> None:
    """Link an artifact version to a model version.

    Args:
        artifact_version: The artifact version to link.
        model_version: The model version to link.
    """
    client = Client()
    client.zen_store.create_model_version_artifact_link(
        ModelVersionArtifactRequest(
            artifact_version=artifact_version.id,
            model_version=model_version.id,
        )
    )

    # Auto-register model artifacts to external model registry if configured
    _maybe_register_model_artifact_to_registry(
        artifact_version=artifact_version,
        model_version=model_version,
    )


def link_artifact_to_model(
    artifact_version: ArtifactVersionResponse,
    model: Optional["Model"] = None,
) -> None:
    """Link the artifact to the model.

    Args:
        artifact_version: The artifact version to link.
        model: The model to link to.

    Raises:
        RuntimeError: If called outside a step.
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

    model_version = model._get_or_create_model_version()
    link_artifact_version_to_model_version(
        artifact_version=artifact_version,
        model_version=model_version,
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
