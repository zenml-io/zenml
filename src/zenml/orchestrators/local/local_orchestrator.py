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
"""Implementation of the ZenML local orchestrator."""

import time
from typing import TYPE_CHECKING, Dict, List, Optional, Type
from uuid import uuid4

from zenml.enums import ExecutionMode
from zenml.logger import get_logger
from zenml.orchestrators import (
    BaseOrchestrator,
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
    SubmissionResult,
)
from zenml.stack import Stack
from zenml.utils import string_utils
from zenml.utils.env_utils import temporary_environment

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse

logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally.

    This orchestrator does not allow for concurrent execution of steps and also
    does not support running on a schedule.
    """

    _orchestrator_run_id: Optional[str] = None

    @property
    def run_init_cleanup_at_step_level(self) -> bool:
        """Whether the orchestrator runs the init and cleanup hooks at step level.

        For orchestrators that run their steps in isolated step environments,
        the run context cannot be shared between steps. In this case, the init
        and cleanup hooks need to be run at step level for each individual step.

        For orchestrators that run their steps in a shared environment with a
        shared memory (e.g. the local orchestrator), the init and cleanup hooks
        can be run at run level and this property should be overridden to return
        True.

        Returns:
            Whether the orchestrator runs the init and cleanup hooks at step
            level.
        """
        return False

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to the orchestrator.

        This method should only submit the pipeline and not wait for it to
        complete. If the orchestrator is configured to wait for the pipeline run
        to complete, a function that waits for the pipeline run to complete can
        be passed as part of the submission result.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment shared by all steps. This should
                be set if your orchestrator for example runs one container that
                is responsible for starting all the steps.
            step_environments: Environment variables to set when executing
                specific steps.
            placeholder_run: An optional placeholder run for the snapshot.

        Returns:
            Optional submission result.

        Raises:
            step_exception: The exception that occurred while running a failed
                step.
            RuntimeError: If the pipeline run fails.
        """
        self._orchestrator_run_id = str(uuid4())
        start_time = time.time()

        execution_mode = snapshot.pipeline_configuration.execution_mode

        failed_steps: List[str] = []
        step_exception: Optional[Exception] = None
        skipped_steps: List[str] = []

        self.run_init_hook(snapshot=snapshot)

        # Run each step
        for step_name, step in snapshot.step_configurations.items():
            if (
                execution_mode == ExecutionMode.STOP_ON_FAILURE
                and failed_steps
            ):
                logger.warning(
                    "Skipping step %s due to the failed step(s): %s (Execution mode %s)",
                    step_name,
                    ", ".join(failed_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if failed_upstream_steps := [
                fs for fs in failed_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to failure in upstream step(s): %s (Execution mode %s)",
                    step_name,
                    ", ".join(failed_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if skipped_upstream_steps := [
                fs for fs in skipped_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to the skipped upstream step(s) %s (Execution mode %s)",
                    step_name,
                    ", ".join(skipped_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step_name,
                )

            step_environment = step_environments[step_name]
            try:
                with temporary_environment(step_environment):
                    self.run_step(step=step)
            except Exception as e:
                failed_steps.append(step_name)
                logger.exception("Step %s failed.", step_name)

                if execution_mode == ExecutionMode.FAIL_FAST:
                    step_exception = e
                    break

        self.run_cleanup_hook(snapshot=snapshot)

        if execution_mode == ExecutionMode.FAIL_FAST and failed_steps:
            assert step_exception is not None
            raise step_exception

        if failed_steps:
            raise RuntimeError(
                "Pipeline run has failed due to failure in step(s): "
                f"{', '.join(failed_steps)}"
            )

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
        self._orchestrator_run_id = None
        return None

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a dynamic pipeline to the orchestrator.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run.

        Returns:
            Optional submission result.
        """
        from zenml.execution.pipeline.dynamic.runner import (
            DynamicPipelineRunner,
        )

        self._orchestrator_run_id = str(uuid4())
        start_time = time.time()

        runner = DynamicPipelineRunner(snapshot=snapshot, run=placeholder_run)
        with temporary_environment(environment):
            runner.run_pipeline()

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
        self._orchestrator_run_id = None
        return None

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If no run id exists. This happens when this method
                gets called while the orchestrator is not running a pipeline.

        Returns:
            The orchestrator run id.
        """
        if not self._orchestrator_run_id:
            raise RuntimeError("No run id set.")

        return self._orchestrator_run_id

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Returns the supported execution modes for this flavor.

        Returns:
            A tuple of supported execution modes.
        """
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]


class LocalOrchestratorConfig(BaseOrchestratorConfig):
    """Local orchestrator config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return True


class LocalOrchestratorFlavor(BaseOrchestratorFlavor):
    """Class for the `LocalOrchestratorFlavor`."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """
        return "local"

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/local.png"

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return LocalOrchestratorConfig

    @property
    def implementation_class(self) -> Type[LocalOrchestrator]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return LocalOrchestrator
