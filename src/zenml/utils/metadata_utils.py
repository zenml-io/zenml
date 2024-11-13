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
from typing import Dict, Optional, Union, overload
from uuid import UUID

from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import get_step_context

logger = get_logger(__name__)


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    artifact_version_id: UUID,
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    artifact_name: str,
    artifact_version: Optional[str] = None,
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    model_version_id: UUID,
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    model_name: str,
    model_version: str,
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    step_id: UUID,
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    run_id_name_or_prefix: Union[UUID, str],
    log_related_entities: Optional[bool] = True,
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    step_name: str,
    run_id_name_or_prefix: Union[UUID, str],
    log_related_entities: Optional[bool] = True,
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
    # Parameter to adjust whether we log to all related entities
    log_related_entities: Optional[bool] = True,
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
        log_related_entities: Flag to decide whether we should log the same
            metadata for related entities.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    client = Client()

    # If a step name is provided, we need a run_id_name_or_prefix and will log
    # metadata for the steps pipeline and model accordingly.
    if step_name is not None and run_id_name_or_prefix is not None:
        run = client.get_pipeline_run(run_id_name_or_prefix)
        step = run.steps[step_name]

        resources = [(step.id, MetadataResourceTypes.STEP_RUN)]

        if log_related_entities:
            resources.append((run.id, MetadataResourceTypes.PIPELINE_RUN))
            if step.model_version:
                resources.append(
                    (
                        step.model_version.id,
                        MetadataResourceTypes.MODEL_VERSION,
                    )
                )
        client.create_run_metadata(metadata=metadata, resources=resources)
    # If a step is identified by id, fetch it directly through the client,
    # follow a similar procedure and log metadata for its pipeline and model
    # as well.
    elif step_id is not None:
        resources = [(step_id, MetadataResourceTypes.STEP_RUN)]

        if log_related_entities:
            step = client.get_run_step(step_id)
            resources.append(
                (step.pipeline_run_id, MetadataResourceTypes.PIPELINE_RUN)
            )

            if step.model_version:
                resources.append(
                    (
                        step.model_version.id,
                        MetadataResourceTypes.MODEL_VERSION,
                    )
                )
        client.create_run_metadata(metadata=metadata, resources=resources)

    # If a pipeline run id is identified, we need to log metadata to it and its
    # model as well.
    elif run_id_name_or_prefix is not None:
        run = client.get_pipeline_run(run_id_name_or_prefix)

        resources = [(run.id, MetadataResourceTypes.PIPELINE_RUN)]

        if log_related_entities and run.model_version is not None:
            resources.append(
                (run.model_version.id, MetadataResourceTypes.MODEL_VERSION)
            )
        client.create_run_metadata(metadata=metadata, resources=resources)

    # If the user provides a model name and version, we use to model abstraction
    # to fetch the model version and attach the corresponding metadata to it.
    elif model_name is not None and model_version is not None:
        from zenml import Model

        mv = Model(name=model_name, version=model_version)

        client.create_run_metadata(
            metadata=metadata,
            resources=[(mv.id, MetadataResourceTypes.MODEL_VERSION)],
        )

    # If the user provides a model version id, we use the client to fetch it and
    # attach the metadata to it.
    elif model_version_id is not None:
        client.create_run_metadata(
            metadata=metadata,
            resources=[
                (model_version_id, MetadataResourceTypes.MODEL_VERSION)
            ],
        )

    # If the user provides an artifact name, there are three possibilities. If
    # an artifact version is also provided with the name, we use both to fetch
    # the artifact version and use it to log the metadata. If no version is
    # provided, if the function is called within a step we search the artifacts
    # of the step if not we fetch the latest version and attach the metadata
    # to the latest version.
    elif artifact_name is not None:
        if artifact_version:
            artifact_version_model = client.get_artifact_version(
                name_id_or_prefix=artifact_name, version=artifact_version
            )
            client.create_run_metadata(
                metadata=metadata,
                resources=[
                    (
                        artifact_version_model.id,
                        MetadataResourceTypes.ARTIFACT_VERSION,
                    )
                ],
            )
        else:
            step_context = None
            with contextlib.suppress(RuntimeError):
                step_context = get_step_context()

            if step_context:
                step_context.add_output_metadata(
                    metadata=metadata, output_name=artifact_name
                )
            else:
                artifact_version_model = client.get_artifact_version(
                    name_id_or_prefix=artifact_name
                )
                client.create_run_metadata(
                    metadata=metadata,
                    resources=[
                        (
                            artifact_version_model.id,
                            MetadataResourceTypes.ARTIFACT_VERSION,
                        )
                    ],
                )

    # If the user directly provides an artifact_version_id, we use the client to
    # fetch is and attach the metadata accordingly.
    elif artifact_version_id is not None:
        client.create_run_metadata(
            metadata=metadata,
            resources=[
                (artifact_version_id, MetadataResourceTypes.ARTIFACT_VERSION)
            ],
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
        resources = [
            (step_context.step_run.id, MetadataResourceTypes.STEP_RUN),
            (step_context.pipeline_run.id, MetadataResourceTypes.PIPELINE_RUN),
        ]
        if step_context.model_version:
            resources.append(
                (
                    step_context.model_version.id,
                    MetadataResourceTypes.MODEL_VERSION,
                )
            )
        client.create_run_metadata(
            metadata=metadata,
            resources=resources,
        )

    else:
        raise ValueError(
            """
            Unsupported way to call the `log_metadata`. Possible combinations "
            include:
            
            # Inside a step
            # Logs the metadata to the step, its run and possibly its model
            log_metadata(metadata={})
            
            # Manually logging for a step
            # Logs the metadata to the step, its run and possibly its model
            log_metadata(metadata={}, step_name=..., run_id_name_or_prefix=...)
            log_metadata(metadata={}, step_id=...)
            
            # Manually logging for a run 
            # Logs the metadata to the run, possibly its model
            log_metadata(metadata={}, run_id_name_or_prefix=...)
            
            # Manually logging for a model
            log_metadata(metadata={}, model_name=..., model_version=...)
            log_metadata(metadata={}, model_version_id=...)
            
            # Manually logging for an artifact
            log_metadata(metadata={}, artifact_name=...)  # inside a step 
            log_metadata(metadata={}, artifact_name=..., artifact_version=...)
            log_metadata(metadata={}, artifact_version_id=...)
            """
        )
