#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the ZenML local threaded orchestrator."""

import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Type
from uuid import uuid4

from pydantic import Field

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
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
    )

logger = get_logger(__name__)


class LocalThreadedOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally with parallel execution.

    This orchestrator allows for concurrent execution of independent steps using
    threads. Steps are executed in parallel when they have no dependencies on each
    other, respecting the DAG structure. Does not support running on a schedule.
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

        This method submits the pipeline and executes steps in parallel when
        they have no dependencies on each other.

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
        if snapshot.schedule:
            logger.warning(
                "Local Threaded Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        self._orchestrator_run_id = str(uuid4())
        start_time = time.time()

        execution_mode = snapshot.pipeline_configuration.execution_mode

        # Thread-safe sets and dicts for tracking step status
        lock = threading.Lock()
        completed_steps: Set[str] = set()
        failed_steps: Set[str] = set()
        skipped_steps: Set[str] = set()
        step_exception: Optional[Exception] = None
        futures: Dict[str, Future] = {}

        self.run_init_hook(snapshot=snapshot)

        # Get max workers from config
        max_workers = self.config.max_workers
        logger.info(
            "Starting local threaded orchestrator with %d worker threads",
            max_workers,
        )

        def get_ready_steps() -> List[str]:
            """Get steps that are ready to run (all dependencies completed)."""
            ready = []
            for step_name, step in snapshot.step_configurations.items():
                # Skip if already processed
                if (
                    step_name in completed_steps
                    or step_name in failed_steps
                    or step_name in skipped_steps
                    or step_name in futures
                ):
                    continue

                # Check if we should skip due to execution mode
                if (
                    execution_mode == ExecutionMode.STOP_ON_FAILURE
                    and failed_steps
                ):
                    with lock:
                        skipped_steps.add(step_name)
                    logger.warning(
                        "Skipping step %s due to the failed step(s): %s (Execution mode %s)",
                        step_name,
                        ", ".join(failed_steps),
                        execution_mode,
                    )
                    continue

                # Check for failed upstream steps
                failed_upstream = [
                    fs for fs in failed_steps if fs in step.spec.upstream_steps
                ]
                if failed_upstream:
                    with lock:
                        skipped_steps.add(step_name)
                    logger.warning(
                        "Skipping step %s due to failure in upstream step(s): %s (Execution mode %s)",
                        step_name,
                        ", ".join(failed_upstream),
                        execution_mode,
                    )
                    continue

                # Check for skipped upstream steps
                skipped_upstream = [
                    ss
                    for ss in skipped_steps
                    if ss in step.spec.upstream_steps
                ]
                if skipped_upstream:
                    with lock:
                        skipped_steps.add(step_name)
                    logger.warning(
                        "Skipping step %s due to the skipped upstream step(s) %s (Execution mode %s)",
                        step_name,
                        ", ".join(skipped_upstream),
                        execution_mode,
                    )
                    continue

                # Check if all upstream steps are completed
                all_upstream_completed = all(
                    upstream in completed_steps
                    for upstream in step.spec.upstream_steps
                )

                if all_upstream_completed:
                    ready.append(step_name)

            return ready

        def run_step_wrapper(step_name: str) -> None:
            """Wrapper to run a step and handle exceptions."""
            nonlocal step_exception

            step = snapshot.step_configurations[step_name]

            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "threaded orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step_name,
                )

            step_environment = step_environments[step_name]
            try:
                logger.info("Running step `%s`", step_name)
                with temporary_environment(step_environment):
                    self.run_step(step=step)
                with lock:
                    completed_steps.add(step_name)
                logger.info("Step `%s` completed successfully", step_name)
            except Exception as e:
                with lock:
                    failed_steps.add(step_name)
                logger.exception("Step %s failed.", step_name)

                if execution_mode == ExecutionMode.FAIL_FAST:
                    with lock:
                        if step_exception is None:
                            step_exception = e

        # Execute steps using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                # Get steps that are ready to run
                ready_steps = get_ready_steps()

                # Submit ready steps to the executor
                for step_name in ready_steps:
                    logger.info(
                        "Submitting step `%s` for execution", step_name
                    )
                    future = executor.submit(run_step_wrapper, step_name)
                    futures[step_name] = future

                # Check if any futures are done and remove them
                done_futures = []
                for step_name, future in list(futures.items()):
                    if future.done():
                        done_futures.append(step_name)

                for step_name in done_futures:
                    del futures[step_name]

                # Check if we're done (all steps processed)
                total_processed = (
                    len(completed_steps)
                    + len(failed_steps)
                    + len(skipped_steps)
                )
                total_steps = len(snapshot.step_configurations)

                if total_processed >= total_steps:
                    break

                # If no active futures and no ready steps, but not all steps processed,
                # something is wrong (shouldn't happen with correct DAG)
                if (
                    not futures
                    and not ready_steps
                    and total_processed < total_steps
                ):
                    remaining_steps = (
                        set(snapshot.step_configurations.keys())
                        - completed_steps
                        - failed_steps
                        - skipped_steps
                    )
                    raise RuntimeError(
                        f"Pipeline execution stalled. Remaining steps cannot be executed: {remaining_steps}"
                    )

                # Short sleep to avoid busy waiting
                if futures:
                    time.sleep(0.1)

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


class LocalThreadedOrchestratorConfig(BaseOrchestratorConfig):
    """Local threaded orchestrator config.

    Attributes:
        max_workers: Maximum number of worker threads to use for parallel
            step execution. Defaults to the number of CPU cores available,
            or 4 if that cannot be determined.
    """

    max_workers: int = Field(
        default_factory=lambda: os.cpu_count() or 4,
        description="Maximum number of worker threads for parallel step execution. "
        "Controls how many independent steps can run concurrently. "
        "Examples: 2 for minimal parallelism, 4 for moderate parallelism, "
        "8 or more for high parallelism on multi-core systems. "
        "Defaults to the number of CPU cores available",
    )

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


class LocalThreadedOrchestratorFlavor(BaseOrchestratorFlavor):
    """Class for the `LocalThreadedOrchestratorFlavor`."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """
        return "local_threaded"

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
        return LocalThreadedOrchestratorConfig

    @property
    def implementation_class(self) -> Type[LocalThreadedOrchestrator]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return LocalThreadedOrchestrator
