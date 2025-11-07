#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the Notion model registration pipeline step."""

from typing import Optional

from zenml import __version__, get_step_context, step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.client import Client
from zenml.integrations.notion.model_registries.notion_model_registry import (
    NotionModelRegistry,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
)

logger = get_logger(__name__)


@step(enable_cache=False)
def notion_register_model_step(
    model: UnmaterializedArtifact,
    name: str,
    version: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[ModelRegistryModelMetadata] = None,
) -> None:
    """Notion model registry step.

    This step registers a model artifact to the Notion model registry,
    creating an entry in your Notion database with all model metadata.

    Args:
        model: Model artifact to be registered. This triggers the step
            when the model is trained but the artifact itself isn't used
            directly.
        name: The name of the model to register.
        version: The version of the model. If not provided, a version
            based on the current timestamp will be generated.
        description: A description of the model version.
        metadata: Additional metadata to associate with the model version.

    Raises:
        ValueError: If the model registry is not a Notion model registry.
    """
    # Fetch the model registry and verify it's Notion
    model_registry = Client().active_stack.model_registry
    if not isinstance(model_registry, NotionModelRegistry):
        raise ValueError(
            "The Notion model registry step can only be used with a "
            "Notion model registry. Please add a Notion model registry "
            "to your stack."
        )

    # Get pipeline context
    step_context = get_step_context()
    pipeline_name = step_context.pipeline.name
    current_run_name = step_context.pipeline_run.name
    pipeline_run_uuid = str(step_context.pipeline_run.id)
    step_name = step_context.step_run.name

    # Get the model artifact URI
    # The model parameter passed to this step is an UnmaterializedArtifact
    # We need to get its URI for registration
    model_source_uri = model.uri

    # Generate version if not provided
    if not version:
        import time

        version = f"v{int(time.time())}"

    # Prepare metadata
    if not metadata:
        metadata = ModelRegistryModelMetadata()

    # Fill in ZenML context metadata
    if metadata.zenml_version is None:
        metadata.zenml_version = __version__
    if metadata.zenml_pipeline_name is None:
        metadata.zenml_pipeline_name = pipeline_name
    if metadata.zenml_run_name is None:
        metadata.zenml_run_name = current_run_name
    if metadata.zenml_pipeline_run_uuid is None:
        metadata.zenml_pipeline_run_uuid = pipeline_run_uuid
    if metadata.zenml_step_name is None:
        metadata.zenml_step_name = step_name

    # Try to pull additional metadata from the model's run_metadata
    try:
        zenml_model_version = step_context.model._get_or_create_model_version()
        if zenml_model_version and zenml_model_version.run_metadata:
            # Extract metadata logged via log_metadata(infer_model=True)
            if not metadata.model_extra:
                # Use setattr to avoid read-only property issue
                setattr(metadata, "model_extra", {})

            # Add any evaluation metrics or model info found
            for (
                key,
                metadata_entry,
            ) in zenml_model_version.run_metadata.items():
                if key in [
                    "evaluation_metrics",
                    "model_info",
                    "hyperparameters",
                ]:
                    if hasattr(metadata_entry, "value"):
                        metadata.model_extra[key] = metadata_entry.value  # type: ignore[index]
    except Exception as e:
        logger.debug(f"Could not extract model metadata: {e}")

    # Register the model version
    logger.info(
        f"Registering model '{name}' version '{version}' to Notion "
        f"model registry..."
    )

    registered_model_version = model_registry.register_model_version(
        name=name,
        version=version,
        model_source_uri=model_source_uri,
        description=description,
        metadata=metadata,
    )

    logger.info(
        f"Successfully registered model {name} version {registered_model_version.version} "
        f"to Notion model registry!"
    )
