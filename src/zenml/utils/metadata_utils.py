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

from typing import Dict, Optional, Set, Union, overload
from uuid import UUID

from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import get_step_context

logger = get_logger(__name__)


@overload
def log_metadata(metadata: Dict[str, MetadataType]) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    artifact_version_id: UUID,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    artifact_name: str,
    artifact_version: Optional[str] = None,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    model_version_id: UUID,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    model_name: str,
    model_version: str,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    step_id: UUID,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    run_id_name_or_prefix: Union[UUID, str],
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    step_name: str,
    run_id_name_or_prefix: Union[UUID, str],
) -> None: ...


def log_metadata(
    metadata: Dict[str, MetadataType],
    # Parameters to manually log metadata for steps and runs
    step_id: Optional[UUID] = None,
    step_name: Optional[str] = None,
    run_id_name_or_prefix: Optional[Union[UUID, str]] = None,
    # Parameters to manually log metadata for artifacts
    artifact_version_id: Optional[UUID] = None,
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
    # Parameters to manually log metadata for models
    model_version_id: Optional[UUID] = None,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
) -> None:
    """Logs metadata for various resource types in a generalized way.

    Args:
        metadata: The metadata to log.
        step_id: The ID of the step.
        step_name: The name of the step.
        run_id_name_or_prefix: The id, name or prefix of the run
        artifact_version_id: The ID of the artifact version
        artifact_name: The name of the artifact.
        artifact_version: The version of the artifact.
        model_version_id: The ID of the model version.
        model_name: The name of the model.
        model_version: The version of the model

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    # Initialize the client
    client = Client()

    # Initialize a batch of request to avoid duplications
    metadata_batch: Dict[MetadataResourceTypes, Set[UUID]] = {
        MetadataResourceTypes.PIPELINE_RUN: set(),
        MetadataResourceTypes.STEP_RUN: set(),
        MetadataResourceTypes.ARTIFACT_VERSION: set(),
        MetadataResourceTypes.MODEL_VERSION: set(),
    }

    # If a step name is provided, we need a run_id_name_or_prefix and will log
    # metadata for the steps pipeline and model accordingly.
    if step_name is not None and run_id_name_or_prefix is not None:
        run_model = client.get_pipeline_run(
            name_id_or_prefix=run_id_name_or_prefix
        )
        step_model = run_model.steps[step_name]

        metadata_batch[MetadataResourceTypes.PIPELINE_RUN].add(run_model.id)
        metadata_batch[MetadataResourceTypes.STEP_RUN].add(step_model.id)
        if step_model.model_version:
            metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
                step_model.model_version.id
            )

    # If a step is identified by id, fetch it directly through the client,
    # follow a similar procedure and log metadata for its pipeline and model
    # as well.
    elif step_id is not None:
        step_model = client.get_run_step(step_run_id=step_id)
        run_model = client.get_pipeline_run(
            name_id_or_prefix=step_model.pipeline_run_id
        )
        metadata_batch[MetadataResourceTypes.PIPELINE_RUN].add(run_model.id)
        metadata_batch[MetadataResourceTypes.STEP_RUN].add(step_model.id)
        if step_model.model_version:
            metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
                step_model.model_version.id
            )

    # If a pipeline run id is identified, we need to log metadata to it and its
    # model as well.
    elif run_id_name_or_prefix is not None:
        run_model = client.get_pipeline_run(
            name_id_or_prefix=run_id_name_or_prefix
        )
        if run_model.model_version:
            metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
                run_model.model_version.id
            )
        metadata_batch[MetadataResourceTypes.PIPELINE_RUN].add(run_model.id)

    # If the user provides a model name and version, we use to model abstraction
    # to fetch the model version and attach the corresponding metadata to it.
    elif model_name is not None and model_version is not None:
        from zenml import Model

        mv = Model(name=model_name, version=model_version)
        metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(mv.id)

    # If the user provides a model version id, we use the client to fetch it and
    # attach the metadata to it.
    elif model_version_id is not None:
        model_version_id = client.get_model_version(
            model_version_name_or_number_or_id=model_version_id
        ).id
        metadata_batch[MetadataResourceTypes.MODEL_VERSION].add(
            model_version_id
        )

    # If the user provides an artifact name, there are two possibilities. If
    # an artifact version is also provided with the name, we use both to fetch
    # the artifact version and use it to log the metadata. If no version is
    # provided, we make sure that the call is happening within a step, otherwise
    # we fail.
    elif artifact_name is not None:
        if artifact_version:
            artifact_version_model = client.get_artifact_version(
                name_id_or_prefix=artifact_name, version=artifact_version
            )
            client.create_run_metadata(
                metadata=metadata,
                resource_id=artifact_version_model.id,
                resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
            )
        else:
            try:
                step_context = get_step_context()
                step_context.add_output_metadata(
                    metadata=metadata, output_name=artifact_name
                )
            except RuntimeError:
                raise ValueError(
                    "You are calling 'log_metadata(artifact_name='...') "
                    "without specifying a version outside of a step execution."
                )

    # If the user directly provides an artifact_version_id, we use the client to
    # fetch is and attach the metadata accordingly.
    elif artifact_version_id is not None:
        artifact_version_model = client.get_artifact_version(
            name_id_or_prefix=artifact_version_id,
        )
        client.create_run_metadata(
            metadata=metadata,
            resource_id=artifact_version_model.id,
            resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
        )

    # If every additional value is None, that means we are calling it bare bones
    # and this call needs to happen during a step execution. We will use the
    # step context to fetch the step, run and possibly the model version and
    # attach the metadata accordingly.
    elif all(
        v is None
        for v in [
            step_id,
            step_name,
            run_id_name_or_prefix,
            artifact_version_id,
            artifact_name,
            artifact_version,
            model_version_id,
            model_name,
            model_version,
        ]
    ):
        try:
            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                "You are calling 'log_metadata()' outside of a step execution. "
                "If you would like to add metadata to a ZenML entity outside "
                "of the step execution, please provide the required "
                "identifiers."
            )
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
        raise ValueError()
