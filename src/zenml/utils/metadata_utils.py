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

from typing import Dict, List, Optional, Union, overload
from uuid import UUID

from zenml.client import Client
from zenml.enums import MetadataResourceTypes, ModelStages
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models import RunMetadataResource
from zenml.steps.step_context import get_step_context

logger = get_logger(__name__)


@overload
def log_metadata(
    metadata: Dict[str, MetadataType],
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
    step_name: str,
    run_id_name_or_prefix: Union[UUID, str],
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
    infer_artifact: bool = False,
    artifact_name: Optional[str] = None,
) -> None: ...


# Model Metadata
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
    model_version: Union[ModelStages, int, str],
) -> None: ...


@overload
def log_metadata(
    *,
    metadata: Dict[str, MetadataType],
    infer_model: bool = False,
) -> None: ...


def log_metadata(
    metadata: Dict[str, MetadataType],
    # Steps and runs
    step_id: Optional[UUID] = None,
    step_name: Optional[str] = None,
    run_id_name_or_prefix: Optional[Union[UUID, str]] = None,
    # Artifacts
    artifact_version_id: Optional[UUID] = None,
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
    infer_artifact: bool = False,
    # Models
    model_version_id: Optional[UUID] = None,
    model_name: Optional[str] = None,
    model_version: Optional[Union[ModelStages, int, str]] = None,
    infer_model: bool = False,
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
        infer_artifact: Flag deciding whether the artifact version should be
            inferred from the step context.
        model_version_id: The ID of the model version.
        model_name: The name of the model.
        model_version: The version of the model.
        infer_model: Flag deciding whether the model version should be
            inferred from the step context.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    client = Client()

    resources: List[RunMetadataResource] = []
    publisher_step_id = None

    # Log metadata to a step by ID
    if step_id is not None:
        resources = [
            RunMetadataResource(
                id=step_id, type=MetadataResourceTypes.STEP_RUN
            )
        ]

    # Log metadata to a step by name and run ID
    elif step_name is not None and run_id_name_or_prefix is not None:
        step_model_id = (
            client.get_pipeline_run(name_id_or_prefix=run_id_name_or_prefix)
            .steps[step_name]
            .id
        )
        resources = [
            RunMetadataResource(
                id=step_model_id, type=MetadataResourceTypes.STEP_RUN
            )
        ]

    # Log metadata to a run by ID
    elif run_id_name_or_prefix is not None:
        run_model = client.get_pipeline_run(
            name_id_or_prefix=run_id_name_or_prefix
        )
        resources = [
            RunMetadataResource(
                id=run_model.id, type=MetadataResourceTypes.PIPELINE_RUN
            )
        ]

    # Log metadata to a model version by name and version
    elif model_name is not None and model_version is not None:
        model_version_model = client.get_model_version(
            model_name_or_id=model_name,
            model_version_name_or_number_or_id=model_version,
        )
        resources = [
            RunMetadataResource(
                id=model_version_model.id,
                type=MetadataResourceTypes.MODEL_VERSION,
            )
        ]

    # Log metadata to a model version by id
    elif model_version_id is not None:
        resources = [
            RunMetadataResource(
                id=model_version_id,
                type=MetadataResourceTypes.MODEL_VERSION,
            )
        ]

    # Log metadata to a model through the step context
    elif infer_model is True:
        try:
            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                "If you are using the `infer_model` option, the function must "
                "be called inside a step with configured `model` in decorator."
                "Otherwise, you can provide a `model_version_id` or a "
                "combination of `model_name` and `model_version`."
            )
        resources = [
            RunMetadataResource(
                id=step_context.model_version.id,
                type=MetadataResourceTypes.MODEL_VERSION,
            )
        ]

    # Log metadata to an artifact version by its name and version
    elif artifact_name is not None and artifact_version is not None:
        artifact_version_model = client.get_artifact_version(
            name_id_or_prefix=artifact_name, version=artifact_version
        )
        resources = [
            RunMetadataResource(
                id=artifact_version_model.id,
                type=MetadataResourceTypes.ARTIFACT_VERSION,
            )
        ]

    # Log metadata to an artifact version by its ID
    elif artifact_version_id is not None:
        resources = [
            RunMetadataResource(
                id=artifact_version_id,
                type=MetadataResourceTypes.ARTIFACT_VERSION,
            )
        ]

    # Log metadata to an artifact version through the step context
    elif infer_artifact is True:
        try:
            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                "When you are using the `infer_artifact` option when you call "
                "`log_metadata`, it must be called inside a step with outputs."
                "Otherwise, you can provide a `artifact_version_id` or a "
                "combination of `artifact_name` and `artifact_version`."
            )

        step_output_names = list(step_context._outputs.keys())

        if artifact_name is not None:
            # If a name provided, ensure it is in the outputs
            if artifact_name not in step_output_names:
                raise ValueError(
                    f"The provided artifact name`{artifact_name}` does not "
                    f"exist in the step outputs: {step_output_names}."
                )
        else:
            # If no name provided, ensure there is only one output
            if len(step_output_names) > 1:
                raise ValueError(
                    "There is more than one output. If you would like to use "
                    "the `infer_artifact` option, you need to define an "
                    "`artifact_name`."
                )

            if len(step_output_names) == 0:
                raise ValueError("The step does not have any outputs.")

            artifact_name = step_output_names[0]

        step_context.add_output_metadata(
            metadata=metadata, output_name=artifact_name
        )
        return

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
            RunMetadataResource(
                id=step_context.step_run.id,
                type=MetadataResourceTypes.STEP_RUN,
            )
        ]
        publisher_step_id = (step_context.step_run.id,)

    else:
        raise ValueError(
            """
            Unsupported way to call the `log_metadata`. Possible combinations "
            include:
            
            # Automatic logging to a step (within a step)
            log_metadata(metadata={})
            
            # Manual logging to a step
            log_metadata(metadata={}, step_name=..., run_id_name_or_prefix=...)
            log_metadata(metadata={}, step_id=...)
            
            # Manual logging to a run
            log_metadata(metadata={}, run_id_name_or_prefix=...)
            
            # Automatic logging to a model (within a step)
            log_metadata(metadata={}, infer_model=True)
            
            # Manual logging to a model
            log_metadata(metadata={}, model_name=..., model_version=...)
            log_metadata(metadata={}, model_version_id=...)
            
            # Automatic logging to an artifact (within a step)
            log_metadata(metadata={}, infer_artifact=True)  # step with single output
            log_metadata(metadata={}, artifact_name=..., infer_artifact=True)  # specific output of a step
            
            # Manual logging to an artifact
            log_metadata(metadata={}, artifact_name=..., artifact_version=...)
            log_metadata(metadata={}, artifact_version_id=...)
            """
        )

    client.create_run_metadata(
        metadata=metadata,
        resources=resources,
        publisher_step_id=publisher_step_id,
    )
