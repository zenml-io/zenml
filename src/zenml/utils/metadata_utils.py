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
"""Utility functions to handle metadata for ZenML entities."""

import contextlib
from typing import Dict, Optional, Union
from uuid import UUID

from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import get_step_context


def log_metadata(
    metadata: Dict[str, MetadataType],
    run: Optional[Union[str, UUID]] = None,
    step: Optional[Union[str, UUID]] = None,
    model: Optional[Union[str, UUID]] = None,
    artifact: Optional[Union[str, UUID]] = None,
) -> None:
    """Logs metadata for various resource types in a generalized way.

    Args:
        metadata: The metadata to log.
        run: The name, ID, or prefix of the run.
        step: The name, ID, or prefix of the step.
        model: The name, ID, or prefix of the model.
        artifact: The name, ID, or prefix of the artifact.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    client = Client()

    # Attempt to get the step context if no identifiers are provided
    if not any([run, step, model, artifact]):
        with contextlib.suppress(RuntimeError):
            step_context = get_step_context()
            if step_context:
                run = step_context.pipeline_run.id
                step = step_context.step_run.id
                model = step_context.model_version.id

    # Raise an error if still no identifiers are available
    if not any([run, step, model, artifact]):
        raise ValueError(
            "No valid identifiers (run, step, model, or artifact) provided "
            "and not running within a step context. Please provide at least "
            "one."
        )

    # Create metadata for the run, if available
    if run:
        if not isinstance(run, UUID):
            run = client.get_pipeline_run(name_id_or_prefix=run).id
        client.create_run_metadata(
            metadata=metadata,
            resource_id=run,
            resource_type=MetadataResourceTypes.PIPELINE_RUN,
        )

    # Create metadata for the step, if available
    if step:
        if not isinstance(step, UUID):
            assert run is not None, (
                "If you are using `log_metadata` function to log metadata "
                "for a step manually, you have to provide a run name id or "
                "prefix as well."
            )
            step = (
                client.get_pipeline_run(name_id_or_prefix=run).steps[step].id
            )
        client.create_run_metadata(
            metadata=metadata,
            resource_id=step,
            resource_type=MetadataResourceTypes.STEP_RUN,
        )

    # Create metadata for the model, if available
    if model:
        if not isinstance(model, UUID):
            model = client.get_model_version(
                model_version_name_or_number_or_id=model
            ).id
        client.create_run_metadata(
            metadata=metadata,
            resource_id=model,
            resource_type=MetadataResourceTypes.MODEL_VERSION,
        )

    # Create metadata for the artifact, if available
    if artifact:
        if not isinstance(artifact, UUID):
            artifact = client.get_artifact_version(
                name_id_or_prefix=artifact
            ).id
        client.create_run_metadata(
            metadata=metadata,
            resource_id=artifact,
            resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
        )
