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
from datetime import datetime
from typing import List, Optional, Set, Tuple

from zenml import Model
from zenml.client import Client
from zenml.config.source import Source
from zenml.constants import (
    STEP_SOURCE_PARAMETER_NAME,
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.models import (
    ModelVersionPipelineRunRequest,
    PipelineDeploymentResponse,
    PipelineRunResponse,
    StepRunRequest,
    StepRunResponse,
)
from zenml.orchestrators import cache_utils, input_utils, utils
from zenml.stack import Stack

logger = get_logger(__name__)


class StepRunRequestFactory:
    def __init__(
        self,
        deployment: "PipelineDeploymentResponse",
        pipeline_run: "PipelineRunResponse",
        stack: "Stack",
    ) -> None:
        self.deployment = deployment
        self.pipeline_run = pipeline_run
        self.stack = stack

    def create_request(self, invocation_id: str) -> StepRunRequest:
        step = self.deployment.step_configurations[invocation_id]

        # How do we ensure this uses the same model version that we also
        # link later, when using a model lazy loader. This only applies
        # after we fixed the issue that the model lazy loader always
        # creates the model version client side and stores in ID in the
        # config.
        input_artifacts, parent_step_ids = input_utils.resolve_step_inputs(
            step=step,
            run_id=self.pipeline_run.id,
        )
        input_artifact_ids = {
            input_name: artifact.id
            for input_name, artifact in input_artifacts.items()
        }

        cache_key = cache_utils.generate_cache_key(
            step=step,
            input_artifact_ids=input_artifact_ids,
            artifact_store=self.stack.artifact_store,
            workspace_id=Client().active_workspace.id,
        )

        (
            docstring,
            source_code,
        ) = self._get_step_docstring_and_source_code()
        code_hash = step.config.caching_parameters.get(
            STEP_SOURCE_PARAMETER_NAME
        )
        step_run_request = StepRunRequest(
            name=invocation_id,
            pipeline_run_id=self.pipeline_run.id,
            deployment=self.deployment.id,
            status=ExecutionStatus.RUNNING,
            cache_key=cache_key,
            docstring=docstring,
            source_code=source_code,
            code_hash=code_hash,
            start_time=datetime.utcnow(),
            user=Client().active_user.id,
            workspace=Client().active_workspace.id,
            logs=None,
            inputs=input_artifact_ids,
            parent_step_ids=parent_step_ids,
        )

        cache_enabled = utils.is_setting_enabled(
            is_enabled_on_step=step.config.enable_cache,
            is_enabled_on_pipeline=self.deployment.pipeline_configuration.enable_cache,
        )

        if cache_enabled:
            if cached_step_run := cache_utils.get_cached_step_run(
                cache_key=cache_key
            ):
                step_run_request.original_step_run_id = cached_step_run.id
                step_run_request.outputs = {
                    output_name: artifact.id
                    for output_name, artifact in cached_step_run.outputs.items()
                }

                step_run_request.status = ExecutionStatus.CACHED
                step_run_request.end_time = step_run_request.start_time

        return step_run_request

    def _get_step_docstring_and_source_code(self) -> Tuple[Optional[str], str]:
        """Gets the docstring and source code of the step.

        Returns:
            The docstring and source code of the step.
        """
        from zenml.steps.base_step import BaseStep

        step_instance = BaseStep.load_from_source(self._step.spec.source)

        docstring = step_instance.docstring
        if docstring and len(docstring) > TEXT_FIELD_MAX_LENGTH:
            docstring = docstring[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."

        source_code = step_instance.source_code
        if source_code and len(source_code) > TEXT_FIELD_MAX_LENGTH:
            source_code = source_code[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."

        return docstring, source_code


def find_cacheable_invocation_candidates(
    deployment: "PipelineDeploymentResponse",
    finished_invocations: Set[str],
    visited_invocations: Set[str],
) -> List[str]:
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

        invocations.append(invocation_id)

    return invocations


def create_cached_steps(
    deployment: "PipelineDeploymentResponse",
    pipeline_run: PipelineRunResponse,
    stack: "Stack",
) -> Set[str]:
    cached_invocations = set()
    visited_invocations = set()
    request_factory = StepRunRequestFactory(
        deployment=deployment, pipeline_run=pipeline_run, stack=stack
    )

    while cache_candidates := find_cacheable_invocation_candidates(
        deployment=deployment,
        finished_invocations=cached_invocations,
        visited_invocations=visited_invocations,
    ):
        for invocation_id in cache_candidates:
            visited_invocations.add(invocation_id)

            try:
                step_run_request = request_factory.create_request(
                    invocation_id
                )
            except Exception:
                # We failed to create the step run. This might be due to some
                # input resolution error, or an error importing the step source
                # (there might not be all the requirements installed?). We can
                # either handle these now or just treat the step as not cached
                # and let the orchestrator try again in a potentially different
                # environment.
                pass
            else:
                if step_run_request.status != ExecutionStatus.CACHED:
                    # If we're not able to cache the step run, the orchestrator
                    # will run the step later which will create the step in the
                    # server -> We don't need to do anything here
                    continue

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
                    step_source=step_run.spec.source,
                )
                if model:
                    # TODO: this does not respect models in the artifact config?
                    utils._link_pipeline_run_to_model_from_context(
                        pipeline_run_id=pipeline_run.id, model=model
                    )
                # Alternative to the above
                link_models_to_pipeline_run(
                    step_run=step_run, step_run_model=model
                )

                logger.info(
                    "Using cached version of step `%s`.", invocation_id
                )
                cached_invocations.add(invocation_id)

    return cached_invocations


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


def link_models_to_pipeline_run(
    step_run: StepRunResponse, step_run_model: Optional[Model]
) -> None:
    models = get_all_models_from_step_outputs(step_source=step_run.spec.source)
    if step_run_model:
        models.append(step_run_model)

    for model in models:
        model._get_or_create_model_version()
        Client().zen_store.create_model_version_pipeline_run_link(
            ModelVersionPipelineRunRequest(
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
                pipeline_run=step_run.pipeline_run_id,
                model=model.model_id,
                model_version=model.model_version_id,
            )
        )


def get_all_models_from_step_outputs(step_source: Source) -> List[Model]:
    # TODO: This does not cover dynamic artifacts by calling `save_artifact`.
    # It seems like `save_artifact` however does not allow linking to a specific
    # model but always uses the one from the step context, in which case we
    # don't really need to care about it

    from zenml.steps.base_step import BaseStep
    from zenml.steps.utils import parse_return_type_annotations

    step_instance = BaseStep.load_from_source(step_source)
    output_annotations = parse_return_type_annotations(
        step_instance.entrypoint
    )

    models = []

    for output in output_annotations.values():
        if output.artifact_config and output.artifact_config.model_name:
            model = Model(
                name=output.artifact_config.model_name,
                version=output.artifact_config.model_version,
            )
            models.append(model)

    return models
