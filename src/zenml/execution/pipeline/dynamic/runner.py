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
"""Dynamic pipeline runner."""

import contextvars
import copy
import inspect
import itertools
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ContextManager,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from uuid import uuid4

from pydantic import TypeAdapter

from zenml import ExternalArtifact
from zenml.artifacts.in_memory_cache import InMemoryArtifactCache
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.step_configurations import (
    GroupInfo,
    Step,
    StepConfiguration,
    StepConfigurationUpdate,
)
from zenml.constants import (
    ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY,
    ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_INTERVAL,
    ENV_ZENML_DYNAMIC_PIPELINE_WORKER_COUNT,
    handle_float_env_var,
    handle_int_env_var,
)
from zenml.enums import (
    ExecutionMode,
    ExecutionStatus,
    GroupType,
    RunWaitConditionLeaseMode,
    RunWaitConditionResolution,
    RunWaitConditionStatus,
    RunWaitConditionType,
    StepRuntime,
)
from zenml.execution.pipeline.dynamic.future_registry import (
    FutureRegistry,
    StartupCancelled,
)
from zenml.execution.pipeline.dynamic.interactive_input_utils import (
    maybe_enable_interactive_wait_prompt,
    poll_interactive_wait_condition_input,
)
from zenml.execution.pipeline.dynamic.invocation_dependency_graph import (
    InvocationDependencyGraph,
    MapNode,
    NodeState,
    StepNode,
)
from zenml.execution.pipeline.dynamic.outputs import (
    AnyStepFuture,
    ArtifactFuture,
    BaseStepFuture,
    MapResultsFuture,
    OutputArtifact,
    StepExecutionFuture,
    StepFuture,
    StepRunOutputs,
    _InlineStepFuture,
    _IsolatedStepFuture,
)
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.execution.pipeline.dynamic.utils import (
    _Unmapped,
    collect_futures,
    load_step_run_outputs,
)
from zenml.execution.pipeline.utils import compute_invocation_id
from zenml.execution.step.utils import launch_step
from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionResponse,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineSnapshotResponse,
    RunWaitConditionLeaseUpdate,
    RunWaitConditionRequest,
    RunWaitConditionResolveRequest,
    RunWaitConditionResponse,
    StepRunResponse,
)
from zenml.orchestrators.publish_utils import (
    publish_cancelled_step_run,
    publish_failed_pipeline_run,
    publish_failed_step_run,
    publish_stopped_step_run,
    publish_successful_pipeline_run,
)
from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.steps.entrypoint_function_utils import StepArtifact
from zenml.steps.step_invocation import StepInvocation
from zenml.steps.utils import OutputSignature
from zenml.utils import (
    env_utils,
    exception_utils,
    pydantic_utils,
    source_utils,
    string_utils,
)
from zenml.utils.logging_utils import (
    is_pipeline_logging_enabled,
    setup_logging_context,
)

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.orchestrators import BaseOrchestrator


logger = get_logger(__name__)

T = TypeVar("T")


class _WaitConditionPollTimeout(Exception):
    """Raised when a wait condition polling times out."""


class _WaitConditionAborted(Exception):
    """Raised when a wait condition is aborted."""


class _WaitConditionState(NamedTuple):
    """State tuple for wait condition handling."""

    is_terminal: bool
    value: Any


