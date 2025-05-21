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

import json
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from uuid import UUID

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.enums import StepRunInputArtifactType
from zenml.exceptions import InputResolutionError
from zenml.utils import pagination_utils, string_utils

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.models.v2.core.step_run import StepRunInputResponse


def resolve_step_inputs(
    step: "Step",
    pipeline_run: "PipelineRunResponse",
    step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
) -> Tuple[Dict[str, "StepRunInputResponse"], List[UUID]]:
    """Resolves inputs for the current step.

    Args:
        step: The step for which to resolve the inputs.
        pipeline_run: The current pipeline run.
        step_runs: A dictionary of already fetched step runs to use for input
            resolution. This will be updated in-place with newly fetched step
            runs.

    Raises:
        InputResolutionError: If input resolving failed due to a missing
            step or output.
        ValueError: If object from model version passed into a step cannot be
            resolved in runtime due to missing object.

    Returns:
        The IDs of the input artifact versions and the IDs of parent steps of
            the current step.
    """
    from zenml.models import ArtifactVersionResponse
    from zenml.models.v2.core.step_run import StepRunInputResponse

    step_runs = step_runs or {}

    steps_to_fetch = set(step.spec.upstream_steps)
    steps_to_fetch.update(
        input_.step_name for input_ in step.spec.inputs.values()
    )
    # Remove all the step runs that we've already fetched.
    steps_to_fetch.difference_update(step_runs.keys())

    if steps_to_fetch:
        step_runs.update(
            {
                run_step.name: run_step
                for run_step in pagination_utils.depaginate(
                    Client().list_run_steps,
                    pipeline_run_id=pipeline_run.id,
                    project=pipeline_run.project_id,
                    name="oneof:" + json.dumps(list(steps_to_fetch)),
                )
            }
        )

    input_artifacts: Dict[str, StepRunInputResponse] = {}
    for name, input_ in step.spec.inputs.items():
        try:
            step_run = step_runs[input_.step_name]
        except KeyError:
            raise InputResolutionError(
                f"No step `{input_.step_name}` found in current run."
            )

        output_name = string_utils.format_name_template(
            input_.output_name, substitutions=step_run.substitutions
        )

        try:
            output = step_run.regular_outputs[output_name]
        except KeyError:
            raise InputResolutionError(
                f"No step output `{output_name}` found for step "
                f"`{input_.step_name}`."
            )
        except ValueError:
            raise InputResolutionError(
                f"Expected 1 regular output artifact for {output_name}."
            )

        input_artifacts[name] = StepRunInputResponse(
            input_type=StepRunInputArtifactType.STEP_OUTPUT,
            **output.model_dump(),
        )

    for (
        name,
        external_artifact,
    ) in step.config.external_input_artifacts.items():
        artifact_version_id = external_artifact.get_artifact_version_id()
        input_artifacts[name] = StepRunInputResponse(
            input_type=StepRunInputArtifactType.EXTERNAL,
            **Client().get_artifact_version(artifact_version_id).model_dump(),
        )

    for name, config_ in step.config.model_artifacts_or_metadata.items():
        err_msg = ""
        try:
            context_model_version = config_._get_model_response(
                pipeline_run=pipeline_run
            )
        except RuntimeError as e:
            err_msg = str(e)
        else:
            if (
                config_.artifact_name is None
                and config_.metadata_name
                and context_model_version.run_metadata is not None
            ):
                # metadata values should go directly in parameters, as primitive types
                step.config.parameters[name] = (
                    context_model_version.run_metadata[config_.metadata_name]
                )
            elif config_.artifact_name is None:
                err_msg = (
                    "Cannot load artifact from model version, "
                    "no artifact name specified."
                )
            else:
                if artifact_ := context_model_version.get_artifact(
                    config_.artifact_name, config_.artifact_version
                ):
                    if config_.metadata_name is None:
                        input_artifacts[name] = StepRunInputResponse(
                            input_type=StepRunInputArtifactType.LAZY_LOADED,
                            **artifact_.model_dump(),
                        )
                    elif config_.metadata_name:
                        # metadata values should go directly in parameters, as primitive types
                        try:
                            step.config.parameters[name] = (
                                artifact_.run_metadata[config_.metadata_name]
                            )
                        except KeyError:
                            err_msg = (
                                f"Artifact run metadata `{config_.metadata_name}` "
                                "could not be found in artifact "
                                f"`{config_.artifact_name}::{config_.artifact_version}`."
                            )
                else:
                    err_msg = (
                        f"Artifact `{config_.artifact_name}::{config_.artifact_version}` "
                        f"not found in model `{context_model_version.model.name}` "
                        f"version `{context_model_version.name}`."
                    )
        if err_msg:
            raise ValueError(
                f"Failed to lazy load model version data in step `{step.config.name}`: "
                + err_msg
            )
    for name, cll_ in step.config.client_lazy_loaders.items():
        value_ = cll_.evaluate()
        if isinstance(value_, ArtifactVersionResponse):
            input_artifacts[name] = StepRunInputResponse(
                input_type=StepRunInputArtifactType.LAZY_LOADED,
                **value_.model_dump(),
            )
        else:
            step.config.parameters[name] = value_

    parent_step_ids = [
        step_runs[upstream_step].id
        for upstream_step in step.spec.upstream_steps
    ]

    return input_artifacts, parent_step_ids
