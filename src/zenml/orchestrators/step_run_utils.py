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
from zenml.config.step_configurations import Step
from zenml.constants import TEXT_FIELD_MAX_LENGTH
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
    """Helper class to create step run requests."""

    def __init__(
        self,
        deployment: "PipelineDeploymentResponse",
        pipeline_run: "PipelineRunResponse",
        stack: "Stack",
    ) -> None:
        """Initialize the object.

        Args:
            deployment: The deployment for which to create step run requests.
            pipeline_run: The pipeline run for which to create step run
                requests.
            stack: The stack on which the pipeline run is happening.
        """
        self.deployment = deployment
        self.pipeline_run = pipeline_run
        self.stack = stack

    def create_request(self, invocation_id: str) -> StepRunRequest:
        """Create a step run request.

        This will only create a request with basic information and will not yet
        compute information like the cache key and inputs. This is separated
        into a different method `populate_request(...)` that might raise
        exceptions while trying to compute this information.

        Args:
            invocation_id: The invocation ID for which to create the request.

        Returns:
            The step run request.
        """
        return StepRunRequest(
            name=invocation_id,
            pipeline_run_id=self.pipeline_run.id,
            deployment=self.deployment.id,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.utcnow(),
            user=Client().active_user.id,
            workspace=Client().active_workspace.id,
        )

    def populate_request(self, request: StepRunRequest) -> None:
        """Populate a step run request with additional information.

        Args:
            request: The request to populate.
        """
        step = self.deployment.step_configurations[request.name]

        # TODO: How do we ensure this uses the same model version that we also
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
        request.inputs = input_artifact_ids
        request.parent_step_ids = parent_step_ids

        cache_key = cache_utils.generate_cache_key(
            step=step,
            input_artifact_ids=input_artifact_ids,
            artifact_store=self.stack.artifact_store,
            workspace_id=Client().active_workspace.id,
        )
        request.cache_key = cache_key

        # TODO: doing this here means this will always fail when running a
        # template, as the step dependencies are not installed in that case
        (
            docstring,
            source_code,
        ) = self._get_docstring_and_source_code(step=step)

        request.docstring = docstring
        request.source_code = source_code

        cache_enabled = utils.is_setting_enabled(
            is_enabled_on_step=step.config.enable_cache,
            is_enabled_on_pipeline=self.deployment.pipeline_configuration.enable_cache,
        )

        if cache_enabled:
            if cached_step_run := cache_utils.get_cached_step_run(
                cache_key=cache_key
            ):
                # TODO: if the step is cached, do we also want to include
                # all the inputs of the original step? This would only make
                # a difference if the original step did some dynamic loading
                # of artifacts using `load_artifact`, which would then not be
                # included for the new one
                
                # request.inputs = {
                #     input_name: artifact.id
                #     for input_name, artifact in cached_step_run.inputs.items()
                # }

                request.original_step_run_id = cached_step_run.id
                request.outputs = {
                    output_name: artifact.id
                    for output_name, artifact in cached_step_run.outputs.items()
                }

                request.status = ExecutionStatus.CACHED
                request.end_time = request.start_time

    @staticmethod
    def _get_docstring_and_source_code(
        step: "Step",
    ) -> Tuple[Optional[str], str]:
        """Gets the docstring and source code of a step.

        Returns:
            The docstring and source code of a step.
        """
        from zenml.steps.base_step import BaseStep

        step_instance = BaseStep.load_from_source(step.spec.source)

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
) -> Set[str]:
    """Find invocations that can potentially be cached.

    Args:
        deployment: The pipeline deployment containing the invocations.
        finished_invocations: A set of invocations that are already finished.

    Returns:
        The set of invocations that can potentially be cached.
    """
    invocations = set()
    for invocation_id, step in deployment.step_configurations.items():
        if invocation_id in finished_invocations:
            continue

        cache_enabled = utils.is_setting_enabled(
            is_enabled_on_step=step.config.enable_cache,
            is_enabled_on_pipeline=deployment.pipeline_configuration.enable_cache,
        )

        if not cache_enabled:
            continue

        if set(step.spec.upstream_steps) - finished_invocations:
            continue

        invocations.add(invocation_id)

    return invocations


