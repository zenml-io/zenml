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
from typing import TYPE_CHECKING, Dict, Sequence
from uuid import uuid4

from zenml.client import Client
from zenml.constants import IN_MEMORY_ARTIFACT_URI_PREFIX
from zenml.logger import get_logger
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import StepRunResponse
    from zenml.stack import Stack


logger = get_logger(__name__)


def generate_artifact_uri(
    artifact_store_path: str,
    step_run: "StepRunResponse",
    output_name: str,
) -> str:
    """Generates a URI for an output artifact.

    Args:
        artifact_store_path: The path of the artifact store in which the
            artifact will be stored.
        step_run: The step run that created the artifact.
        output_name: The name of the output in the step run for this artifact.

    Returns:
        The URI of the output artifact.
    """
    for banned_character in ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]:
        output_name = output_name.replace(banned_character, "_")
    return os.path.join(
        artifact_store_path,
        step_run.name,
        output_name,
        str(step_run.id),
        str(uuid4())[:8],  # add random subfolder to avoid collisions
    )


def prepare_output_artifact_uris(
    step_run: "StepRunResponse",
    stack: "Stack",
    step: "Step",
    *,
    skip_artifact_materialization: bool = False,
) -> Dict[str, str]:
    """Prepares the output artifact URIs to run the current step.

    Args:
        step_run: The step run for which to prepare the artifact URIs.
        stack: The stack on which the pipeline is running.
        step: The step configuration.
        skip_artifact_materialization: Whether to skip artifact materialization.

    Raises:
        RuntimeError: If an artifact URI already exists.

    Returns:
        A dictionary mapping output names to artifact URIs.
    """
    artifact_store = stack.artifact_store
    output_artifact_uris: Dict[str, str] = {}

    for output_name in step.config.outputs.keys():
        substituted_output_name = string_utils.format_name_template(
            output_name, substitutions=step_run.config.substitutions
        )
        artifact_store_path = (
            IN_MEMORY_ARTIFACT_URI_PREFIX
            if skip_artifact_materialization
            else artifact_store.path
        )
        artifact_uri = generate_artifact_uri(
            artifact_store_path=artifact_store_path,
            step_run=step_run,
            output_name=substituted_output_name,
        )

        if not skip_artifact_materialization:
            if artifact_store.exists(artifact_uri):
                raise RuntimeError("Artifact already exists")
            artifact_store.makedirs(artifact_uri)
        output_artifact_uris[output_name] = artifact_uri
    return output_artifact_uris


def remove_artifact_dirs(artifact_uris: Sequence[str]) -> None:
    """Removes the artifact directories.

    Args:
        artifact_uris: URIs of the artifacts to remove the directories for.
    """
    artifact_store = Client().active_stack.artifact_store
    for artifact_uri in artifact_uris:
        if artifact_store.isdir(artifact_uri):
            artifact_store.rmtree(artifact_uri)
