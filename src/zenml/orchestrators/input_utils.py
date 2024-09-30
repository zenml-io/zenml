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

from typing import TYPE_CHECKING, Dict, List, Set, Tuple
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


from datetime import datetime
from typing import Optional

from zenml import Model
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.models import (
    PipelineDeploymentResponse,
    PipelineRunResponse,
    StepRunRequest,
    StepRunResponse,
)
from zenml.orchestrators import cache_utils, publish_utils, utils
from zenml.stack import Stack

logger = get_logger(__name__)


def find_cacheable_invocation_candidates(
    deployment: "PipelineDeploymentResponse",
    finished_invocations: Set[str],
    visited_invocations: Set[str],
) -> List[str]:
    if deployment.schedule:
        # A solution for getting a similar behavior when running with
        # orchestrator-native scheduled pipelines: We add an additional "setup"
        # step that runs before all actual steps of the pipeline, which runs
        # this code to compute all the pre-cached steps. Probably not necessary
        # though as this will be supported out of the box for pipelines
        # scheduled via ZenML's native scheduling
        return []

    invocations = []
    for invocation_id, step in deployment.step_configurations.items():
        if invocation_id in visited_invocations:
            continue

        cache_enabled = utils.is_setting_enabled(
            is_enabled_on_step=step.config.enable_cache,
            is_enabled_on_pipeline=deployment.pipeline_configuration.enable_cache,
        )

        if not cache_enabled:
            continue

        if set(step.spec.upstream_steps) - finished_invocations:
            continue

        # TODO: Question for reviewers: My current thinking is that this
        # should not be affected by client lazy loaders or model lazy loaders.
        # Am I missing something?
        invocations.append(invocation_id)

    return invocations


def do_something(
    deployment: "PipelineDeploymentResponse",
    pipeline_run: PipelineRunResponse,
    stack: "Stack",
) -> None:
    cached_invocations = set()
    visited_invocations = set()

    while cache_candidates := find_cacheable_invocation_candidates(
        deployment=deployment,
        finished_invocations=cached_invocations,
        visited_invocations=visited_invocations,
    ):
        for invocation_id in cache_candidates:
            visited_invocations.add(invocation_id)

            step = deployment.step_configurations[invocation_id]

            # How do we ensure this uses the same model version that we also
            # link later, when using a model lazy loader. This only applies
            # after we fixed the issue that the model lazy loader always
            # creates the model version client side and stores in ID in the
            # config.
            input_artifacts, parent_step_ids = resolve_step_inputs(
                step=step, run_id=pipeline_run.id
            )
            input_artifact_ids = {
                input_name: artifact.id
                for input_name, artifact in input_artifacts.items()
            }

            cache_key = cache_utils.generate_cache_key(
                step=step,
                input_artifact_ids=input_artifact_ids,
                artifact_store=stack.artifact_store,
                workspace_id=Client().active_workspace.id,
            )

            if cached_step_run := cache_utils.get_cached_step_run(
                cache_key=cache_key
            ):
                now = datetime.utcnow()
                step_run_request = StepRunRequest(
                    name=invocation_id,
                    pipeline_run_id=pipeline_run.id,
                    deployment=deployment.id,
                    status=ExecutionStatus.CACHED,
                    cache_key=cache_key,
                    docstring=None,
                    source_code=None,
                    code_hash=None,
                    start_time=now,
                    end_time=now,
                    user=Client().active_user.id,
                    workspace=Client().active_workspace.id,
                    logs=None,
                    original_step_run_id=cached_step_run.id,
                    inputs=input_artifact_ids,
                    parent_step_ids=parent_step_ids,
                    outputs={
                        output_name: artifact.id
                        for output_name, artifact in cached_step_run.outputs.items()
                    },
                )
                step_run = Client().zen_store.create_run_step(step_run_request)
                model = get_and_link_model(
                    deployment=deployment,
                    invocation_id=invocation_id,
                    pipeline_run=pipeline_run,
                    step_run=step_run,
                )
                utils._link_cached_artifacts_to_model(
                    model_from_context=model,
                    step_run=step_run_request,
                    step_source=step.spec.source,
                )
                # TODO: this does not respect models in the artifact config?
                utils._link_pipeline_run_to_model_from_context(
                    pipeline_run_id=pipeline_run.id, model=model
                )
                logger.info(
                    "Using cached version of step `%s`.", invocation_id
                )
                cached_invocations.add(invocation_id)

    for invocation_id in cached_invocations:
        deployment.step_configurations.pop(invocation_id)

    if len(deployment.step_configurations) == 0:
        # All steps were cached, we update the pipeline run status
        publish_utils.publish_succesful_pipeline_run(pipeline_run.id)


def get_and_link_model(
    deployment: PipelineDeploymentResponse,
    invocation_id: str,
    pipeline_run: PipelineRunResponse,
    step_run: StepRunResponse,
) -> Optional["Model"]:
    step = deployment.step_configurations[invocation_id]
    model = step.config.model or deployment.pipeline_configuration.model

    if model:
        pass_step_run = step.config.model is not None
        model._prepare_model_version_before_step_launch(
            pipeline_run=pipeline_run,
            step_run=step_run if pass_step_run else None,
            return_logs=False,
        )

    return model
