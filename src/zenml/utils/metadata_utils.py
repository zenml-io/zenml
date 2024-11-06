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
from typing import Dict, Optional, Set, Union
from uuid import UUID

from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import get_step_context


def log_metadata(
    metadata: Dict[str, MetadataType],
    run: Optional[Union[str, UUID]] = None,
    step: Optional[Union[str, UUID]] = None,
    model_version: Optional[Union[str, UUID]] = None,
    artifact_version: Optional[Union[str, UUID]] = None,
) -> None:
    """Logs metadata for various resource types in a generalized way.

    Args:
        metadata: The metadata to log.
        run: The name, ID, or prefix of the run.
        step: The name, ID, or prefix of the step.
        model_version: The name, ID, or prefix of the model version.
        artifact_version: The name, ID, or prefix of the artifact version.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    client = Client()

    if not any([run, step, model_version, artifact_version]):
        # Executing without any identifiers -> Fetch the step context
        with contextlib.suppress(RuntimeError):
            step_context = get_step_context()
            if step_context:
                client.create_run_metadata(
                    metadata=metadata,
                    resource_id=step_context.pipeline_run.id,
                    resource_type=MetadataResourceTypes.PIPELINE_RUN,
                )
                client.create_run_metadata(
                    metadata=metadata,
                    resource_id=step_context.step_run.id,
                    resource_type=MetadataResourceTypes.STEP_RUN,
                )
                if step_context.model_version:
                    client.create_run_metadata(
                        metadata=metadata,
                        resource_id=step_context.model_version.id,
                        resource_type=MetadataResourceTypes.MODEL_VERSION,
                    )
            else:
                raise ValueError(
                    "No valid identifiers (run, step, model, or artifact) "
                    "provided and not running within a step context. Please "
                    "provide at least one."
                )
    else:
        # Executing outside a step execution
        metadata_batch: Dict[MetadataResourceTypes, Set[UUID]] = {
            MetadataResourceTypes.PIPELINE_RUN: set(),
            MetadataResourceTypes.STEP_RUN: set(),
            MetadataResourceTypes.ARTIFACT_VERSION: set(),
            MetadataResourceTypes.MODEL_VERSION: set(),
        }

        if step:
            # If a step identifier is provided, try to fetch it. If the
            # identifier is a UUID, we can directly fetch it. If the identifier
            # is a step name, we also need a run identifier.
            if not isinstance(step, UUID):
                assert run is not None, (
                    "If you are using `log_metadata` function to log metadata "
                    "for a specific step by name, you need to provide an "
                    "identifier for the pipeline run it belongs to."
                )
                run_model = client.get_pipeline_run(name_id_or_prefix=run)
                step_model = run_model.steps[step]
            else:
                step_model = client.get_run_step(step_run_id=step)
                run_model = client.get_pipeline_run(
                    name_id_or_prefix=step_model.pipeline_run_id
                )

            metadata_batch[MetadataResourceTypes.PIPELINE_RUN].add(
                run_model.id
            )
            metadata_batch[MetadataResourceTypes.STEP_RUN].add(step_model.id)
            if step_model.model_version:
                metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
                    step_model.model_version.id
                )

        if run:
            # If a run identifier is provided, try to fetch it. We may have
            # already fetched it and added it to the batch, when we were
            # handling the step. In order to avoid duplicate calls, the
            # metadata_batch is being used.
            run_model = client.get_pipeline_run(name_id_or_prefix=run)

            if run_model.model_version:
                metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
                    run_model.model_version.id
                )
            metadata_batch[MetadataResourceTypes.PIPELINE_RUN].add(
                run_model.id
            )

        if model_version_id := model_version:
            # If a model version identifier is provided, try to fetch it. It is
            # possible that we have already fetched this model version when
            # we are dealing with the step and run. In order to duplications,
            # the metadata_batch is being used.
            if not isinstance(model_version_id, UUID):
                model_version_id = client.get_model_version(
                    model_version_name_or_number_or_id=model_version
                ).id
            metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
                model_version_id
            )

        if artifact_version_id := artifact_version:
            # If an artifact version identifier is provided, try to fetch it and
            # add it to the batch.
            if not isinstance(artifact_version_id, UUID):
                artifact_version_id = client.get_artifact_version(
                    name_id_or_prefix=artifact_version
                ).id
            metadata_batch[MetadataResourceTypes.ARTIFACT_VERSION].add(
                artifact_version_id
            )

        # Create the run metadata
        for resource_type, resource_ids in metadata_batch.items():
            for resource_id in resource_ids:
                client.create_run_metadata(
                    metadata=metadata,
                    resource_id=resource_id,
                    resource_type=resource_type,
                )
