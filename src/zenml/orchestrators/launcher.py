# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module defines a generic Launcher for all ZenML steps."""

import hashlib
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple, Type
from uuid import UUID

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import ExecutionStatus
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models.pipeline_models import (
    ArtifactModel,
    PipelineRunModel,
    StepRunModel,
)
from zenml.steps.utils import StepExecutor
from zenml.utils import source_utils, string_utils

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.pipeline_configurations import PipelineConfiguration
    from zenml.stack import Stack
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


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
    step_run: "StepRunModel",
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
        step_run.entrypoint_name,
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
        # TODO: make sure this is the correct artifact class
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
    step_run: "StepRunModel", stack: "Stack", step: "Step"
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


class Launcher:
    """This class is responsible for launching a step of a ZenML pipeline.

    It does the following:
    1. Query ZenML to resolve the input artifacts of the step,
    2. Generate a cache key based on the step name, parameters, and
        input artifacts and check if the step can be cached,
    3. Register the step run with ZenML,
    4. If not cached, call the `StepExecutor` to execute the step,
    5. If execution was successful, register the output artifacts with ZenML,
    6. Update the step run status,
    7. Update the pipeline run status.
    """

    def __init__(
        self,
        step: Step,
        step_name: str,
        run_name: str,
        pipeline_config: "PipelineConfiguration",
        stack: "Stack",
    ):
        """Initializes the launcher.

        Args:
            step: The step to launch.
            step_name: The name of the step.
            run_name: The name of the pipeline run.
            pipeline_config: The pipeline configuration.
            stack: The stack on which the pipeline is running.
        """
        self._step = step
        self._step_name = step_name
        self._run_name = run_name
        self._pipeline_config = pipeline_config
        self._stack = stack

    def launch(self) -> None:
        """Launches the step."""
        # TODO: Create run here instead

        logger.info(f"Step `{self._step_name}` has started.")

        run = Client().zen_store.get_run(self._run_name)

        # 1. Get input artifacts IDs of current run
        input_artifact_ids, parent_step_ids = self._resolve_inputs(
            run_id=run.id
        )

        # 2. Generate cache key for current step
        cache_key = generate_cache_key(
            step=self._step,
            artifact_store=self._stack.artifact_store,
            input_artifact_ids=input_artifact_ids,
        )

        # 3. Register step run
        parameters = {
            key: str(value)
            for key, value in self._step.config.parameters.items()
        }
        current_step_run = StepRunModel(
            name=self._step_name,
            pipeline_run_id=run.id,
            parent_step_ids=parent_step_ids,
            input_artifacts=input_artifact_ids,
            status=ExecutionStatus.RUNNING,
            entrypoint_name=self._step.config.name,
            parameters=parameters,
            step_configuration=self._step.dict(),
            mlmd_parent_step_ids=[],
            cache_key=cache_key,
            output_artifacts={},
            caching_parameters=self._step.config.caching_parameters,
            start_time=datetime.now(),
            enable_cache=self._step.config.enable_cache,
        )

        cache_enabled = (
            self._pipeline_config.enable_cache
            and self._step.config.enable_cache
        )
        cache_used = False
        if cache_enabled:
            # 4. query zen store for all step runs with same cache key
            cache_candidates = Client().zen_store.list_run_steps(
                project_id=Client().active_project.id,
                cache_key=cache_key,
                status=ExecutionStatus.COMPLETED,
            )

            if cache_candidates:
                # if exists, use latest run and do the following:
                #   - Set status to cached
                #   - Update with output artifacts of the existing step run
                cache_candidates.sort(key=lambda s: s.created)
                cached_step_run = cache_candidates[-1]
                current_step_run.output_artifacts = (
                    cached_step_run.output_artifacts
                )
                current_step_run.status = ExecutionStatus.CACHED
                current_step_run.end_time = current_step_run.start_time
                Client().zen_store.create_run_step(current_step_run)

                logger.info(f"Using cached version of `{self._step_name}`.")
                cache_used = True

        if not cache_used:
            # if no step run exists:
            #   - Run code
            #   - Register the new output artifacts
            Client().zen_store.create_run_step(current_step_run)

            input_artifacts = prepare_input_artifacts(
                input_artifact_ids=input_artifact_ids
            )
            output_artifacts = prepare_output_artifacts(
                step_run=current_step_run, stack=self._stack, step=self._step
            )

            step_run_info = StepRunInfo(
                config=self._step.config,
                pipeline=self._pipeline_config,
                run_name=run.name,
            )

            start_time = time.time()

            if self._step.config.step_operator:
                from zenml.step_operators.step_operator_entrypoint_configuration import (
                    StepOperatorEntrypointConfiguration,
                )

                step_operator = get_step_operator(
                    stack=self._stack,
                    step_operator_name=self._step.config.step_operator,
                )

                entrypoint_command = StepOperatorEntrypointConfiguration.get_entrypoint_command() + StepOperatorEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=self._step_name,
                    pipeline_run_id=str(run.id),
                    step_run_id=str(current_step_run.id),
                )

                logger.info(
                    "Using step operator `%s` to run step `%s`.",
                    step_operator.name,
                    self._step_name,
                )
                try:
                    step_operator.launch(
                        info=step_run_info,
                        entrypoint_command=entrypoint_command,
                    )
                except:
                    self._cleanup_failed_run(
                        pipeline_run=run,
                        step_run=current_step_run,
                        artifacts=list(output_artifacts.values()),
                    )
                    raise
            else:
                executor = StepExecutor(step=self._step)
                self._stack.prepare_step_run(info=step_run_info)
                try:
                    executor.execute(
                        input_artifacts=input_artifacts,
                        output_artifacts=output_artifacts,
                        run_name=self._run_name,
                        pipeline_config=self._pipeline_config,
                    )
                except:
                    self._cleanup_failed_run(
                        pipeline_run=run,
                        step_run=current_step_run,
                        artifacts=list(output_artifacts.values()),
                    )
                    raise
                finally:
                    self._stack.cleanup_step_run(info=step_run_info)

            duration = time.time() - start_time
            logger.info(
                f"Step `{self._step_name}` has finished in "
                f"{string_utils.get_human_readable_time(duration)}."
            )

            output_artifact_ids = {}
            for name, artifact_ in output_artifacts.items():
                artifact_model = ArtifactModel(
                    name=name,
                    type=artifact_.TYPE_NAME,
                    uri=artifact_.uri,
                    materializer=artifact_.materializer,
                    data_type=artifact_.data_type,
                )
                Client().zen_store.create_artifact(artifact_model)
                output_artifact_ids[name] = artifact_model.id

            current_step_run.output_artifacts = output_artifact_ids
            current_step_run.status = ExecutionStatus.COMPLETED
            current_step_run.end_time = datetime.now()
            Client().zen_store.update_run_step(current_step_run)

        # TODO: do we need to update the run status here, or does that happen
        # on the SQL zen store automatically?
        steps_in_current_run = Client().zen_store.list_run_steps(run_id=run.id)
        status = ExecutionStatus.run_status(
            step_statuses=[step_run.status for step_run in steps_in_current_run]
        )
        if status != run.status:
            run.status = status
            Client().zen_store.update_run(run)

    def _resolve_inputs(
        self, run_id: UUID
    ) -> Tuple[Dict[str, UUID], List[UUID]]:
        """Resolves inputs for the current step.

        Args:
            run_id: The ID of the current pipeline run.

        Raises:
            RuntimeError: If input resolving failed due to a missing step or
                output.

        Returns:
            The IDs of the input artifacts and the IDs of parent steps of the
            current step.
        """
        current_run_steps = {
            run_step.entrypoint_name: run_step
            for run_step in Client().zen_store.list_run_steps(run_id=run_id)
        }

        input_artifact_ids: Dict[str, UUID] = {}
        for name, input_ in self._step.spec.inputs.items():
            try:
                step_run = current_run_steps[input_.step_name]
            except KeyError:
                raise RuntimeError(
                    f"No step `{input_.step_name}` found in current run."
                )

            try:
                artifact_id = step_run.output_artifacts[input_.output_name]
            except KeyError:
                raise RuntimeError(
                    f"No output `{input_.output_name}` found for step "
                    f"`{input_.step_name}`."
                )

            input_artifact_ids[name] = artifact_id

        parent_step_ids = [
            current_run_steps[upstream_step].id
            for upstream_step in self._step.spec.upstream_steps
        ]

        return input_artifact_ids, parent_step_ids

    def _cleanup_failed_run(
        self,
        pipeline_run: PipelineRunModel,
        step_run: StepRunModel,
        artifacts: Sequence[BaseArtifact],
    ) -> None:
        logger.error(f"Failed to execute step `{self._step_name}`.")
        step_run.status = ExecutionStatus.FAILED
        Client().zen_store.update_run_step(step_run)
        pipeline_run.status = ExecutionStatus.FAILED
        Client().zen_store.update_run(pipeline_run)

        remove_artifact_dirs(artifacts=artifacts)

        logger.debug("Finished failed step execution cleanup.")