class DynamicPipelineRunner:
    """Dynamic pipeline runner."""

    def __init__(
        self,
        snapshot: "PipelineSnapshotResponse",
        run: Optional["PipelineRunResponse"],
        orchestrator: Optional["BaseOrchestrator"] = None,
    ) -> None:
        """Initialize the dynamic pipeline runner.

        Args:
            snapshot: The snapshot of the pipeline.
            run: The pipeline run.
            orchestrator: The orchestrator to use. If not provided, the
                orchestrator will be inferred from the snapshot stack.

        Raises:
            RuntimeError: If the snapshot has no associated stack.
        """
        if not snapshot.stack:
            raise RuntimeError("Missing stack for snapshot.")

        if (
            snapshot.pipeline_configuration.execution_mode
            == ExecutionMode.CONTINUE_ON_FAILURE
        ):
            logger.warning(
                "The `%s` execution mode is not supported for "
                "dynamic pipelines right now. "
                "The `%s` execution mode will be used instead.",
                snapshot.pipeline_configuration.execution_mode,
                ExecutionMode.STOP_ON_FAILURE,
            )

        self._snapshot = snapshot
        self._pipeline: Optional["DynamicPipeline"] = None
        self._fail_fast = (
            snapshot.pipeline_configuration.execution_mode
            == ExecutionMode.FAIL_FAST
        )

        worker_count = handle_int_env_var(
            ENV_ZENML_DYNAMIC_PIPELINE_WORKER_COUNT, default=10
        )
        self._executor = ThreadPoolExecutor(max_workers=worker_count)

        stack = Stack.from_model(snapshot.stack)
        if orchestrator:
            self._orchestrator = orchestrator
        else:
            self._orchestrator = stack.orchestrator

        self._step_operator = stack.step_operator
        self._invocation_id_lock = threading.Lock()
        self._invocation_ids: Set[str] = set()

        self._run, self._orchestrator_run_id = self._prepare_run(run)
        self._existing_step_runs = self._run.steps

        self._steps_to_monitor: Dict[str, "StepRunResponse"] = {}

        self._shutdown_requested = False
        self._failure_detected = False
        self._exception: Optional[BaseException] = None
        self._lifecycle_lock = threading.RLock()
        self._monitoring_event = threading.Event()
        self._startup_event = threading.Event()
        self._dependency_graph = InvocationDependencyGraph()
        self._future_registry = FutureRegistry()

    def _prepare_run(
        self, run: Optional["PipelineRunResponse"]
    ) -> Tuple["PipelineRunResponse", str]:
        """Prepare the pipeline run.

        This method either creates a new run if not provided or potentially
        updates the existing run with the orchestrator run ID.

        Args:
            run: The pipeline run to prepare.

        Returns:
            The prepared pipeline run and the orchestrator run ID.
        """
        if run and run.orchestrator_run_id:
            orchestrator_run_id = run.orchestrator_run_id
        else:
            orchestrator_run_id = self._orchestrator.get_orchestrator_run_id()

        if run and not run.orchestrator_run_id:
            run = Client().zen_store.update_run(
                run_id=run.id,
                run_update=PipelineRunUpdate(
                    orchestrator_run_id=orchestrator_run_id,
                ),
            )
        else:
            existing_runs = Client().list_pipeline_runs(
                snapshot_id=self._snapshot.id,
                orchestrator_run_id=orchestrator_run_id,
            )
            if existing_runs.total == 1:
                run = existing_runs.items[0]
            else:
                run = create_placeholder_run(
                    snapshot=self._snapshot,
                    orchestrator_run_id=orchestrator_run_id,
                )

        return run, orchestrator_run_id

    @property
    def pipeline(self) -> "DynamicPipeline":
        """The pipeline that the runner is executing.

        Raises:
            RuntimeError: If the pipeline can't be loaded.

        Returns:
            The pipeline that the runner is executing.
        """
        if self._pipeline is None:
            if (
                not self._snapshot.pipeline_spec
                or not self._snapshot.pipeline_spec.source
            ):
                raise RuntimeError("Missing pipeline source for snapshot.")

            pipeline = source_utils.load(self._snapshot.pipeline_spec.source)
            if not isinstance(pipeline, DynamicPipeline):
                raise RuntimeError(
                    "Invalid pipeline source: "
                    f"{self._snapshot.pipeline_spec.source.import_path}"
                )
            pipeline = copy.deepcopy(pipeline)
            pipeline._configuration = self._snapshot.pipeline_configuration
            self._pipeline = pipeline

        return self._pipeline

    def _monitoring_loop(self) -> None:
        """Monitoring loop.

        This should run in a separate thread and monitors the running steps.
        """
        from zenml.config.step_configurations import Step

        monitoring_interval = handle_float_env_var(
            ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_INTERVAL, default=10.0
        )
        monitoring_delay = handle_float_env_var(
            ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY, default=0.1
        )

        while not self._shutdown_requested:
            start_time = time.time()

            # Copy the steps to avoid the dictionary getting modified by
            # the main thread while we're iterating over it.
            for invocation_id, step_run in list(
                self._steps_to_monitor.items()
            ):
                infra_status: Optional[ExecutionStatus] = None
                try:
                    infra_status = self._get_isolated_step_infra_status(
                        step_run
                    )
                except Exception as e:
                    logger.error(
                        "Failed to get infra status for step `%s`: %s",
                        invocation_id,
                        e,
                    )
                else:
                    logger.debug(
                        "Step `%s` infra status: %s.",
                        invocation_id,
                        infra_status,
                    )

                if infra_status in [
                    ExecutionStatus.INITIALIZING,
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                ]:
                    # Step still running on the infra side, no need to
                    # do anything here.
                    continue

                step_run = Client().get_run_step(step_run.id)

                db_status = step_run.status

                if infra_status is None and db_status in [
                    ExecutionStatus.INITIALIZING,
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                ]:
                    # Step is running in the DB and we have no information on
                    # the infra side, so we wait for the next
                    # monitoring interval to check again. We store the
                    # refreshed step run to have the most up to date status.
                    self._steps_to_monitor[invocation_id] = step_run
                    continue

                self._steps_to_monitor.pop(invocation_id, None)

                if db_status == ExecutionStatus.STOPPING:
                    # The step runner sets the status to STOPPING when receiving
                    # a heartbeat response that the pipeline should be stopped.
                    # We now update this status to STOPPED.
                    step_run = publish_stopped_step_run(step_run.id)
                elif db_status == ExecutionStatus.CANCELLING:
                    # Resource preemption sets the status to CANCELLING. We now
                    # update the status to CANCELLED.
                    step_run = publish_cancelled_step_run(step_run.id)
                elif (
                    infra_status
                    in [ExecutionStatus.FAILED, ExecutionStatus.STOPPED]
                    and db_status == ExecutionStatus.RUNNING
                ):
                    # Step failed/stopped on the infra side, but the
                    # code failed before it could report the status back to us.
                    step_run = publish_failed_step_run(step_run.id)

                # Get the updated status that we might have just published
                db_status = step_run.status

                duration_string = (
                    string_utils.get_human_readable_time(
                        step_run.duration.total_seconds()
                    )
                    if step_run.duration
                    else None
                )
                if db_status.is_successful:
                    if duration_string:
                        logger.info(
                            "Step `%s` finished successfully in %s.",
                            invocation_id,
                            duration_string,
                        )
                    else:
                        logger.info(
                            "Step `%s` finished successfully.",
                            invocation_id,
                        )
                    self._on_step_finished(step_run=step_run)
                elif db_status.is_failed:
                    if duration_string:
                        logger.error(
                            "Step `%s` failed after %s.",
                            invocation_id,
                            duration_string,
                        )
                    else:
                        logger.error(
                            "Step `%s` failed.",
                            invocation_id,
                        )
                    self._on_step_finished(step_run=step_run)
                elif db_status == ExecutionStatus.STOPPED:
                    if duration_string:
                        logger.info(
                            "Step `%s` stopped after %s.",
                            invocation_id,
                            duration_string,
                        )
                    else:
                        logger.info("Step `%s` stopped.", invocation_id)
                    self._on_step_finished(step_run=step_run)
                elif db_status == ExecutionStatus.RETRYING:
                    # The server set the status of the step run to retrying ->
                    # The server expects the step to be retried.
                    remaining_retries = get_remaining_retries(
                        step_run=step_run
                    )

                    if duration_string:
                        logger.error(
                            "Step `%s` failed after %s. Remaining retries: %d.",
                            invocation_id,
                            duration_string,
                            remaining_retries,
                        )
                    else:
                        logger.error(
                            "Step `%s` failed. Remaining retries: %d.",
                            invocation_id,
                            remaining_retries,
                        )

                    with self._lifecycle_lock:
                        if (
                            remaining_retries > 0
                            and not self._failure_detected
                        ):
                            # If there was a failure already, we do not want to
                            # start any new work no matter the execution mode.
                            step = Step(
                                spec=step_run.spec,
                                config=step_run.config,
                                step_config_overrides=step_run.config,
                            )
                            self._queue_concurrent_isolated_step(step=step)

                time.sleep(monitoring_delay)

            duration = time.time() - start_time
            time_to_sleep = max(0, monitoring_interval - duration)
            self._monitoring_event.wait(timeout=time_to_sleep)
            self._monitoring_event.clear()

    def _start_monitoring_loop(self) -> threading.Thread:
        """Start the monitoring loop.

        Returns:
            The monitoring thread.
        """
        ctx = contextvars.copy_context()
        monitoring_thread = threading.Thread(
            name="DynamicPipelineRunner-Monitoring-Loop",
            target=lambda: ctx.run(self._monitoring_loop),
            daemon=True,
        )
        monitoring_thread.start()
        return monitoring_thread

    def _startup_loop(self) -> None:
        """Startup loop."""
        while not self._failure_detected and not self._shutdown_requested:
            self._startup_event.wait(timeout=None)

            while not self._failure_detected and not self._shutdown_requested:
                node = self._dependency_graph.get_ready_node()
                if node is None:
                    # Clear and immediately re-check to avoid missing work that
                    # becomes ready concurrently with this transition to waiting.
                    self._startup_event.clear()
                    node = self._dependency_graph.get_ready_node()
                    if node is None:
                        break

                node_id = node.node_id
                try:
                    if isinstance(node, StepNode):
                        self._handle_step_ready(node=node)
                    elif isinstance(node, MapNode):
                        self._handle_map_ready(node=node)
                except Exception as e:
                    if isinstance(node, StepNode):
                        self._handle_step_startup_failed(
                            invocation_id=node_id, exception=e
                        )
                        logger.exception(
                            "Failed to start concurrent step `%s`.",
                            node_id,
                        )
                    elif isinstance(node, MapNode):
                        self._handle_map_expansion_failed(
                            map_id=node_id, exception=e
                        )
                        logger.exception(
                            "Failed to start concurrent map `%s`.",
                            node_id,
                        )

                    # ONLY FAIL_FAST and STOP_ON_FAILURE execution modes are
                    # supported for dynamic pipelines. In both cases, we do not
                    # allow starting any new steps after any failure.
                    return

    def _start_startup_loop(self) -> threading.Thread:
        """Start the startup loop.

        Returns:
            The startup thread.
        """
        ctx = contextvars.copy_context()
        startup_thread = threading.Thread(
            name="DynamicPipelineRunner-Startup-Loop",
            target=lambda: ctx.run(self._startup_loop),
            daemon=True,
        )
        startup_thread.start()
        return startup_thread

    def _register_isolated_step_for_monitoring(
        self, invocation_id: str, step_run: "StepRunResponse"
    ) -> None:
        """Register an isolated step for monitoring.

        Args:
            invocation_id: The step invocation ID.
            step_run: The step run response to monitor.
        """
        with self._lifecycle_lock:
            self._steps_to_monitor[invocation_id] = step_run
            should_stop_step = self._failure_detected and self._fail_fast

        if should_stop_step:
            try:
                self._stop_isolated_step(step_run)
            except Exception:
                logger.exception("Failed to stop step `%s`.", invocation_id)

    def _get_isolated_step_infra_status(
        self, step_run: "StepRunResponse"
    ) -> Optional[ExecutionStatus]:
        """Get the status of an isolated step from the component infrastructure.

        Args:
            step_run: The step run to get the status of.

        Returns:
            The status of the step run.
        """
        if step_run.config.step_operator:
            assert self._step_operator
            return self._step_operator.get_status(step_run)
        else:
            return self._orchestrator.get_isolated_step_status(step_run)

    def run_pipeline(self) -> None:
        """Run the pipeline.

        Raises:
            Exception: If the pipeline run failed.
        """
        logs_context: ContextManager[Any] = nullcontext()
        if is_pipeline_logging_enabled(self._snapshot.pipeline_configuration):
            logs_context = setup_logging_context(
                source="orchestrator", pipeline_run=self._run
            )

        with logs_context:
            if self._run.status.is_finished:
                logger.info("Run `%s` is already finished.", str(self._run.id))
                return
            elif self._run.status in {
                ExecutionStatus.RESUMING,
                ExecutionStatus.PAUSED,
                ExecutionStatus.RETRYING,
            }:
                self._run = Client().zen_store.update_run(
                    run_id=self._run.id,
                    run_update=PipelineRunUpdate(
                        status=ExecutionStatus.RUNNING,
                    ),
                )
                logger.info("Resuming run `%s`.", str(self._run.id))
            elif self._run.status == ExecutionStatus.RUNNING:
                logger.info("Continuing existing run `%s`.", str(self._run.id))
            elif self._run.status in {
                ExecutionStatus.INITIALIZING,
                ExecutionStatus.PROVISIONING,
            }:
                # Set the run status to running already, in case no steps start
                # immediately which would otherwise cause the run to be stuck in
                # some init state.
                self._run = Client().zen_store.update_run(
                    run_id=self._run.id,
                    run_update=PipelineRunUpdate(
                        status=ExecutionStatus.RUNNING,
                    ),
                )

            assert self._snapshot.stack

            with (
                InMemoryArtifactCache(),
                env_utils.temporary_runtime_environment(
                    self._snapshot.pipeline_configuration, self._snapshot.stack
                ),
                DynamicPipelineRunContext(
                    pipeline=self.pipeline,
                    run=self._run,
                    snapshot=self._snapshot,
                    runner=self,
                ),
            ):
                monitoring_thread = self._start_monitoring_loop()
                startup_thread = self._start_startup_loop()

                if not self._run.triggered_by_deployment:
                    # Only run the init hook if the run is not triggered by
                    # a deployment, as the deployment service will have
                    # already run the init hook.
                    self._orchestrator.run_init_hook(snapshot=self._snapshot)

                params = self.pipeline.configuration.parameters or {}
                try:
                    self.pipeline._call_entrypoint(**params)
                    # The pipeline function finished successfully, but some
                    # steps might still be running. We now wait for all of
                    # them and raise any exceptions that occurred.
                    self.wait_until_done_or_failure()
                except _WaitConditionPollTimeout:
                    logger.info("Pausing pipeline run `%s`.", self._run.id)
                    return
                except _WaitConditionAborted as abort_exception:
                    logger.info(
                        "Stopping pipeline run `%s` because a wait condition "
                        "was aborted.",
                        self._run.id,
                    )
                    self._abort_and_drain(exception=abort_exception)
                    return
                except Exception as e:
                    logger.debug("Exception in pipeline function: %s", e)
                    self._abort_and_drain(exception=e)
                    exception_info = (
                        exception_utils.collect_exception_information(
                            exception=e,
                            user_func=self.pipeline.entrypoint,
                        )
                    )
                    publish_failed_pipeline_run(
                        self._run.id, exception_info=exception_info
                    )
                    raise
                finally:
                    if not self._run.triggered_by_deployment:
                        # Only run the cleanup hook if the run is not
                        # triggered by a deployment, as the deployment
                        # service will have already run the cleanup hook.
                        self._orchestrator.run_cleanup_hook(
                            snapshot=self._snapshot
                        )

                    self._executor.shutdown(wait=True, cancel_futures=True)

                    self._shutdown_requested = True
                    self._startup_event.set()
                    self._monitoring_event.set()
                    monitoring_thread.join()
                    startup_thread.join()

                self._run = Client().zen_store.get_run(
                    self._run.id, hydrate=False
                )
                if self._run.status == ExecutionStatus.RUNNING:
                    publish_successful_pipeline_run(self._run.id)
                    logger.info("Pipeline completed successfully.")

    def _handle_graph_update(self, new_nodes_ready: bool) -> None:
        """Handle a graph update.

        Args:
            new_nodes_ready: Whether any new nodes are ready.
        """
        if new_nodes_ready:
            self._startup_event.set()

    def _allocate_invocation_id(
        self, step: "BaseStep", custom_id: Optional[str], allow_suffix: bool
    ) -> str:
        """Allocate a new invocation ID.

        Args:
            step: The step to allocate an invocation ID for.
            custom_id: A custom invocation ID to use.
            allow_suffix: Whether to allow suffixing the invocation ID.

        Returns:
            The allocated invocation ID.
        """
        # TODO: maybe prevent `map:` prefixes for invocation IDs
        with self._invocation_id_lock:
            invocation_id = compute_invocation_id(
                existing_invocations=self._invocation_ids,
                step=step,
                custom_id=custom_id,
                allow_suffix=allow_suffix,
            )
            self._invocation_ids.add(invocation_id)

        return invocation_id

    @overload
    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
        group: Optional["GroupInfo"] = None,
        concurrent: Literal[False] = False,
    ) -> StepRunOutputs: ...

    @overload
    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
        group: Optional["GroupInfo"] = None,
        concurrent: Literal[True] = True,
    ) -> "StepFuture": ...

    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
        group: Optional["GroupInfo"] = None,
        concurrent: bool = False,
    ) -> Union[StepRunOutputs, "StepFuture"]:
        """Launch a step.

        Args:
            step: The step to launch.
            id: The invocation ID of the step.
            args: The arguments for the step function.
            kwargs: The keyword arguments for the step function.
            after: The step run output futures to wait for.
            group: The group information for this step.
            concurrent: Whether to launch the step concurrently.

        Raises:
            BaseException: If the step failed.

        Returns:
            The step run outputs or a future for the step run outputs.
        """  # noqa: DOC502, DOC503
        step = step.copy()

        invocation_id = self._allocate_invocation_id(
            step=step, custom_id=id, allow_suffix=not id
        )

        remaining_retries = None
        if step_run := self._existing_step_runs.get(invocation_id):
            runtime = get_step_runtime(
                step_config=step_run.config,
                pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
                orchestrator=self._orchestrator,
            )

            if step_run.status.is_successful:
                # The step finished successfully, but we still need to return
                # a future in case the step was launched concurrently so the
                # caller gets the correct object back.
                if concurrent:
                    execution_future = _IsolatedStepFuture(
                        pipeline_run_id=self._run.id,
                        invocation_id=invocation_id,
                    )
                    future = StepFuture(
                        invocation_id=invocation_id,
                        execution_future=execution_future,
                        output_keys=list(step_run.config.outputs),
                    )
                    self._register_concurrent_step_invocation(
                        future=future,
                        initial_state=NodeState.SUCCEEDED,
                    )
                    self._handle_step_execution_succeeded(
                        invocation_id=invocation_id
                    )
                    return future
                else:
                    return load_step_run_outputs(step_run.id)

            if (
                runtime == StepRuntime.INLINE
                and step_run.status == ExecutionStatus.RUNNING
            ):
                # Inline steps that are in running state didn't have the
                # chance to report their failure back to ZenML before the
                # orchestration environment was shut down. But there is no
                # way that they're actually still running if we're in a new
                # orchestration environment, so we mark them as failed and
                # potentially restart them depending on the retry config.
                step_run = publish_failed_step_run(step_run.id)
                # Store the updated step run so we can compute the remaining
                # retries in the async submission flow.
                self._existing_step_runs[invocation_id] = step_run

            if step_run.status.is_failed:
                exception = self._get_step_exception(step_run=step_run)

                # If the step is running concurrently, we only raise the
                # exception once the future is awaited.
                if concurrent:
                    execution_future = _IsolatedStepFuture(
                        pipeline_run_id=self._run.id,
                        invocation_id=invocation_id,
                    )
                    future = StepFuture(
                        invocation_id=invocation_id,
                        execution_future=execution_future,
                        output_keys=list(step_run.config.outputs),
                    )
                    self._register_concurrent_step_invocation(
                        future=future,
                        initial_state=NodeState.FAILED,
                    )
                    self._handle_step_execution_failed(
                        invocation_id=invocation_id,
                        exception=exception,
                    )
                    return future
                else:
                    raise exception

            remaining_retries = get_remaining_retries(step_run=step_run)

            if step_run.status == ExecutionStatus.RUNNING:
                logger.info(
                    "Restarting the monitoring of existing step `%s` "
                    "(ID: %s). Remaining retries: %d",
                    step_run.name,
                    step_run.id,
                    remaining_retries,
                )
                execution_future = _IsolatedStepFuture(
                    pipeline_run_id=self._run.id,
                    invocation_id=invocation_id,
                )
                monitoring_future = StepFuture(
                    invocation_id=invocation_id,
                    execution_future=execution_future,
                    output_keys=list(step_run.config.outputs),
                )
                self._register_concurrent_step_invocation(
                    future=monitoring_future,
                    initial_state=NodeState.RUNNING,
                )
                self._register_isolated_step_for_monitoring(
                    invocation_id=invocation_id,
                    step_run=step_run,
                )
                self._handle_step_running(invocation_id=invocation_id)
                if concurrent:
                    return monitoring_future
                else:
                    return monitoring_future.result()

        inputs = convert_to_keyword_arguments(step.entrypoint, args, kwargs)

        config_overrides = None
        if self._run and self._run.triggered_by_deployment:
            # Deployment-specific step overrides
            config_overrides = StepConfigurationUpdate(
                enable_cache=False,
                step_operator=None,
                parameters={},
                runtime=StepRuntime.INLINE,
                group=group,
            )
        elif group:
            config_overrides = StepConfigurationUpdate(
                group=group,
            )

        if concurrent:
            future = StepFuture(
                invocation_id=invocation_id,
                output_keys=list(step.entrypoint_definition.outputs),
            )
            self._register_concurrent_step_invocation(
                future=future,
                step=step,
                inputs=inputs,
                after=after,
                config_overrides=config_overrides,
            )
            return future
        else:
            if (
                running_upstream_dependencies
                := _get_running_upstream_dependencies(inputs, after)
            ):
                logger.info(
                    "Waiting for upstream dependencies `%s` to finish before "
                    "executing step `%s`.",
                    ", ".join(running_upstream_dependencies),
                    invocation_id,
                )

            compiled_step = self._compile_or_reuse(
                step=step,
                invocation_id=invocation_id,
                inputs=inputs,
                after=after,
                config=config_overrides,
            )

            step_run = self._run_sync_step(
                step=compiled_step, remaining_retries=remaining_retries
            )
            return load_step_run_outputs(step_run.id)

    def _run_sync_step(
        self,
        step: "Step",
        remaining_retries: Optional[int] = None,
    ) -> StepRunResponse:
        """Run a synchronous step.

        Args:
            step: The step to run.
            remaining_retries: The remaining retries for the step.

        Returns:
            The step run response.
        """
        return launch_step(
            snapshot=self._snapshot,
            step=step,
            orchestrator_run_id=self._orchestrator_run_id,
            wait=True,
            retry=True,
            remaining_retries=remaining_retries,
        )

    def _compile_or_reuse(
        self,
        step: "BaseStep",
        invocation_id: str,
        inputs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
        config: Optional["StepConfigurationUpdate"] = None,
    ) -> "Step":
        """Compile a step invocation or reuse from existing step run.

        Args:
            step: The step to compile.
            invocation_id: The invocation ID of the step.
            inputs: The step inputs.
            after: Optional upstream futures for the step.
            config: Optional config overrides for compilation.

        Returns:
            The compiled step.
        """
        if existing_step_run := self._existing_step_runs.get(invocation_id):
            compiled_step = Step(
                spec=existing_step_run.spec,
                config=existing_step_run.config,
                step_config_overrides=existing_step_run.config,
            )
        else:
            compiled_step = compile_dynamic_step_invocation(
                snapshot=self._snapshot,
                pipeline=self.pipeline,
                step=step,
                invocation_id=invocation_id,
                inputs=inputs,
                pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
                after=after,
                config=config,
            )

        return compiled_step

    def map(
        self,
        step: "BaseStep",
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
        product: bool = False,
    ) -> "MapResultsFuture":
        """Map over step inputs.

        Args:
            step: The step to run.
            args: The arguments for the step function.
            kwargs: The keyword arguments for the step function.
            after: The step run output futures to wait for before executing the
                steps.
            product: Whether to produce a cartesian product of the mapped
                inputs.

        Returns:
            A future that represents the map results.
        """
        step = step.copy()
        inputs = convert_to_keyword_arguments(step.entrypoint, args, kwargs)
        invocation_id = self._allocate_invocation_id(
            step=step, custom_id=None, allow_suffix=True
        )
        map_future = MapResultsFuture(invocation_id=invocation_id)
        self._register_map_invocation(
            future=map_future,
            step=step,
            inputs=inputs,
            after=after,
            product=product,
        )
        return map_future

    @overload
    def wait(
        self,
        schema: Type[T],
        type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
        timeout: int = 600,
        poll_interval: int = 5,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
    ) -> T: ...

    @overload
    def wait(
        self,
        schema: object = None,
        type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
        timeout: int = 600,
        poll_interval: int = 5,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
    ) -> Any: ...

    def wait(
        self,
        schema: Optional[Any] = None,
        type: RunWaitConditionType = RunWaitConditionType.EXTERNAL_INPUT,
        timeout: int = 600,
        poll_interval: int = 5,
        question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
    ) -> Any:
        """Create and poll a run wait condition.

        Args:
            schema: Optional expected output type for the resolved result.
            type: Wait condition type.
            timeout: Maximum time in seconds to poll before pausing.
            poll_interval: Poll interval in seconds.
            question: Optional question shown to external actors.
            metadata: Optional metadata attached to the condition.
            name: Optional deterministic wait condition name.
            after: Optional upstream futures that must finish before waiting.

        Raises:
            RuntimeError: If called outside the dynamic pipeline function.
            _WaitConditionAborted: If the wait condition was aborted.
            _WaitConditionPollTimeout: If the wait condition polling timed out.
            KeyboardInterrupt: If interrupted while waiting.
            BaseException: If polling fails after the lease is abandoned.

        Returns:
            The resolved wait condition value.
        """
        from zenml.execution.pipeline.dynamic.run_context import (
            DynamicPipelineRunContext,
        )
        from zenml.steps.step_context import StepContext
        from zenml.utils.time_utils import utc_now

        context = DynamicPipelineRunContext.get()
        if not context:
            raise RuntimeError(
                "`zenml.wait(...)` can only be used inside dynamic pipelines."
            )

        if StepContext.is_active():
            raise RuntimeError(
                "`zenml.wait(...)` cannot be called inside a step function. "
                "Use it only in the pipeline function."
            )

        wait_condition_name = name or context.next_wait_condition_name()

        for future in collect_futures(after=after, expand_map_results=True):
            future.wait()

        condition = Client().zen_store.create_run_wait_condition(
            RunWaitConditionRequest(
                project=self._run.project_id,
                run=self._run.id,
                name=wait_condition_name,
                type=type,
                question=question,
                metadata=metadata or {},
                data_schema=pydantic_utils.get_json_schema_for_type(schema)
                if schema
                else None,
            )
        )
        state = self._handle_wait_condition_state(
            condition=condition, schema=schema
        )
        if state.is_terminal:
            return state.value

        if poll_interval <= 0:
            logger.debug(
                "Non-positive poll interval provided, falling back to 5 seconds."
            )
            poll_interval = 5

        logger.info(
            "Waiting on wait condition `%s` (type=%s, timeout=%ss, poll=%ss).",
            wait_condition_name,
            type.value,
            timeout,
            poll_interval,
        )
        deadline = time.time() + timeout

        try:
            with maybe_enable_interactive_wait_prompt(
                orchestrator=self._orchestrator,
                condition=condition,
            ) as interactive_prompting_enabled:
                # We keep polling until the deadline is reached and all ongoing
                # steps have finished.
                while time.time() < deadline or self.has_in_progress_work():
                    # TODO: catch pipeline failure here and handle it.
                    lease_now = utc_now()
                    status = (
                        Client().zen_store.update_run_wait_condition_lease(
                            run_wait_condition_id=condition.id,
                            lease_update=RunWaitConditionLeaseUpdate(
                                poller_instance_id=self._orchestrator_run_id,
                                poller_lease_expires_at=lease_now
                                + timedelta(
                                    seconds=max(15, poll_interval * 2)
                                ),
                            ),
                        )
                    )
                    if status != RunWaitConditionStatus.PENDING:
                        condition = Client().zen_store.get_run_wait_condition(
                            condition.id, hydrate=True
                        )
                    state = self._handle_wait_condition_state(
                        condition=condition, schema=schema
                    )
                    if state.is_terminal:
                        return state.value

                    if interactive_prompting_enabled:
                        # If we're running interactively, we sleep until the
                        # polling interval is reached or the user submitted
                        # input in their terminal.
                        poll_interactive_wait_condition_input(
                            condition=condition,
                            poll_interval=poll_interval,
                        )
                    else:
                        time.sleep(poll_interval)
        except _WaitConditionAborted:
            raise
        except KeyboardInterrupt:
            try:
                Client().zen_store.resolve_run_wait_condition(
                    run_wait_condition_id=condition.id,
                    resolve_request=RunWaitConditionResolveRequest(
                        resolution=RunWaitConditionResolution.ABORT,
                    ),
                )
            except Exception as e:
                logger.warning(
                    "Failed to abort wait condition `%s` after keyboard "
                    "interrupt: %s",
                    condition.id,
                    e,
                )
            raise
        except BaseException:
            try:
                Client().zen_store.update_run_wait_condition_lease(
                    run_wait_condition_id=condition.id,
                    lease_update=RunWaitConditionLeaseUpdate(
                        poller_instance_id=self._orchestrator_run_id,
                        poller_lease_expires_at=utc_now(),
                        mode=RunWaitConditionLeaseMode.ABANDON,
                    ),
                )
            except Exception as e:
                logger.warning(
                    "Failed to abandon wait condition `%s` after wait loop "
                    "failure: %s",
                    condition.id,
                    e,
                )
            raise

        status = Client().zen_store.update_run_wait_condition_lease(
            run_wait_condition_id=condition.id,
            lease_update=RunWaitConditionLeaseUpdate(
                poller_instance_id=self._orchestrator_run_id,
                poller_lease_expires_at=utc_now(),
                mode=RunWaitConditionLeaseMode.FINALIZE,
            ),
        )
        if status != RunWaitConditionStatus.PENDING:
            condition = Client().zen_store.get_run_wait_condition(
                condition.id, hydrate=True
            )
        state = self._handle_wait_condition_state(
            condition=condition, schema=schema
        )
        if state.is_terminal:
            return state.value

        raise _WaitConditionPollTimeout(
            f"Wait condition `{condition.name}` polling timed out."
        )

    @staticmethod
    def _handle_wait_condition_state(
        condition: "RunWaitConditionResponse",
        schema: Optional[Any] = None,
    ) -> _WaitConditionState:
        """Handle wait conditions.

        Args:
            condition: The latest wait condition state.
            schema: Optional schema used to parse the resolved result.

        Raises:
            _WaitConditionAborted: If the condition was resolved with abort.

        Returns:
            State indicating whether the condition is terminal and its value.
        """
        if condition.status == RunWaitConditionStatus.PENDING:
            return _WaitConditionState(is_terminal=False, value=None)

        if condition.resolution == RunWaitConditionResolution.ABORT:
            raise _WaitConditionAborted(
                f"Wait condition `{condition.name}` resolved with abort."
            )

        if schema is None:
            return _WaitConditionState(is_terminal=True, value=None)

        return _WaitConditionState(
            is_terminal=True,
            value=TypeAdapter(schema).validate_python(condition.result),
        )

    def has_in_progress_work(self) -> bool:
        """Check if there is any in-progress tracked work.

        Returns:
            True if there is any in-progress tracked work, False otherwise.
        """
        return self._future_registry.has_in_progress_work()

    # Failure/Shutdown handling

    def wait_until_done_or_failure(self) -> None:
        """Wait until all futures finished or a failure has been detected.

        Raises:
            BaseException: If a failure has been detected.
        """  # noqa: DOC503
        while True:
            if self._exception:
                raise self._exception

            if not self.has_in_progress_work():
                if self._exception:
                    raise self._exception
                return

            time.sleep(1)

    def _on_failure_detected(self, exception: BaseException) -> None:
        """Handle any failure that happens during pipeline execution.

        This method
        - cancels all in-progress startup work
        - sets a flag that prevents any new startup work from being started
        - stops all isolated steps in the FAIL_FAST execution mode

        Args:
            exception: The failure exception.
        """
        steps_to_stop: List["StepRunResponse"] = []
        nodes_to_cancel: List[Union["StepNode", "MapNode"]] = []

        with self._lifecycle_lock:
            if self._failure_detected:
                return
            self._failure_detected = True
            self._exception = exception

            nodes_to_cancel = self._dependency_graph.list_nodes(
                states={NodeState.PENDING, NodeState.READY, NodeState.STARTING}
            )
            if self._fail_fast:
                steps_to_stop = list(self._steps_to_monitor.values())

        logger.debug(
            "Initial pipeline failure detected: %s",
            str(exception),
        )

        startup_cancelled_exception = StartupCancelled(str(exception))
        for node in nodes_to_cancel:
            if isinstance(node, StepNode):
                self._future_registry.cancel_step_startup(
                    invocation_id=node.node_id,
                    exception=startup_cancelled_exception,
                )
            elif isinstance(node, MapNode):
                self._future_registry.cancel_map_startup(
                    map_id=node.node_id,
                    exception=startup_cancelled_exception,
                )

        logger.debug("Startup work cancelled.")
        self._startup_event.set()

        for step_run in steps_to_stop:
            try:
                self._stop_isolated_step(step_run)
            except Exception:
                logger.exception("Failed to stop step `%s`.", step_run.name)

        logger.debug("Requested stopping of isolated steps.")
        self._monitoring_event.set()

    def _stop_isolated_step(self, step_run: "StepRunResponse") -> None:
        """Stop an isolated step.

        Args:
            step_run: The step run to stop.
        """
        if step_run.config.step_operator:
            assert self._step_operator
            self._step_operator.cancel(step_run)
        else:
            self._orchestrator.stop_isolated_step(step_run)

    def _raise_if_startup_cancelled(self) -> None:
        """Abort startup work once a failure has been detected.

        Raises:
            StartupCancelled: If a failure has been detected.
        """
        if self._failure_detected:
            raise StartupCancelled(
                "Dynamic pipeline runner is not starting new work."
            )

    def _abort_and_drain(self, exception: BaseException) -> None:
        """Trigger the failure path and wait for in-flight work to finish.

        Args:
            exception: Exception that triggered the abort.
        """
        self._on_failure_detected(exception=exception)
        self._future_registry.await_all_no_raise()

    def _get_step_exception(
        self, step_run: "StepRunResponse"
    ) -> BaseException:
        """Get the failure exception for a step run.

        Args:
            step_run: The step run.

        Returns:
            The failure exception.
        """
        return exception_utils.reconstruct_exception(
            exception_info=step_run.exception_info,
            fallback_message=(
                f"Step `{step_run.name}` failed with status "
                f"`{step_run.status}`."
            ),
        )

    # Concurrent step lifecycle

    def _register_concurrent_step_invocation(
        self,
        future: StepFuture,
        initial_state: Optional[NodeState] = None,
        step: Optional[BaseStep] = None,
        inputs: Optional[Dict[str, Any]] = None,
        after: Union[AnyStepFuture, Sequence[AnyStepFuture], None] = None,
        config_overrides: Optional["StepConfigurationUpdate"] = None,
    ) -> None:
        """Register a concurrent step invocation.

        Args:
            future: The step future.
            initial_state: Optional initial graph state for the node.
            step: Optional step payload for startup.
            inputs: Optional input payload for startup.
            after: Optional upstream futures for startup.
            config_overrides: Optional config overrides for the step.
        """
        if inputs is not None:
            upstream_node_ids = _collect_upstream_node_ids(
                inputs=inputs, after=after
            )
        else:
            upstream_node_ids = None

        with self._lifecycle_lock:
            if self._failure_detected and initial_state in {
                None,
                NodeState.PENDING,
                NodeState.READY,
                NodeState.STARTING,
            }:
                # This is a future that requires startup but startup has already
                # been cancelled.
                future._cancel_startup(
                    StartupCancelled(
                        f"Startup for step `{future.invocation_id}` was "
                        "cancelled."
                    )
                )
                return

            self._future_registry.register_step_future(
                invocation_id=future.invocation_id, future=future
            )
            nodes_ready = self._dependency_graph.register_step_node(
                node_id=future.invocation_id,
                upstream_ids=upstream_node_ids,
                state=initial_state,
                step=step,
                inputs=inputs,
                after=after,
                config_overrides=config_overrides,
            )
        self._handle_graph_update(nodes_ready)

    def _handle_step_starting(self, invocation_id: str) -> None:
        """Mark a step node as starting in the dependency graph.

        Args:
            invocation_id: The step invocation ID.
        """
        nodes_ready = self._dependency_graph.mark_node_starting(
            node_id=invocation_id
        )
        self._handle_graph_update(nodes_ready)

    def _handle_step_ready(self, node: StepNode) -> None:
        """Handle a ready step node.

        Args:
            node: The step node.

        Raises:
            RuntimeError: If the step node is missing startup payload.
        """
        if node.step is None or node.inputs is None:
            raise RuntimeError(
                f"Missing startup payload for step node `{node.node_id}`."
            )

        self._handle_step_starting(invocation_id=node.node_id)

        compiled_step = self._compile_or_reuse(
            step=node.step,
            invocation_id=node.node_id,
            inputs=node.inputs,
            after=node.after,
            config=node.config_overrides,
        )

        runtime = get_step_runtime(
            step_config=compiled_step.config,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            orchestrator=self._orchestrator,
        )

        with self._lifecycle_lock:
            # This error will be caught by the startup loop and set as a
            # startup failure on the future.
            self._raise_if_startup_cancelled()

            execution_future: StepExecutionFuture
            if runtime == StepRuntime.INLINE:
                remaining_retries = None
                if step_run := self._existing_step_runs.get(node.node_id):
                    remaining_retries = get_remaining_retries(
                        step_run=step_run
                    )

                execution_future = self._queue_concurrent_inline_step(
                    step=compiled_step, remaining_retries=remaining_retries
                )
            else:
                execution_future = self._queue_concurrent_isolated_step(
                    step=compiled_step
                )

            self._handle_step_startup_succeeded(
                invocation_id=node.node_id,
                execution_future=execution_future,
            )

    def _queue_concurrent_isolated_step(
        self, step: "Step"
    ) -> _IsolatedStepFuture:
        """Queue a concurrent isolated step.

        Args:
            step: The step to queue.

        Returns:
            The step future.
        """

        def _launch_no_wait() -> StepRunResponse:
            try:
                step_run = launch_step(
                    snapshot=self._snapshot,
                    step=step,
                    orchestrator_run_id=self._orchestrator_run_id,
                    # The monitoring loop is responsible for monitoring and retrying
                    # steps.
                    wait=False,
                    retry=False,
                )
            except BaseException as e:
                self._handle_step_execution_failed(
                    invocation_id=step.spec.invocation_id, exception=e
                )
                raise e

            self._register_isolated_step_for_monitoring(
                invocation_id=step.spec.invocation_id,
                step_run=step_run,
            )
            return step_run

        ctx = contextvars.copy_context()
        concurrent_future = self._executor.submit(ctx.run, _launch_no_wait)
        return _IsolatedStepFuture(
            wrapped=concurrent_future,
            pipeline_run_id=self._run.id,
            invocation_id=step.spec.invocation_id,
        )

    def _queue_concurrent_inline_step(
        self, step: "Step", remaining_retries: Optional[int] = None
    ) -> _InlineStepFuture:
        """Queue a concurrent inline step.

        Args:
            step: The step to queue.
            remaining_retries: The remaining retries for the step.

        Returns:
            The step future.
        """

        def _launch_and_wait() -> StepRunResponse:
            try:
                step_run = self._run_sync_step(
                    step=step, remaining_retries=remaining_retries
                )
            except BaseException as e:
                self._handle_step_execution_failed(
                    invocation_id=step.spec.invocation_id, exception=e
                )
                raise e

            self._on_step_finished(step_run=step_run)
            return step_run

        ctx = contextvars.copy_context()
        concurrent_future = self._executor.submit(ctx.run, _launch_and_wait)
        return _InlineStepFuture(
            wrapped=concurrent_future,
            invocation_id=step.spec.invocation_id,
        )

    def _handle_step_running(self, invocation_id: str) -> None:
        """Mark a step node as running in the dependency graph.

        Args:
            invocation_id: The step invocation ID.
        """
        nodes_ready = self._dependency_graph.mark_node_running(
            node_id=invocation_id
        )
        self._handle_graph_update(nodes_ready)

    def _handle_step_startup_succeeded(
        self, invocation_id: str, execution_future: StepExecutionFuture
    ) -> None:
        """Store a successful step startup in the registry and graph.

        Args:
            invocation_id: The step invocation ID.
            execution_future: The future for the started step execution.
        """
        self._future_registry.bind_step_execution_future(
            invocation_id=invocation_id, future=execution_future
        )
        nodes_ready = self._dependency_graph.mark_node_running(
            node_id=invocation_id
        )
        self._handle_graph_update(nodes_ready)

    def _handle_step_startup_failed(
        self, invocation_id: str, exception: BaseException
    ) -> None:
        """Store a failed step startup in the registry and graph.

        Args:
            invocation_id: The step invocation ID.
            exception: The startup exception.
        """
        self._future_registry.fail_step_startup(
            invocation_id=invocation_id, exception=exception
        )
        nodes_ready = self._dependency_graph.mark_node_failed(
            node_id=invocation_id
        )
        self._handle_graph_update(nodes_ready)
        self._on_failure_detected(exception=exception)

    def _on_step_finished(self, step_run: "StepRunResponse") -> None:
        """Handle a terminal step run.

        Args:
            step_run: The terminal step run.
        """
        if not step_run.status.is_finished:
            # When this is being called from an inline future, the step run
            # might not be refreshed yet and therefore not have the correct
            # status.
            step_run = Client().get_run_step(step_run.id, hydrate=False)

        logger.debug(
            "Processing terminal step `%s` with status `%s`.",
            step_run.name,
            step_run.status,
        )

        if step_run.status.is_successful:
            self._handle_step_execution_succeeded(invocation_id=step_run.name)
        elif (
            step_run.status.is_failed
            or step_run.status == ExecutionStatus.STOPPED
        ):
            exception = self._get_step_exception(step_run=step_run)
            self._handle_step_execution_failed(
                invocation_id=step_run.name, exception=exception
            )

    def _handle_step_execution_succeeded(self, invocation_id: str) -> None:
        """Mark a step node as successfully finished.

        Args:
            invocation_id: The step invocation ID.
        """
        nodes_ready = self._dependency_graph.mark_node_succeeded(
            node_id=invocation_id
        )
        self._handle_graph_update(nodes_ready)

    def _handle_step_execution_failed(
        self,
        invocation_id: str,
        exception: BaseException,
    ) -> None:
        """Mark a step node as failed.

        Args:
            invocation_id: The step invocation ID.
            exception: Step execution exception.
        """
        nodes_ready = self._dependency_graph.mark_node_failed(
            node_id=invocation_id
        )
        self._handle_graph_update(nodes_ready)
        self._on_failure_detected(exception=exception)

    # Concurrent map lifecycle

    def _register_map_invocation(
        self,
        future: MapResultsFuture,
        step: BaseStep,
        inputs: Dict[str, Any],
        product: bool,
        after: Union[AnyStepFuture, Sequence[AnyStepFuture], None] = None,
    ) -> None:
        """Register a map invocation.

        Args:
            future: The map future.
            step: The mapped step payload for startup.
            inputs: The input payload for startup.
            after: Optional upstream futures for startup.
            product: The map expansion mode.
        """
        node_id = future.invocation_id
        upstream_node_ids = _collect_upstream_node_ids(
            inputs=inputs, after=after
        )

        with self._lifecycle_lock:
            if self._failure_detected:
                future._cancel_startup(
                    StartupCancelled(
                        f"Startup for map expansion `{node_id}` was cancelled."
                    )
                )
                return

            self._future_registry.register_map_future(
                map_id=node_id, future=future
            )
            nodes_ready = self._dependency_graph.register_map_node(
                node_id=node_id,
                step=step,
                inputs=inputs,
                product=product,
                upstream_ids=upstream_node_ids,
                after=after,
            )
        self._handle_graph_update(nodes_ready)

    def _handle_map_starting(self, map_id: str) -> None:
        """Mark a map node as starting in the dependency graph.

        Args:
            map_id: The map node ID.
        """
        nodes_ready = self._dependency_graph.mark_node_starting(node_id=map_id)
        self._handle_graph_update(nodes_ready)

    def _handle_map_ready(self, node: MapNode) -> None:
        """Handle a ready map expansion node.

        Args:
            node: The ready map node to expand.
        """
        self._handle_map_starting(map_id=node.node_id)

        kwargs = await_step_inputs(node.inputs)
        step_inputs = expand_mapped_inputs(kwargs, product=node.product)

        group_info = GroupInfo(
            id=str(uuid4()),
            name=node.step.name,
            type=GroupType.MAP,
        )

        with self._lifecycle_lock:
            # This error will be caught by the startup loop and set as a
            # startup failure on the future.
            self._raise_if_startup_cancelled()

        step_futures = [
            self.launch_step(
                node.step,
                id=f"map:{node.node_id}:{index}",
                args=(),
                kwargs=inputs,
                after=node.after,
                group=group_info,
                concurrent=True,
            )
            for index, inputs in enumerate(step_inputs)
        ]

        logger.debug(
            "Populating futures for map %s",
            node.node_id,
        )
        self._handle_map_expansion_succeeded(
            map_id=node.node_id,
            child_futures=step_futures,
        )

    def _handle_map_expansion_succeeded(
        self, map_id: str, child_futures: List[StepFuture]
    ) -> None:
        """Store a successful map expansion in the registry and graph.

        Args:
            map_id: The map ID.
            child_futures: The child step futures created for the map.
        """
        child_node_ids = [
            child_future.invocation_id for child_future in child_futures
        ]

        self._future_registry.bind_map_child_futures(
            map_id=map_id, child_futures=child_futures
        )
        nodes_ready = self._dependency_graph.attach_map_children(
            map_node_id=map_id, child_node_ids=child_node_ids
        )
        self._handle_graph_update(nodes_ready)

    def _handle_map_expansion_failed(
        self, map_id: str, exception: BaseException
    ) -> None:
        """Store a failed map expansion in the registry and graph.

        Args:
            map_id: The map ID.
            exception: The expansion exception.
        """
        self._future_registry.fail_map_startup(
            map_id=map_id, exception=exception
        )
        nodes_ready = self._dependency_graph.mark_node_failed(node_id=map_id)
        self._handle_graph_update(nodes_ready)
        self._on_failure_detected(exception=exception)


