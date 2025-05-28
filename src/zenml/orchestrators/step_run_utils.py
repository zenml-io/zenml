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
"""Utilities for creating step runs."""

from typing import Dict, List, Optional, Set, Tuple, Union

from zenml import Tag, add_tags
from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.constants import CODE_HASH_PARAMETER_NAME, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.logger import get_logger
from zenml.model.utils import link_artifact_version_to_model_version
from zenml.models import (
    ArtifactVersionResponse,
    ModelVersionResponse,
    PipelineDeploymentResponse,
    PipelineRunResponse,
    StepRunRequest,
    StepRunResponse,
)
from zenml.orchestrators import cache_utils, input_utils, utils
from zenml.stack import Stack
from zenml.utils.time_utils import utc_now

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
            status=ExecutionStatus.RUNNING,
            start_time=utc_now(),
            project=Client().active_project.id,
        )

    def populate_request(
        self,
        request: StepRunRequest,
        step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
    ) -> None:
        """Populate a step run request with additional information.

        Args:
            request: The request to populate.
            step_runs: A dictionary of already fetched step runs to use for
                input resolution. This will be updated in-place with newly
                fetched step runs.
        """
        step = self.deployment.step_configurations[request.name]

        input_artifacts, parent_step_ids = input_utils.resolve_step_inputs(
            step=step,
            pipeline_run=self.pipeline_run,
            step_runs=step_runs,
        )
        input_artifact_ids = {
            input_name: artifact.id
            for input_name, artifact in input_artifacts.items()
        }

        request.inputs = {
            name: [artifact.id] for name, artifact in input_artifacts.items()
        }
        request.parent_step_ids = parent_step_ids

        cache_key = cache_utils.generate_cache_key(
            step=step,
            input_artifact_ids=input_artifact_ids,
            artifact_store=self.stack.artifact_store,
            project_id=Client().active_project.id,
        )
        request.cache_key = cache_key

        (
            docstring,
            source_code,
        ) = self._get_docstring_and_source_code(invocation_id=request.name)

        request.docstring = docstring
        request.source_code = source_code
        request.code_hash = step.config.parameters.get(
            CODE_HASH_PARAMETER_NAME
        )

        cache_enabled = utils.is_setting_enabled(
            is_enabled_on_step=step.config.enable_cache,
            is_enabled_on_pipeline=self.deployment.pipeline_configuration.enable_cache,
        )

        if cache_enabled:
            if cached_step_run := cache_utils.get_cached_step_run(
                cache_key=cache_key
            ):
                request.inputs = {
                    input_name: [artifact.id for artifact in artifacts]
                    for input_name, artifacts in cached_step_run.inputs.items()
                }

                request.original_step_run_id = cached_step_run.id
                request.outputs = {
                    output_name: [artifact.id for artifact in artifacts]
                    for output_name, artifacts in cached_step_run.outputs.items()
                }

                request.status = ExecutionStatus.CACHED
                request.end_time = request.start_time

    def _get_docstring_and_source_code(
        self, invocation_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get the docstring and source code for the step.

        Args:
            invocation_id: The step invocation ID for which to get the
                docstring and source code.

        Returns:
            The docstring and source code of the step.
        """
        step = self.deployment.step_configurations[invocation_id]

        try:
            return self._get_docstring_and_source_code_from_step_instance(
                step=step
            )
        except ImportError:
            pass

        # Failed to import the step instance, this is most likely because this
        # code is running on the server as part of a template execution.
        # We now try to fetch the docstring/source code from a step run of the
        # deployment that was used to create the template
        return self._try_to_get_docstring_and_source_code_from_template(
            invocation_id=invocation_id
        )

    @staticmethod
    def _get_docstring_and_source_code_from_step_instance(
        step: "Step",
    ) -> Tuple[Optional[str], str]:
        """Get the docstring and source code of a step.

        Args:
            step: The step configuration.

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

    def _try_to_get_docstring_and_source_code_from_template(
        self, invocation_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Try to get the docstring and source code via a potential template.

        Args:
            invocation_id: The step invocation ID for which to get the
                docstring and source code.

        Returns:
            The docstring and source code of the step.
        """
        if template_id := self.pipeline_run.template_id:
            template = Client().get_run_template(template_id)
            if (
                deployment_id := template.source_deployment.id
                if template.source_deployment
                else None
            ):
                steps = Client().list_run_steps(
                    deployment_id=deployment_id,
                    name=invocation_id,
                    size=1,
                    hydrate=True,
                )

                if len(steps) > 0:
                    step = steps[0]
                    return step.docstring, step.source_code

        return None, None


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
    # This is used to cache the step runs that we created to avoid unnecessary
    # server requests.
    step_runs: Dict[str, "StepRunResponse"] = {}

    while (
        cache_candidates := find_cacheable_invocation_candidates(
            deployment=deployment,
            finished_invocations=cached_invocations,
        )
        # We've already checked these invocations and were not able to cache
        # them -> no need to check them again
        - visited_invocations
    ):
        for invocation_id in cache_candidates:
            visited_invocations.add(invocation_id)

            try:
                step_run_request = request_factory.create_request(
                    invocation_id
                )
                request_factory.populate_request(
                    step_run_request, step_runs=step_runs
                )
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

            # Include the newly created step run in the step runs dictionary to
            # avoid fetching it again later when downstream steps need it for
            # input resolution.
            step_runs[invocation_id] = step_run

            if (
                model_version := step_run.model_version
                or pipeline_run.model_version
            ):
                link_output_artifacts_to_model_version(
                    artifacts=step_run.outputs,
                    model_version=model_version,
                )

            cascade_tags_for_output_artifacts(
                artifacts=step_run.outputs,
                tags=pipeline_run.config.tags,
            )

            logger.info("Using cached version of step `%s`.", invocation_id)
            cached_invocations.add(invocation_id)

    return cached_invocations


def log_model_version_dashboard_url(
    model_version: ModelVersionResponse,
) -> None:
    """Log the dashboard URL for a model version.

    If the current server is not a ZenML Pro workspace, a fallback message is
    logged instead.

    Args:
        model_version: The model version for which to log the dashboard URL.
    """
    from zenml.utils.dashboard_utils import get_model_version_url

    if model_version_url := get_model_version_url(model_version):
        logger.info(
            "Dashboard URL for Model Version `%s (%s)`:\n%s",
            model_version.model.name,
            model_version.name,
            model_version_url,
        )
    else:
        logger.info(
            "Models can be viewed in the dashboard using ZenML Pro. Sign up "
            "for a free trial at https://www.zenml.io/pro/"
        )


def link_output_artifacts_to_model_version(
    artifacts: Dict[str, List[ArtifactVersionResponse]],
    model_version: ModelVersionResponse,
) -> None:
    """Link the outputs of a step run to a model version.

    Args:
        artifacts: The step output artifacts.
        model_version: The model version to link.
    """
    for output_artifacts in artifacts.values():
        for output_artifact in output_artifacts:
            link_artifact_version_to_model_version(
                artifact_version=output_artifact,
                model_version=model_version,
            )


def cascade_tags_for_output_artifacts(
    artifacts: Dict[str, List[ArtifactVersionResponse]],
    tags: Optional[List[Union[str, Tag]]] = None,
) -> None:
    """Tag the outputs of a step run.

    Args:
        artifacts: The step output artifacts.
        tags: The tags to add to the artifacts.
    """
    if tags is None:
        return

    cascade_tags = [t for t in tags if isinstance(t, Tag) and t.cascade]

    for output_artifacts in artifacts.values():
        for output_artifact in output_artifacts:
            add_tags(
                tags=[t.name for t in cascade_tags],
                artifact_version_id=output_artifact.id,
            )
