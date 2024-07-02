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

from typing import TYPE_CHECKING, Dict, List, Tuple
from uuid import UUID

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.exceptions import InputResolutionError
from zenml.utils import pagination_utils

if TYPE_CHECKING:
    from zenml.models import ArtifactVersionResponse


def resolve_step_inputs(
    step: "Step",
    run_id: UUID,
) -> Tuple[Dict[str, "ArtifactVersionResponse"], List[UUID]]:
    """Resolves inputs for the current step.

    Args:
        step: The step for which to resolve the inputs.
        run_id: The ID of the current pipeline run.

    Raises:
        InputResolutionError: If input resolving failed due to a missing
            step or output.
        ValueError: If object from model version passed into a step cannot be
            resolved in runtime due to missing object.

    Returns:
        The IDs of the input artifact versions and the IDs of parent steps of
            the current step.
    """
    from zenml.models import ArtifactVersionResponse, RunMetadataResponse

    current_run_steps = {
        run_step.name: run_step
        for run_step in pagination_utils.depaginate(
            Client().list_run_steps, pipeline_run_id=run_id
        )
    }

    input_artifacts: Dict[str, "ArtifactVersionResponse"] = {}
    for name, input_ in step.spec.inputs.items():
        try:
            step_run = current_run_steps[input_.step_name]
        except KeyError:
            raise InputResolutionError(
                f"No step `{input_.step_name}` found in current run."
            )

        try:
            artifact = step_run.outputs[input_.output_name]
        except KeyError:
            raise InputResolutionError(
                f"No output `{input_.output_name}` found for step "
                f"`{input_.step_name}`."
            )

        input_artifacts[name] = artifact

    for (
        name,
        external_artifact,
    ) in step.config.external_input_artifacts.items():
        artifact_version_id = external_artifact.get_artifact_version_id()
        input_artifacts[name] = Client().get_artifact_version(
            artifact_version_id
        )

    for name, config_ in step.config.model_artifacts_or_metadata.items():
        issue_found = False
        try:
            if config_.metadata_name is None and config_.artifact_name:
                if artifact_ := config_.model.get_artifact(
                    config_.artifact_name, config_.artifact_version
                ):
                    input_artifacts[name] = artifact_
                else:
                    issue_found = True
            elif config_.artifact_name is None and config_.metadata_name:
                # metadata values should go directly in parameters, as primitive types
                step.config.parameters[name] = config_.model.run_metadata[
                    config_.metadata_name
                ].value
            elif config_.metadata_name and config_.artifact_name:
                # metadata values should go directly in parameters, as primitive types
                if artifact_ := config_.model.get_artifact(
                    config_.artifact_name, config_.artifact_version
                ):
                    step.config.parameters[name] = artifact_.run_metadata[
                        config_.metadata_name
                    ].value
                else:
                    issue_found = True
            else:
                issue_found = True
        except KeyError:
            issue_found = True

        if issue_found:
            raise ValueError(
                "Cannot fetch requested information from model "
                f"`{config_.model.name}` version "
                f"`{config_.model.version}` given artifact "
                f"`{config_.artifact_name}`, artifact version "
                f"`{config_.artifact_version}`, and metadata "
                f"key `{config_.metadata_name}` passed into "
                f"the step `{step.config.name}`."
            )
    for name, cll_ in step.config.client_lazy_loaders.items():
        value_ = cll_.evaluate()
        if isinstance(value_, ArtifactVersionResponse):
            input_artifacts[name] = value_
        elif isinstance(value_, RunMetadataResponse):
            step.config.parameters[name] = value_.value
        else:
            step.config.parameters[name] = value_

    parent_step_ids = [
        current_run_steps[upstream_step].id
        for upstream_step in step.spec.upstream_steps
    ]

    return input_artifacts, parent_step_ids