def create_cached_step_runs(
    deployment: "PipelineDeploymentResponse",
    pipeline_run: PipelineRunResponse,
    stack: "Stack",
) -> Set[str]:
    """Create all cached step runs for a pipeline run.

    Args:
        deployment: The deployment of the pipeline run.
        pipeline_run: The pipeline run for which to create the step runs.
        stack: The stack on which the pipeline run is happening.

    Returns:
        The invocation IDs of the created step runs.
    """
    cached_invocations: Set[str] = set()
    visited_invocations: Set[str] = set()
    request_factory = StepRunRequestFactory(
        deployment=deployment, pipeline_run=pipeline_run, stack=stack
    )

    while (
        cache_candidates := find_cacheable_invocation_candidates(
            deployment=deployment,
            finished_invocations=cached_invocations,
        )
        - visited_invocations
    ):
        for invocation_id in cache_candidates:
            visited_invocations.add(invocation_id)

            try:
                step_run_request = request_factory.create_request(
                    invocation_id
                )
                request_factory.populate_request(step_run_request)
            except Exception as e:
                # We failed to create/populate the step run. This might be due
                # to some input resolution error, or an error importing the step
                # source (there might be some missing dependencies). We just
                # treat the step as not cached and let the orchestrator try
                # again in a potentially different environment.
                logger.debug(
                    "Failed preparing step run `%s`: %s", invocation_id, str(e)
                )
                continue

            if step_run_request.status != ExecutionStatus.CACHED:
                # If we're not able to cache the step run, the orchestrator
                # will run the step later which will create the step run
                # -> We don't need to do anything here
                continue

            step_run = Client().zen_store.create_run_step(step_run_request)
            model = get_and_link_model(
                deployment=deployment,
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
            # link_models_to_pipeline_run(
            #     step_run=step_run, step_run_model=model
            # )

            logger.info("Using cached version of step `%s`.", invocation_id)
            cached_invocations.add(invocation_id)

    return cached_invocations


def get_and_link_model(
    deployment: PipelineDeploymentResponse,
    pipeline_run: PipelineRunResponse,
    step_run: StepRunResponse,
) -> Optional["Model"]:
    model = step_run.config.model or deployment.pipeline_configuration.model

    if model:
        pass_step_run = step_run.config.model is not None
        preparation_logs = model._prepare_model_version_before_step_launch(
            pipeline_run=pipeline_run,
            step_run=step_run if pass_step_run else None,
            return_logs=True,
        )

        if preparation_logs:
            logger.info(preparation_logs)

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


def fetch_or_create_model(
    model: Model, pipeline_run: PipelineRunResponse
) -> Model:
    if model.model_version_id:
        return (
            Client()
            .get_model_version(
                model_name_or_id=model.name,
                model_version_name_or_number_or_id=model.model_version_id,
            )
            .to_model_class()
        )

    if model.version:
        return (
            Client()
            .get_model_version(
                model_name_or_id=model.name,
                model_version_name_or_number_or_id=model.version,
            )
            .to_model_class()
        )

    # The model version should be created as part of this run
    # -> We first check if it was already created as part of this run, and if
    # not we do create it. If this is running in two parallel steps, we might
    # run into issues that this will create two versions
    if pipeline_run.config.model and pipeline_run.model_version:
        if (
            pipeline_run.config.model.name == model.name
            and pipeline_run.config.model.version is None
        ):
            return pipeline_run.model_version.to_model_class()

    for _, step_run in pipeline_run.steps.items():
        if step_run.config.model and step_run.model_version:
            if (
                step_run.config.model.name == model.name
                and step_run.config.model.version is None
            ):
                return step_run.model_version.to_model_class()

    # We did not find any existing model that matches -> Create one
    return model._get_or_create_model_version().to_model_class()
