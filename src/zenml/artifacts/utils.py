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
"""Utility functions for logging artifact metadata."""

from typing import Dict, Optional

from zenml.client import Client
from zenml.exceptions import StepContextError
from zenml.metadata.metadata_types import MetadataType
from zenml.new.steps.step_context import get_step_context


def log_artifact_metadata(
    metadata: Dict[str, MetadataType],
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
) -> None:
    """Log artifact metadata.

    This function can be used to log metadata for either existing artifacts or
    artifacts that are newly created in the same step.

    Args:
        metadata: The metadata to log.
        artifact_name: The name of the artifact to log metadata for. Can
            be omitted when being called inside a step with only one output.
        artifact_version: The version of the artifact to log metadata for. If
            not provided, the default behavior is as follows:
            - when being called inside a step that produces an artifact named
                `artifact_name`, the metadata will be associated to the
                corresponding newly created artifact.
            - when being called outside of a step, or in a step that does not
                produce any artifact named `artifact_name`, the metadata will
                be associated to the latest version of that artifact.

    Raises:
        ValueError:
            - If no artifact name is provided and the function is not called
                inside a step with a single output.
            - If neither an artifact nor an output with the given name exists.
    """
    try:
        step_context = get_step_context()
        in_step_outputs = artifact_name in step_context._outputs
    except StepContextError:
        step_context = None
        in_step_outputs = False

    if not step_context or not in_step_outputs or artifact_version:
        if not artifact_name:
            raise ValueError(
                "Artifact name must be provided unless the function is called "
                "inside a step with a single output."
            )
        client = Client()
        artifact = client.get_artifact(artifact_name, artifact_version)
        # TODO
        # update_model = ArtifactUpdateModel(metadata=metadata)
        # client.update_artifact(artifact.id, update_model)

    else:
        try:
            step_context.add_output_metadata(
                metadata=metadata, output_name=artifact_name
            )
        except StepContextError as e:
            raise ValueError(e)
