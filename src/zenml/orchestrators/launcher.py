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
"""This module defines a generic Launcher for all ZenML steps."""

import hashlib
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple, Type
from uuid import UUID

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import ExecutionStatus
from zenml.exceptions import InputResolutionError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models.pipeline_run_models import (
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
)
from zenml.models.step_run_models import (
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
)
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.executor import StepExecutor
from zenml.stack import Stack
from zenml.utils import source_utils, string_utils

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


def get_step_name_in_pipeline(
    step: "Step", deployment: "PipelineDeployment"
) -> str:
    """Gets the step name of a step inside a pipeline.

    Args:
        step: The step for which to get the name.
        deployment: The pipeline deployment that contains the step.

    Returns:
        The name of the step inside the pipeline.
    """
    step_name_mapping = {
        step_.config.name: key for key, step_ in deployment.steps.items()
    }
    return step_name_mapping[step.config.name]


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


def generate_cache_key(
    step: Step,
    artifact_store: "BaseArtifactStore",
    input_artifact_ids: Dict[str, UUID],
) -> str:
    """Generates a cache key for a step run.

    The cache key is a MD5 hash of the step name, the step parameters, and the
    input artifacts.

    If the cache key is the same for two step runs, we conclude that the step
    runs are identical and can be cached.

    Args:
        step: The step to generate the cache key for.
        artifact_store: The artifact store to use.
        input_artifact_ids: The input artifact IDs for the step.

    Returns:
        A cache key.
    """
    hash_ = hashlib.md5()

    hash_.update(step.spec.source.encode())
    # TODO: should this include the pipeline name? It does in tfx
    # TODO: maybe this should be the ID instead? Or completely removed?
    hash_.update(artifact_store.path.encode())

    for name, artifact_id in input_artifact_ids.items():
        hash_.update(name.encode())
        hash_.update(artifact_id.bytes)

    for name, output in step.config.outputs.items():
        hash_.update(name.encode())
        hash_.update(output.artifact_source.encode())
        hash_.update(output.materializer_source.encode())

    for key, value in sorted(step.config.parameters.items()):
        hash_.update(key.encode())
        hash_.update(str(value).encode())

    for key, value in sorted(step.config.caching_parameters.items()):
        hash_.update(key.encode())
        hash_.update(str(value).encode())

    return hash_.hexdigest()


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


def remove_artifact_dirs(artifacts: Sequence[BaseArtifact]) -> None:
    """Removes the artifact directories.

    Args:
        artifacts: Artifacts for which to remove the directories.
    """
    for artifact in artifacts:
        if fileio.isdir(artifact.uri):
            fileio.rmtree(artifact.uri)


def get_step_operator(
    stack: "Stack", step_operator_name: str
) -> "BaseStepOperator":
    """Fetches the step operator from the stack.

    Args:
        stack: Stack on which the step is being executed.
        step_operator_name: Name of the step operator to get.

    Returns:
        The step operator to run a step.

    Raises:
        RuntimeError: If no active step operator is found.
    """
    step_operator = stack.step_operator

    # the two following errors should never happen as the stack gets
    # validated before running the pipeline
    if not step_operator:
        raise RuntimeError(
            f"No step operator specified for active stack '{stack.name}'."
        )

    if step_operator_name != step_operator.name:
        raise RuntimeError(
            f"No step operator named '{step_operator_name}' in active "
            f"stack '{stack.name}'."
        )

    return step_operator


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


def get_cached_step_run(cache_key: str) -> Optional[StepRunResponseModel]:
    """If a given step can be cached, get the corresponding existing step run.

    A step run can be cached if there is an existing step run in the same
    project which has the same cache key and was successfully executed.

    Args:
        cache_key: The cache key of the step.

    Returns:
        The existing step run if the step can be cached, otherwise None.
    """
    cache_candidates = Client().zen_store.list_run_steps(
        project_id=Client().active_project.id,
        cache_key=cache_key,
        status=ExecutionStatus.COMPLETED,
    )
    if cache_candidates:
        cache_candidates.sort(key=lambda s: s.created)
        return cache_candidates[-1]
    return None


def get_pipeline_run_status(
    step_statuses: List[ExecutionStatus], num_steps: int
) -> ExecutionStatus:
    """Gets the pipeline run status for the given step statuses.

    Args:
        step_statuses: The status of steps in this run.
        num_steps: The total amount of steps in this run.

    Returns:
        The run status.
    """
    if ExecutionStatus.FAILED in step_statuses:
        return ExecutionStatus.FAILED
    if ExecutionStatus.RUNNING in step_statuses:
        return ExecutionStatus.RUNNING
    if len(step_statuses) < num_steps:
        return ExecutionStatus.RUNNING

    return ExecutionStatus.COMPLETED


