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
"""Utilities for inputs."""

from typing import Dict, List, Tuple
from uuid import UUID

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.exceptions import InputResolutionError


def resolve_step_inputs(
    step: "Step", run_id: UUID
) -> Tuple[Dict[str, UUID], List[UUID]]:
    """Resolves inputs for the current step.

    Args:
        step: The step for which to resolve the inputs.
        run_id: The ID of the current pipeline run.

    Raises:
        InputResolutionError: If input resolving failed due to a missing
            step or output.

    Returns:
        The IDs of the input artifacts and the IDs of parent steps of the
        current step.
    """
    current_run_steps = {
        run_step.step.config.name: run_step
        for run_step in Client().zen_store.list_run_steps(run_id=run_id)
    }

    input_artifact_ids: Dict[str, UUID] = {}
    for name, input_ in step.spec.inputs.items():
        try:
            step_run = current_run_steps[input_.step_name]
        except KeyError:
            raise InputResolutionError(
                f"No step `{input_.step_name}` found in current run."
            )

        try:
            artifact_id = step_run.output_artifacts[input_.output_name]
        except KeyError:
            raise InputResolutionError(
                f"No output `{input_.output_name}` found for step "
                f"`{input_.step_name}`."
            )

        input_artifact_ids[name] = artifact_id

    parent_step_ids = [
        current_run_steps[upstream_step].id
        for upstream_step in step.spec.upstream_steps
    ]

    return input_artifact_ids, parent_step_ids


def prepare_input_artifacts(
    input_artifact_ids: Dict[str, UUID]
) -> Dict[str, BaseArtifact]:
    """Prepares the input artifacts to run the current step.

    Args:
        input_artifact_ids: IDs of all input artifacts for the step.

    Returns:
        The input artifacts.
    """
    input_artifacts: Dict[str, BaseArtifact] = {}
    for name, artifact_id in input_artifact_ids.items():
        artifact_model = Client().zen_store.get_artifact(
            artifact_id=artifact_id
        )
        artifact_ = BaseArtifact(
            uri=artifact_model.uri,
            materializer=artifact_model.materializer,
            data_type=artifact_model.data_type,
            name=name,
        )
        input_artifacts[name] = artifact_

    return input_artifacts