def compile_dynamic_step_invocation(
    snapshot: "PipelineSnapshotResponse",
    pipeline: "DynamicPipeline",
    step: "BaseStep",
    invocation_id: str,
    inputs: Dict[str, Any],
    pipeline_docker_settings: "DockerSettings",
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None] = None,
    config: Optional[StepConfigurationUpdate] = None,
) -> "Step":
    """Compile a dynamic step invocation.

    Args:
        snapshot: The snapshot.
        pipeline: The dynamic pipeline.
        step: The step to compile.
        invocation_id: The invocation ID of the step.
        inputs: The inputs for the step function.
        pipeline_docker_settings: The Docker settings of the parent pipeline.
        after: The step run output futures to wait for.
        config: The configuration for the step.

    Returns:
        The compiled step.
    """
    upstream_steps = set()

    for future in collect_futures(after=after, expand_map_results=True):
        future.wait()
        upstream_steps.add(future.invocation_id)

    inputs = await_step_inputs(inputs)

    for value in inputs.values():
        if isinstance(value, OutputArtifact):
            upstream_steps.add(value.step_name)

        if (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            upstream_steps.update(item.step_name for item in value)

    input_artifacts: Dict[str, Union[StepArtifact, List[StepArtifact]]] = {}
    external_artifacts = {}
    for name, value in inputs.items():
        if isinstance(value, OutputArtifact):
            input_artifacts[name] = StepArtifact(
                invocation_id=value.step_name,
                output_name=value.output_name,
                annotation=OutputSignature(resolved_annotation=Any),
                pipeline=pipeline,
                chunk_index=value.chunk_index,
                chunk_size=value.chunk_size,
            )
        elif (
            isinstance(value, list)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            input_artifacts[name] = [
                StepArtifact(
                    invocation_id=item.step_name,
                    output_name=item.output_name,
                    annotation=OutputSignature(resolved_annotation=Any),
                    pipeline=pipeline,
                    chunk_index=item.chunk_index,
                    chunk_size=item.chunk_size,
                )
                for item in value
            ]
        elif isinstance(value, (ArtifactVersionResponse, ExternalArtifact)):
            external_artifacts[name] = value
        else:
            # TODO: should some of these be parameters?
            external_artifacts[name] = ExternalArtifact(value=value)

    if template := get_config_template(snapshot, step, pipeline):
        logger.debug(
            "Using config template `%s` for step `%s`",
            template.spec.invocation_id,
            invocation_id,
        )
        step._configuration = template.config.model_copy(
            update={"template": template.spec.invocation_id}
        )

    default_parameters = {
        key: value
        for key, value in convert_to_keyword_arguments(
            step.entrypoint, (), inputs, apply_defaults=True
        ).items()
        if key not in inputs and key not in step.configuration.parameters
    }

    step_invocation = StepInvocation(
        id=invocation_id,
        step=step,
        input_artifacts=input_artifacts,
        external_artifacts=external_artifacts,
        default_parameters=default_parameters,
        upstream_steps=upstream_steps,
        pipeline=pipeline,
        model_artifacts_or_metadata={},
        client_lazy_loaders={},
        parameters={},
    )

    compiled_step = Compiler()._compile_step_invocation(
        invocation=step_invocation,
        stack=Client().active_stack,
        step_config=config,
        pipeline=pipeline,
    )

    if not compiled_step.config.docker_settings.skip_build:
        if template:
            if (
                template.config.docker_settings
                != compiled_step.config.docker_settings
            ):
                logger.warning(
                    "Custom Docker settings specified for step %s will be "
                    "ignored. The image built for template %s will be used "
                    "instead.",
                    invocation_id,
                    template.spec.invocation_id,
                )
        elif compiled_step.config.docker_settings != pipeline_docker_settings:
            logger.warning(
                "Custom Docker settings specified for step %s will be "
                "ignored. The image built for the pipeline will be used "
                "instead.",
                invocation_id,
            )

    return compiled_step


def get_step_runtime(
    step_config: "StepConfiguration",
    pipeline_docker_settings: "DockerSettings",
    orchestrator: Optional["BaseOrchestrator"] = None,
) -> StepRuntime:
    """Determine if a step should be run in process.

    Args:
        step_config: The step configuration.
        pipeline_docker_settings: The Docker settings of the parent pipeline.
        orchestrator: The orchestrator to use. If not provided, the
            orchestrator will be inferred from the active stack.

    Returns:
        The runtime for the step.
    """
    if step_config.step_operator:
        return StepRuntime.ISOLATED

    if not orchestrator:
        orchestrator = Client().active_stack.orchestrator

    if not orchestrator.can_run_isolated_steps:
        return StepRuntime.INLINE

    runtime = step_config.runtime

    if runtime is None:
        if not step_config.resource_settings.empty:
            runtime = StepRuntime.ISOLATED
        elif step_config.docker_settings != pipeline_docker_settings:
            runtime = StepRuntime.ISOLATED
        else:
            runtime = StepRuntime.INLINE

    return runtime


def get_config_template(
    snapshot: "PipelineSnapshotResponse",
    step: "BaseStep",
    pipeline: "DynamicPipeline",
) -> Optional["Step"]:
    """Get the config template for a step executed in a dynamic pipeline.

    Args:
        snapshot: The snapshot of the pipeline.
        step: The step to get the config template for.
        pipeline: The dynamic pipeline that the step is being executed in.

    Returns:
        The config template for the step.
    """
    for index, step_ in enumerate(pipeline.depends_on):
        if step_._static_id == step._static_id:
            break
    else:
        return None

    return list(snapshot.step_configurations.values())[index]


def expand_mapped_inputs(
    inputs: Dict[str, Any],
    product: bool = False,
) -> List[Dict[str, Any]]:
    """Find the mapped and unmapped inputs of a step.

    Args:
        inputs: The step function inputs.
        product: Whether to produce a cartesian product of the mapped inputs.

    Raises:
        RuntimeError: If no mapped inputs are found or the input combinations
            are not valid.

    Returns:
        The step inputs.
    """
    static_inputs: Dict[str, Any] = {}
    mapped_input_names: List[str] = []
    mapped_inputs: List[Tuple[OutputArtifact, ...]] = []

    for key, value in inputs.items():
        if isinstance(value, _Unmapped):
            static_inputs[key] = value.value
        elif isinstance(value, OutputArtifact):
            if value.item_count is None:
                static_inputs[key] = value
            elif value.item_count == 0:
                raise RuntimeError(
                    f"Artifact `{value.id}` has 0 items and cannot be mapped "
                    "over. Wrap it with the `unmapped(...)` function to pass "
                    "the artifact without mapping over it."
                )
            else:
                mapped_input_names.append(key)
                mapped_inputs.append(
                    tuple(
                        value.chunk(index=i) for i in range(value.item_count)
                    )
                )
        elif (
            isinstance(value, ArtifactVersionResponse)
            and value.item_count is not None
        ):
            static_inputs[key] = value
            logger.warning(
                "Received sequence-like artifact for step input `%s`. Mapping "
                "over artifacts that are not step output artifacts is "
                "currently not supported, and the complete artifact will be "
                "passed to all steps. If you want to silence this warning, "
                "wrap your input with the `unmapped(...)` function.",
                key,
            )
        elif (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            # List of step output artifacts, in this case the mapping is over
            # the items of the list
            mapped_input_names.append(key)
            mapped_inputs.append(tuple(value))
        elif isinstance(value, Sequence):
            logger.warning(
                "Received sequence-like data for step input `%s`. Mapping over "
                "data that is not a step output artifact is currently not "
                "supported, and the complete data will be passed to all steps. "
                "If you want to silence this warning, wrap your input with the "
                "`unmapped(...)` function.",
                key,
            )
            static_inputs[key] = value
        else:
            static_inputs[key] = value

    if len(mapped_inputs) == 0:
        raise RuntimeError(
            "No inputs to map over found. When calling `.map(...)` or "
            "`.product(...)` on a step, you need to pass at least one "
            "sequence-like step output of a previous step as input."
        )

    step_inputs = []

    if product:
        for input_combination in itertools.product(*mapped_inputs):
            all_inputs = copy.deepcopy(static_inputs)
            for name, value in zip(mapped_input_names, input_combination):
                all_inputs[name] = value
            step_inputs.append(all_inputs)
    else:
        item_counts = [len(inputs) for inputs in mapped_inputs]
        if not all(count == item_counts[0] for count in item_counts):
            raise RuntimeError(
                f"All mapped input artifacts must have the same "
                "item counts, but you passed artifacts with item counts "
                f"{item_counts}. If you want "
                "to pass sequence-like artifacts without mapping over "
                "them, wrap them with the `unmapped(...)` function."
            )

        for i in range(item_counts[0]):
            all_inputs = copy.deepcopy(static_inputs)
            for name, artifact in zip(
                mapped_input_names,
                [artifact_list[i] for artifact_list in mapped_inputs],
            ):
                all_inputs[name] = artifact
            step_inputs.append(all_inputs)

    return step_inputs


def convert_to_keyword_arguments(
    func: Callable[..., Any],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    apply_defaults: bool = False,
) -> Dict[str, Any]:
    """Convert function arguments to keyword arguments.

    Args:
        func: The function to convert the arguments to keyword arguments for.
        args: The arguments to convert to keyword arguments.
        kwargs: The keyword arguments to convert to keyword arguments.
        apply_defaults: Whether to apply the function default values.

    Returns:
        The keyword arguments.
    """
    signature = inspect.signature(func, follow_wrapped=True)
    bound_args = signature.bind_partial(*args, **kwargs)
    if apply_defaults:
        bound_args.apply_defaults()

    return bound_args.arguments


def await_step_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Await the inputs of a step.

    Args:
        inputs: The inputs of the step.

    Raises:
        RuntimeError: If a step run future with multiple output artifacts is
            passed as an input.

    Returns:
        The awaited inputs.
    """
    result = {}
    for key, value in inputs.items():
        if isinstance(value, MapResultsFuture):
            value = value.futures

        if (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, StepFuture) for item in value)
        ):
            if any(len(item._output_keys) != 1 for item in value):
                raise RuntimeError(
                    f"Invalid step input `{key}`: Passing a future that refers "
                    "to multiple output artifacts as an input to another step "
                    "is not allowed."
                )
            value = [item.artifacts() for item in value]
        elif isinstance(value, StepFuture):
            if len(value._output_keys) != 1:
                raise RuntimeError(
                    f"Invalid step input `{key}`: Passing a future that refers "
                    "to multiple output artifacts as an input to another step "
                    "is not allowed."
                )
            value = value.artifacts()

        if (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, ArtifactFuture) for item in value)
        ):
            value = [item.result() for item in value]

        if isinstance(value, ArtifactFuture):
            value = value.result()

        result[key] = value

    return result


def _collect_upstream_node_ids(
    inputs: Dict[str, Any],
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
) -> List[str]:
    """Collect upstream node IDs from step inputs and `after` futures.

    Args:
        inputs: The step inputs.
        after: Optional upstream futures for explicit ordering.

    Returns:
        The upstream node IDs.
    """
    return [
        future.invocation_id
        for future in collect_futures(inputs=inputs, after=after)
    ]


def _get_running_upstream_dependencies(
    inputs: Dict[str, Any],
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
) -> List[str]:
    """Get all running upstream dependencies for a step.

    Args:
        inputs: The inputs of the step.
        after: The step run futures to wait for.

    Raises:
        TypeError: If an unexpected future type is passed.

    Returns:
        The list of running upstream dependencies.
    """
    futures = collect_futures(inputs=inputs, after=after)

    dependencies = []

    for future in futures:
        if isinstance(future, MapResultsFuture):
            if future.startup_succeeded:
                for item in future.futures:
                    if item.running():
                        dependencies.append(item.invocation_id)
            elif future.running():
                dependencies.append(future.invocation_id)
        elif isinstance(future, BaseStepFuture):
            if future.running():
                dependencies.append(future.invocation_id)
        else:
            raise TypeError(f"Unexpected future type: {type(future)}")

    return dependencies


def get_remaining_retries(step_run: "StepRunResponse") -> int:
    """Get the remaining retries for a step run.

    Args:
        step_run: The step run to get the remaining retries for.

    Returns:
        The remaining retries for the step run.
    """
    max_retries = (
        step_run.config.retry.max_retries if step_run.config.retry else 0
    )
    return max(0, 1 + max_retries - step_run.version)
