#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utilities for outputs."""

import os
from typing import TYPE_CHECKING, Dict, Sequence, Type

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.config.step_configurations import Step
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models.step_run_models import StepRunResponseModel
from zenml.stack import Stack
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore

logger = get_logger(__name__)


def generate_artifact_uri(
    artifact_store: "BaseArtifactStore",
    step_run: "StepRunResponseModel",
    output_name: str,
) -> str:
    """Generates a URI for an output artifact.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        step_run: The step run that created the artifact.
        output_name: The name of the output in the step run for this artifact.

    Returns:
        The URI of the output artifact.
    """
    return os.path.join(
        artifact_store.path,
        step_run.step.config.name,
        output_name,
        str(step_run.id),
    )


def prepare_output_artifacts(
    step_run: "StepRunResponseModel", stack: "Stack", step: "Step"
) -> Dict[str, BaseArtifact]:
    """Prepares the output artifacts to run the current step.

    Args:
        step_run: The step run for which to prepare the artifacts.
        stack: The stack on which the pipeline is running.
        step: The step configuration.

    Raises:
        RuntimeError: If the artifact URI already exists.

    Returns:
        The output artifacts.
    """
    output_artifacts: Dict[str, BaseArtifact] = {}
    for name, artifact_config in step.config.outputs.items():
        artifact_class: Type[
            BaseArtifact
        ] = source_utils.load_and_validate_class(
            artifact_config.artifact_source, expected_class=BaseArtifact
        )
        artifact_uri = generate_artifact_uri(
            artifact_store=stack.artifact_store,
            step_run=step_run,
            output_name=name,
        )
        if fileio.exists(artifact_uri):
            raise RuntimeError("Artifact already exists")
        fileio.makedirs(artifact_uri)

        artifact_ = artifact_class(
            name=name,
            uri=artifact_uri,
        )
        output_artifacts[name] = artifact_

    return output_artifacts


def remove_artifact_dirs(artifacts: Sequence[BaseArtifact]) -> None:
    """Removes the artifact directories.

    Args:
        artifacts: Artifacts for which to remove the directories.
    """
    for artifact in artifacts:
        if fileio.isdir(artifact.uri):
            fileio.rmtree(artifact.uri)