def update_pipeline_run_status(pipeline_run: PipelineRunResponseModel) -> None:
    """Updates the status of the current pipeline run.

    Args:
        pipeline_run: The model of the current pipeline run.
    """
    assert pipeline_run.num_steps is not None
    steps_in_current_run = Client().zen_store.list_run_steps(
        run_id=pipeline_run.id
    )
    run_status = get_pipeline_run_status(
        step_statuses=[step_run.status for step_run in steps_in_current_run],
        num_steps=pipeline_run.num_steps,
    )

    if run_status != pipeline_run.status:
        if run_status in {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}:
            run_update = PipelineRunUpdateModel(
                status=run_status, end_time=datetime.now()
            )
        else:
            run_update = PipelineRunUpdateModel(status=run_status)

        Client().zen_store.update_run(
            run_id=pipeline_run.id, run_update=run_update
        )


class Launcher:
    """This class is responsible for launching a step of a ZenML pipeline.

    It does the following:
    1. Query ZenML to resolve the input artifacts of the step,
    2. Generate a cache key based on the step and its artifacts,
    3. Build a `StepRunModel` for the step run,
    4. Check if the step run can be cached, and if so, register it as cached.
    5. If not cached, call the `StepExecutor` to execute the step, and register
        the step as running.
    6. If execution was successful, register the output artifacts with ZenML,
    7. If not cached, update the step run status,
    8. Update the pipeline run status.
    """

    def __init__(
        self,
        deployment: "PipelineDeployment",
        step: Step,
        orchestrator_run_id: str,
    ):
        """Initializes the launcher.

        Args:
            deployment: The pipeline deployment.
            step: The step to launch.
            orchestrator_run_id: The orchestrator pipeline run id.
        """
        self._deployment = deployment
        self._step = step
        self._orchestrator_run_id = orchestrator_run_id
        stack_model = Client().get_stack(deployment.stack_id)
        self._stack = Stack.from_model(stack_model)
        self._step_name = get_step_name_in_pipeline(
            step=step, deployment=deployment
        )

    def launch(self) -> None:
        """Launches the step."""
        logger.info(f"Step `{self._step_name}` has started.")

        pipeline_run = self._create_or_reuse_run()

        step_run = StepRunRequestModel(
            name=self._step_name,
            pipeline_run_id=pipeline_run.id,
            step=self._step,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
        )
        try:
            try:
                execution_needed, step_run_response = self._prepare(
                    step_run=step_run
                )
            except:  # noqa: E722
                step_run.status = ExecutionStatus.FAILED
                step_run.end_time = datetime.now()
                Client().zen_store.create_run_step(step_run)
                raise

            if execution_needed:
                self._run_step(
                    pipeline_run=pipeline_run,
                    step_run=step_run_response,
                )

            # 8. Update the pipeline run status
            update_pipeline_run_status(pipeline_run=pipeline_run)
        except:  # noqa: E722
            Client().zen_store.update_run(
                run_id=pipeline_run.id,
                run_update=PipelineRunUpdateModel(
                    status=ExecutionStatus.FAILED,
                    end_time=datetime.now(),
                ),
            )
            raise

    def _create_or_reuse_run(self) -> PipelineRunResponseModel:
        """Creates a run or reuses an existing one.

        Returns:
            The created or existing run.
        """
        run_id = orchestrator_utils.get_run_id_for_orchestrator_run_id(
            orchestrator=self._stack.orchestrator,
            orchestrator_run_id=self._orchestrator_run_id,
        )

        date = datetime.now().strftime("%Y_%m_%d")
        time = datetime.now().strftime("%H_%M_%S_%f")
        run_name = self._deployment.run_name.format(date=date, time=time)

        logger.debug(
            "Creating pipeline run with ID: %s, name: %s", run_id, run_name
        )

        client = Client()
        pipeline_run = PipelineRunRequestModel(
            id=run_id,
            name=run_name,
            orchestrator_run_id=self._orchestrator_run_id,
            user=client.active_user.id,
            project=client.active_project.id,
            stack=self._deployment.stack_id,
            pipeline=self._deployment.pipeline_id,
            enable_cache=self._deployment.pipeline.enable_cache,
            status=ExecutionStatus.RUNNING,
            pipeline_configuration=self._deployment.pipeline.dict(),
            num_steps=len(self._deployment.steps),
        )

        return client.zen_store.get_or_create_run(pipeline_run)

    def _prepare(
        self, step_run: StepRunRequestModel
    ) -> Tuple[bool, StepRunResponseModel]:
        """Prepares running the step.

        Args:
            step_run: The step to run.

        Returns:
            Tuple that specifies whether the step needs to be executed as
            well as the response model of the registered step run.
        """
        input_artifact_ids, parent_step_ids = resolve_step_inputs(
            step=self._step, run_id=step_run.pipeline_run_id
        )

        cache_key = generate_cache_key(
            step=self._step,
            artifact_store=self._stack.artifact_store,
            input_artifact_ids=input_artifact_ids,
        )

        step_run.input_artifacts = input_artifact_ids
        step_run.parent_step_ids = parent_step_ids
        step_run.cache_key = cache_key

        cache_enabled = (
            self._deployment.pipeline.enable_cache
            and self._step.config.enable_cache
        )

        execution_needed = True
        if cache_enabled:
            cached_step_run = get_cached_step_run(cache_key=cache_key)
            if cached_step_run:
                logger.info(f"Using cached version of `{self._step_name}`.")
                execution_needed = False
                step_run.output_artifacts = cached_step_run.output_artifacts
                step_run.status = ExecutionStatus.CACHED
                step_run.end_time = step_run.start_time

        step_run_response = Client().zen_store.create_run_step(step_run)

        return execution_needed, step_run_response

    def _run_step(
        self,
        pipeline_run: PipelineRunResponseModel,
        step_run: StepRunResponseModel,
    ) -> None:
        """Runs the current step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
        """
        # Prepare step run information.
        step_run_info = StepRunInfo(
            config=self._step.config,
            pipeline=self._deployment.pipeline,
            run_name=pipeline_run.name,
            run_id=pipeline_run.id,
            step_run_id=step_run.id,
        )
        input_artifacts = prepare_input_artifacts(
            input_artifact_ids=step_run.input_artifacts,
        )
        output_artifacts = prepare_output_artifacts(
            step_run=step_run, stack=self._stack, step=self._step
        )

        # Run the step.
        start_time = time.time()
        try:
            if self._step.config.step_operator:
                self._run_step_with_step_operator(
                    step_operator_name=self._step.config.step_operator,
                    step_run=step_run,
                    step_run_info=step_run_info,
                )
            else:

                self._run_step_without_step_operator(
                    step_run=step_run,
                    input_artifacts=input_artifacts,
                    output_artifacts=output_artifacts,
                    step_run_info=step_run_info,
                )
        except:  # noqa: E722
            self._cleanup_failed_run(
                step_run=step_run,
                artifacts=list(output_artifacts.values()),
            )
            raise

        duration = time.time() - start_time
        logger.info(
            f"Step `{self._step_name}` has finished in "
            f"{string_utils.get_human_readable_time(duration)}."
        )

    def _run_step_with_step_operator(
        self,
        step_operator_name: str,
        step_run: StepRunResponseModel,
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the current step with a step operator.

        Args:
            step_operator_name: The name of the step operator to use.
            step_run: The model of the current step run.
            step_run_info: Additional information needed to run the step.
        """
        from zenml.step_operators.step_operator_entrypoint_configuration import (
            StepOperatorEntrypointConfiguration,
        )

        step_operator = get_step_operator(
            stack=self._stack,
            step_operator_name=step_operator_name,
        )
        entrypoint_command = (
            StepOperatorEntrypointConfiguration.get_entrypoint_command()
            + StepOperatorEntrypointConfiguration.get_entrypoint_arguments(
                step_name=self._step_name,
                step_run_id=str(step_run.id),
            )
        )
        logger.info(
            "Using step operator `%s` to run step `%s`.",
            step_operator.name,
            self._step_name,
        )
        step_operator.launch(
            info=step_run_info,
            entrypoint_command=entrypoint_command,
        )

    def _run_step_without_step_operator(
        self,
        step_run: StepRunResponseModel,
        input_artifacts: Dict[str, BaseArtifact],
        output_artifacts: Dict[str, BaseArtifact],
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the current step without a step operator.

        Args:
            step_run: The model of the current step run.
            input_artifacts: The input artifacts of the current step.
            output_artifacts: The output artifacts of the current step.
            step_run_info: Additional information needed to run the step.
        """
        executor = StepExecutor(step=self._step, stack=self._stack)
        executor.execute(
            input_artifacts=input_artifacts,
            output_artifacts=output_artifacts,
            step_run_info=step_run_info,
        )

    def _cleanup_failed_run(
        self,
        step_run: StepRunResponseModel,
        artifacts: Sequence[BaseArtifact],
    ) -> None:
        """Clean up a failed step run.

        - Set both the step and pipeline run status to failed
        - Delete all output artifacts

        Args:
            step_run: The step run.
            artifacts: The output artifacts of the step.
        """
        logger.error(f"Failed to execute step `{self._step_name}`.")
        Client().zen_store.update_run_step(
            step_run_id=step_run.id,
            step_run_update=StepRunUpdateModel(
                status=ExecutionStatus.FAILED,
                end_time=datetime.now(),
            ),
        )
        remove_artifact_dirs(artifacts=artifacts)
        logger.debug("Finished failed step execution cleanup.")
