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
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    ContextManager,
    Dict,
    Iterator,
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

from zenml.artifacts.in_memory_cache import InMemoryArtifactCache
from zenml.client import Client
from zenml.config.step_configurations import (
    GroupInfo,
    Step,
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
    HookType,
    RunWaitConditionLeaseMode,
    RunWaitConditionResolution,
    RunWaitConditionStatus,
    RunWaitConditionType,
    StepRuntime,
)
from zenml.execution.pipeline.dynamic.compilation import (
    compile_child_pipeline,
    compile_dynamic_step_invocation,
    get_step_runtime,
)
from zenml.execution.pipeline.dynamic.future_registry import (
    FutureRegistry,
    StartupCancelled,
)
from zenml.execution.pipeline.dynamic.inputs import (
    await_step_inputs,
    collect_upstream_node_ids,
    convert_to_keyword_arguments,
    get_running_upstream_dependencies,
)
from zenml.execution.pipeline.dynamic.interactive_input_utils import (
    maybe_enable_interactive_wait_prompt,
    poll_interactive_wait_condition_input,
)
from zenml.execution.pipeline.dynamic.invocation_dependency_graph import (
    ChildPipelineNode,
    InvocationDependencyGraph,
    MapNode,
    NodeState,
    StepNode,
)
from zenml.execution.pipeline.dynamic.outputs import (
    AnyOutputFuture,
    MapResultsFuture,
    PipelineFuture,
    PipelineRunOutputs,
    StepExecutionFuture,
    StepFuture,
    StepRunOutputs,
    _InlineStepFuture,
    _IsolatedStepFuture,
    wrap_step_failure,
)
from zenml.execution.pipeline.dynamic.pipeline_output_utils import (
    get_pipeline_entrypoint_output_names,
    prepare_pipeline_output_artifacts,
)
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.execution.pipeline.dynamic.utils import (
    collect_futures,
    expand_mapped_inputs,
    get_remaining_retries,
    load_pipeline_run_outputs,
    load_step_run_outputs,
)
from zenml.execution.pipeline.utils import compute_invocation_id
from zenml.execution.step.utils import launch_step
from zenml.hooks.execution import run_lifecycle_hook
from zenml.logger import get_logger
from zenml.models import (
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
    publish_pipeline_run_status_update,
    publish_stopped_step_run,
    publish_successful_step_run,
)
from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.utils import (
    env_utils,
    exception_utils,
    pagination_utils,
    pydantic_utils,
    string_utils,
)
from zenml.utils.logging_utils import (
    is_pipeline_logging_enabled,
    setup_logging_context,
)

if TYPE_CHECKING:
    from zenml.orchestrators import BaseOrchestrator


MAP_INVOCATION_ID_PREFIX = "map:"
CHILD_PIPELINE_INVOCATION_ID_PREFIX = "pipeline:"

logger = get_logger(__name__)

T = TypeVar("T")


class _WaitConditionState(NamedTuple):
    """State tuple for wait condition handling."""

    is_terminal: bool
    value: Any


class _WaitConditionAborted(Exception):
    """Raised when a wait condition is aborted."""


class RunPaused(Exception):
    """Raised when a run (or one of its descendants) entered a paused state."""


class _PipelineThreadState:
    """State of a runner's pipeline thread.

    The pipeline thread is the thread that is executing the pipeline code.
    This state object tracks whether the pipeline function is currently
    executing, blocked on a wait condition or blocked waiting for an internal
    future.
    """

    def __init__(self) -> None:
        """Initialize the state."""
        # The ID of the thread executing the pipeline function.
        self.id: Optional[int] = None
        self._stack: List[Tuple[bool, Optional[float]]] = []

    def is_working(self) -> bool:
        """Whether the runner is currently doing active work.

        Returns:
            True if the top of the stack represents active work.
        """
        if not self._stack:
            return False
        working, deadline = self._stack[-1]
        if not working:
            return False
        return deadline is None or time.time() < deadline

    @contextmanager
    def claim(self, deadline: Optional[float] = None) -> Iterator[None]:
        """Mark the pipeline thread as actively doing work.

        Args:
            deadline: If set, the frame stops counting as work once
                wall-clock time passes the deadline (used while polling a
                wait condition).

        Yields:
            None.
        """
        self._stack.append((True, deadline))
        try:
            yield
        finally:
            self._stack.pop()

    @contextmanager
    def release(self) -> Iterator[None]:
        """Mark the pipeline thread as parked on tree-internal work.

        Yields:
            None.
        """
        self._stack.append((False, None))
        try:
            yield
        finally:
            self._stack.pop()


class _PauseCoordinator:
    """Pause coordinator for the run tree."""

    def __init__(self) -> None:
        """Initialize the coordinator."""
        self._lock = threading.Lock()
        self._runners: List["DynamicPipelineRunner"] = []

    def register(self, runner: "DynamicPipelineRunner") -> None:
        """Register a runner.

        Args:
            runner: The runner to register.
        """
        with self._lock:
            self._runners.append(runner)

    def unregister(self, runner: "DynamicPipelineRunner") -> None:
        """Remove a runner.

        Args:
            runner: The runner to remove.
        """
        with self._lock:
            try:
                self._runners.remove(runner)
            except ValueError:
                pass

    def has_active_work(self) -> bool:
        """Whether any runner is currently doing active work.

        Returns:
            True if any runner reports active work, False otherwise.
        """
        with self._lock:
            runners = list(self._runners)
        return any(r.has_active_work() for r in runners)


class DynamicPipelineRunner:
    """Dynamic pipeline runner."""

    def __init__(
        self,
        snapshot: "PipelineSnapshotResponse",
        run: Optional["PipelineRunResponse"],
        orchestrator: Optional["BaseOrchestrator"] = None,
        pause_coordinator: Optional[_PauseCoordinator] = None,
        parent_runner: Optional["DynamicPipelineRunner"] = None,
    ) -> None:
        """Initialize the dynamic pipeline runner.

        Args:
            snapshot: The snapshot of the pipeline.
            run: The pipeline run.
            orchestrator: The orchestrator to use. If not provided, the
                orchestrator will be inferred from the snapshot stack.
            pause_coordinator: The pause coordinator for the run tree. The
                root runner passes `None` (creates a new coordinator);
                child runners inherit the parent's coordinator so tree-wide
                queries see the entire run tree.
            parent_runner: The parent runner, if this is a child pipeline.
                Used to cascade `_is_paused` up the ancestor chain when a
                descendant run pauses.

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

        self._parent_runner = parent_runner
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
        self._existing_step_runs = {}
        self._existing_child_runs = {}

        if self._run.status not in {
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.PROVISIONING,
        }:
            self._existing_step_runs = self._run.steps
            self._existing_child_runs = self._load_existing_child_runs()

        self._steps_to_monitor: Dict[str, "StepRunResponse"] = {}

        self._shutdown_requested = False
        self._failure_detected = False
        self._exception: Optional[BaseException] = None
        self._lifecycle_lock = threading.RLock()
        self._monitoring_event = threading.Event()
        self._startup_event = threading.Event()
        self._dependency_graph = InvocationDependencyGraph()
        self._future_registry = FutureRegistry()
        self._child_runners: Dict[str, "DynamicPipelineRunner"] = {}
        self._state = _PipelineThreadState()

        self._is_paused = False
        self._pause_coordinator = pause_coordinator or _PauseCoordinator()
        self._pause_coordinator.register(self)

    def _prepare_run(
        self,
        run: Optional["PipelineRunResponse"],
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
            resolved_orchestrator_run_id = run.orchestrator_run_id
        else:
            resolved_orchestrator_run_id = (
                self._orchestrator.get_orchestrator_run_id()
            )

        if run and not run.orchestrator_run_id:
            run = Client().zen_store.update_run(
                run_id=run.id,
                run_update=PipelineRunUpdate(
                    orchestrator_run_id=resolved_orchestrator_run_id,
                ),
            )
        else:
            existing_runs = Client().list_pipeline_runs(
                snapshot_id=self._snapshot.id,
                orchestrator_run_id=resolved_orchestrator_run_id,
            )
            if existing_runs.total == 1:
                run = existing_runs.items[0]
            else:
                run = create_placeholder_run(
                    snapshot=self._snapshot,
                    orchestrator_run_id=resolved_orchestrator_run_id,
                )

        return run, resolved_orchestrator_run_id

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

            pipeline = DynamicPipeline.load_from_source(
                self._snapshot.pipeline_spec.source
            )
            pipeline = copy.deepcopy(pipeline)
            pipeline._configuration = self._snapshot.pipeline_configuration
            self._pipeline = pipeline

        return self._pipeline

    @property
    def run(self) -> "PipelineRunResponse":
        """The run executed by this runner.

        Returns:
            The pipeline run.
        """
        return self._run

    @property
    def snapshot(self) -> "PipelineSnapshotResponse":
        """The snapshot executed by this runner.

        Returns:
            The pipeline snapshot.
        """
        return self._snapshot

    @property
    def orchestrator_run_id(self) -> str:
        """The orchestrator run ID associated with this runner.

        Returns:
            The orchestrator run ID.
        """
        return self._orchestrator_run_id

    @property
    def orchestrator(self) -> "BaseOrchestrator":
        """The orchestrator used by this runner.

        Returns:
            The orchestrator.
        """
        return self._orchestrator

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
                elif infra_status in [
                    ExecutionStatus.FAILED,
                    ExecutionStatus.STOPPED,
                ] and db_status in [
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                ]:
                    # Step failed/stopped on the infra side, but the
                    # code failed before it could report the status back to us.
                    step_run = publish_failed_step_run(step_run.id)
                elif (
                    infra_status == ExecutionStatus.COMPLETED
                    and db_status == ExecutionStatus.RUNNING
                ):
                    if step_run.config.command is not None:
                        # For isolated command steps, no zenml code is running
                        # and therefore nothing publishes the status. We assume
                        # the command finished successfully because of the
                        # infra status.
                        step_run = publish_successful_step_run(
                            step_run_id=step_run.id,
                            output_artifact_ids={},
                        )
                    else:
                        # This should never happen, handle it just in case. If
                        # this happens, the node would stay in `RUNNING` status
                        # forever and keep the pipeline from finishing. We
                        # record a failure but don't raise to keep the
                        # monitoring loop alive during the shutdown phase.
                        exc = RuntimeError(
                            f"Step `{invocation_id}` completed on the "
                            "infrastructure side but its status was not "
                            "updated."
                        )
                        self.record_failure(
                            wrap_step_failure(exc, invocation_id=invocation_id)
                        )

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
                            execution_future = (
                                self._queue_concurrent_isolated_step(step=step)
                            )
                            # Replace the execution future of the registered
                            # step future. This is done so a failed submission
                            # resolves the future instead of leaving it polling
                            # the step run that is stuck in `RETRYING` status.
                            self._future_registry.rebind_step_execution_future(
                                invocation_id=invocation_id,
                                future=execution_future,
                            )

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
                    elif isinstance(node, ChildPipelineNode):
                        self._handle_child_pipeline_ready(node=node)
                    elif isinstance(node, MapNode):
                        self._handle_map_ready(node=node)
                except Exception as e:
                    self._record_node_failure(node_id=node_id, exception=e)
                    logger.exception(
                        "Failed to start concurrent node `%s`.", node_id
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
            BaseException: If the init hook fails.
            Exception: If loading the pipeline fails.
        """
        self._state.id = threading.get_ident()
        logs_context: ContextManager[Any] = nullcontext()
        if is_pipeline_logging_enabled(self._snapshot.pipeline_configuration):
            logs_context = setup_logging_context(
                source="orchestrator", pipeline_run=self._run
            )

        with logs_context:
            run_start_hook = False
            run_resume_hook = self._run.status in {
                ExecutionStatus.RESUMING,
                ExecutionStatus.PAUSED,
            }

            if self._run.status.is_finished:
                logger.info("Run `%s` is already finished.", str(self._run.id))
                return
            elif self._run.status in {
                ExecutionStatus.RESUMING,
                # TODO: We should probably not include paused here, as we want
                # to require the user to move a run to resuming first.
                # Otherwise, the same run might be resumed multiple times.
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
                run_start_hook = True

            assert self._snapshot.stack

            try:
                pipeline = self.pipeline
            except Exception as e:
                self._publish_run_status(exception=e)
                raise

            with (
                InMemoryArtifactCache(),
                env_utils.temporary_runtime_environment(
                    self._snapshot.pipeline_configuration, self._snapshot.stack
                ),
                DynamicPipelineRunContext(
                    pipeline=pipeline,
                    run=self._run,
                    snapshot=self._snapshot,
                    runner=self,
                ),
            ):
                monitoring_thread = self._start_monitoring_loop()
                startup_thread = self._start_startup_loop()

                if run_start_hook:
                    run_lifecycle_hook(
                        self._snapshot.pipeline_configuration.start_hook_source,
                        HookType.RUN_START,
                    )
                elif run_resume_hook:
                    run_lifecycle_hook(
                        self._snapshot.pipeline_configuration.resume_hook_source,
                        HookType.RUN_RESUME,
                    )

                if not self._run.triggered_by_deployment:
                    # Only run the init hook if the run is not triggered by
                    # a deployment, as the deployment service will have
                    # already run the init hook.
                    try:
                        self._orchestrator.run_init_hook(
                            snapshot=self._snapshot
                        )
                    except BaseException as e:
                        # The init hook itself is not tracked, but its failure
                        # ends the run, so the run end and failure hooks fire
                        # before the failure propagates.
                        self._fire_terminal_run_hooks(
                            ExecutionStatus.FAILED, e
                        )
                        raise

                try:
                    self._run_entrypoint_and_finalize()
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
                    self._pause_coordinator.unregister(self)

    def _run_entrypoint_and_finalize(self) -> None:
        """Run the user entrypoint, drain remaining work, publish final status.

        Raises:
            BaseException: Any unexpected exception out of the entrypoint
                or the drain.
        """  # noqa: DOC503
        params = self.pipeline.configuration.parameters or {}
        return_value: Any = None
        try:
            with self._state.claim():
                return_value = self.pipeline._call_entrypoint(**params)
        except RunPaused:
            # Either this run or a child run that was awaited on paused.
            self._mark_paused()
        except _WaitConditionAborted as abort_exception:
            logger.info(
                "Stopping pipeline run `%s` because a wait condition "
                "was aborted.",
                self._run.id,
            )
            self._abort_and_drain(exception=abort_exception)
            # The server already published the terminal status. Refresh the run
            # so the end hook sees it, then fire the run end hook.
            self._run = Client().zen_store.get_run(self._run.id)
            self._fire_terminal_run_hooks(self._run.status)
            return
        except BaseException as e:
            logger.debug("Exception in pipeline function: %s", e)
            self._abort_and_drain(exception=e)
            self._publish_run_status(exception=e)
            self._fire_terminal_run_hooks(ExecutionStatus.FAILED, e)
            raise

        # The user code has returned. But there might still be concurrent work
        # in progress, which we now wait for. If any exception occurs in the
        # concurrent work, we raise and abort.
        try:
            self._settle_concurrent_work()
        except BaseException as e:
            logger.debug("Failure during settle: %s", e)
            self._abort_and_drain(exception=e)
            self._publish_run_status(exception=e)
            self._fire_terminal_run_hooks(ExecutionStatus.FAILED, e)
            raise

        try:
            self._publish_run_status(return_value=return_value)
            # A completed run fires end then success. A concurrent stop can
            # resolve the run to a terminal, non-completed status, which fires
            # the end hook only. A paused run fires the pause hook instead.
            if self._run.status == ExecutionStatus.PAUSED:
                run_lifecycle_hook(
                    self._snapshot.pipeline_configuration.pause_hook_source,
                    HookType.RUN_PAUSE,
                )
            elif self._run.status.is_finished:
                self._fire_terminal_run_hooks(self._run.status)
        except Exception as e:
            # Publish failed for some reason (e.g., invalid return value).
            # Mark the run failed instead of leaving it stuck in RUNNING.
            logger.exception(
                "Failed to publish outputs for pipeline `%s`.",
                self.snapshot.pipeline.name,
            )
            self._publish_run_status(exception=e)
            self._fire_terminal_run_hooks(ExecutionStatus.FAILED, e)
            raise

    def _fire_terminal_run_hooks(
        self,
        status: ExecutionStatus,
        exception: Optional[BaseException] = None,
    ) -> None:
        """Fire the run end hook, then the terminal hook matching the status.

        Args:
            status: The terminal status of the run.
            exception: The exception that ended the run, if any.
        """
        config = self._snapshot.pipeline_configuration
        run_lifecycle_hook(
            config.end_hook_source,
            HookType.RUN_END,
            optional_args=(exception,),
        )
        if status == ExecutionStatus.COMPLETED:
            run_lifecycle_hook(
                config.success_hook_source, HookType.RUN_SUCCESS
            )
        elif exception is not None:
            run_lifecycle_hook(
                config.failure_hook_source,
                HookType.RUN_FAILURE,
                optional_args=(exception,),
            )

    def notify_graph_changed(self, nodes_ready: bool) -> None:
        """Wake up the startup loop if new nodes became ready.

        Args:
            nodes_ready: Whether any new nodes are ready.
        """
        if nodes_ready:
            self._startup_event.set()

    def mark_node_starting(self, node_id: str) -> None:
        """Mark a graph node as starting and propagate readiness changes.

        Args:
            node_id: The node ID.
        """
        self.notify_graph_changed(
            self._dependency_graph.mark_node_starting(node_id=node_id)
        )

    def mark_node_running(self, node_id: str) -> None:
        """Mark a graph node as running and propagate readiness changes.

        Args:
            node_id: The node ID.
        """
        self.notify_graph_changed(
            self._dependency_graph.mark_node_running(node_id=node_id)
        )

    def mark_node_succeeded(self, node_id: str) -> None:
        """Mark a graph node as succeeded and propagate readiness changes.

        Args:
            node_id: The node ID.
        """
        self.notify_graph_changed(
            self._dependency_graph.mark_node_succeeded(node_id=node_id)
        )

    def mark_node_failed(self, node_id: str) -> None:
        """Mark a graph node as failed and propagate readiness changes.

        This only updates the graph state. Use `record_failure(exception)` to
        also trigger the pipeline-level failure cascade.

        Args:
            node_id: The node ID.
        """
        self.notify_graph_changed(
            self._dependency_graph.mark_node_failed(node_id=node_id)
        )

    def record_failure(self, exception: BaseException) -> None:
        """Trigger the pipeline-level failure cascade.

        Marks the runner as failed (idempotent), cancels in-flight startup
        work, stops isolated steps in fail-fast mode and forwards shutdown to
        running child pipelines.

        Args:
            exception: The failure exception.
        """
        # RunPaused must be handled separately and not recorded as a failure.
        assert not isinstance(exception, RunPaused)
        self._on_failure_detected(exception=exception)

    def allocate_invocation_id(
        self,
        base_name: str,
        allow_suffix: bool = True,
    ) -> str:
        """Allocate a new invocation ID with the given base name.

        Args:
            base_name: Base name for the invocation ID.
            allow_suffix: Whether to allow suffixing the invocation ID.

        Returns:
            The allocated invocation ID.
        """
        # TODO: maybe prevent `map:` prefixes for invocation IDs
        with self._invocation_id_lock:
            invocation_id = compute_invocation_id(
                existing_invocations=self._invocation_ids,
                base_name=base_name,
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
        group: Optional["GroupInfo"] = None,
        concurrent: Literal[True] = True,
    ) -> "StepFuture": ...

    def launch_step(
        self,
        step: "BaseStep",
        id: Optional[str],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
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

        invocation_id = self.allocate_invocation_id(
            base_name=id or step.name, allow_suffix=not id
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
                    self.mark_node_succeeded(node_id=invocation_id)
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
                    self.mark_node_failed(node_id=invocation_id)
                    self.record_failure(
                        exception=wrap_step_failure(
                            exception, invocation_id=invocation_id
                        )
                    )
                    return future
                else:
                    raise exception

            remaining_retries = get_remaining_retries(step_run=step_run)

            if step_run.status in {
                ExecutionStatus.PROVISIONING,
                ExecutionStatus.RUNNING,
            }:
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
                self.mark_node_running(node_id=invocation_id)
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
                := get_running_upstream_dependencies(inputs, after)
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
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
        invocation_id = self.allocate_invocation_id(
            base_name=step.name, allow_suffix=True
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
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
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
    ) -> Any:
        """Create and poll a run wait condition.

        Args:
            schema: Optional expected output type for the resolved result.
            type: Wait condition type.
            timeout: Earliest time in seconds at which polling may give up
                and pause the run. The actual pause is deferred until all
                active work in this pipeline (or any parent/child pipelines) has
                finished.
            poll_interval: Poll interval in seconds.
            question: Optional question shown to external actors.
            metadata: Optional metadata attached to the condition.
            name: Optional deterministic wait condition name.
            after: Optional upstream futures that must finish before waiting.

        Raises:
            RuntimeError: If called outside the dynamic pipeline function.
            _WaitConditionAborted: If the wait condition was aborted.
            RunPaused: If the wait condition polling timed out and the run
                was transitioned to PAUSED.
            KeyboardInterrupt: If interrupted while waiting.
            BaseException: If polling fails after the lease is abandoned.

        Returns:
            The resolved wait condition value.
        """  # noqa: DOC503
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

        if threading.get_ident() != self._state.id:
            # `wait(...)` is currently only allowed as a sync call in the
            # pipeline function.
            raise RuntimeError(
                "`zenml.wait(...)` must be called from the pipeline "
                "thread, not from a worker thread spawned inside the "
                "pipeline function."
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

        deadline = time.time() + timeout
        logger.info(
            "Waiting on wait condition `%s` (type=%s, timeout=%ss, poll=%ss).",
            wait_condition_name,
            type.value,
            timeout,
            poll_interval,
        )

        with self._state.claim(deadline):
            try:
                with maybe_enable_interactive_wait_prompt(
                    orchestrator=self._orchestrator,
                    condition=condition,
                ) as interactive_prompting_enabled:
                    # Poll while own deadline hasn't expired or any runner
                    # in the tree still has active work. Once both flip
                    # false the loop exits naturally; the lease finalize
                    # below transitions the run to PAUSED on the server.
                    while (
                        time.time() < deadline
                        or self._pause_coordinator.has_active_work()
                    ):
                        lease_now = utc_now()
                        status = Client().zen_store.update_run_wait_condition_lease(
                            run_wait_condition_id=condition.id,
                            lease_update=RunWaitConditionLeaseUpdate(
                                poller_instance_id=self._orchestrator_run_id,
                                poller_lease_expires_at=lease_now
                                + timedelta(
                                    seconds=max(15, poll_interval * 2)
                                ),
                            ),
                        )
                        if status != RunWaitConditionStatus.PENDING:
                            condition = (
                                Client().zen_store.get_run_wait_condition(
                                    condition.id, hydrate=True
                                )
                            )
                        state = self._handle_wait_condition_state(
                            condition=condition, schema=schema
                        )
                        if state.is_terminal:
                            return state.value

                        if interactive_prompting_enabled:
                            # If we're running interactively, sleep until
                            # the polling interval is reached or the user
                            # submitted input in their terminal.
                            poll_interactive_wait_condition_input(
                                condition=condition,
                                poll_interval=poll_interval,
                            )
                        else:
                            time.sleep(poll_interval)
            except _WaitConditionAborted:
                raise
            except KeyboardInterrupt as keyboard_interrupt:
                try:
                    Client().zen_store.resolve_run_wait_condition(
                        run_wait_condition_id=condition.id,
                        resolve_request=RunWaitConditionResolveRequest(
                            resolution=RunWaitConditionResolution.ABORT,
                        ),
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to abort wait condition `%s` after "
                        "keyboard interrupt: %s",
                        condition.id,
                        e,
                    )
                    # When resolving a wait condition with `ABORT` resolution,
                    # the server will transition the run to a `STOPPED` status.
                    # This failed, which means we re-raise the
                    # KeyboardInterrupt, which causes downstream code to publish
                    # a `FAILED` run status.
                    raise keyboard_interrupt
                else:
                    # Raise _WaitConditionAborted to signal that the wait
                    # condition was aborted. Downstream code will not publish
                    # a `FAILED` run status in this case.
                    raise _WaitConditionAborted(
                        f"Wait condition `{condition.name}` was aborted."
                    ) from keyboard_interrupt
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
                        "Failed to abandon wait condition `%s` after wait "
                        "loop failure: %s",
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

        raise RunPaused()

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

    # Failure/Shutdown handling

    def has_active_work(self) -> bool:
        """Whether this runner is currently doing active work.

        Returns:
            True if this runner has any active work, False otherwise.
        """
        if self._state.is_working():
            # Pipeline function is doing active work.
            return True
        for node in self._dependency_graph.list_nodes():
            if node.state in {NodeState.STARTING, NodeState.READY}:
                # A node in the graph is waiting to be executed.
                return True
            if node.state == NodeState.RUNNING:
                if isinstance(node, (ChildPipelineNode, MapNode)):
                    continue

                # A step node is in progress -> we're doing active work.
                return True
        return False

    def _mark_paused(self) -> None:
        """Mark this run paused and cascade up to the parent chain."""
        runner: Optional["DynamicPipelineRunner"] = self
        while runner is not None:
            runner._is_paused = True
            runner = runner._parent_runner

    def _settle_concurrent_work(self) -> None:
        """Block until all concurrent work has settled.

        Raises:
            BaseException: If a failure has been detected during the wait.
        """  # noqa: DOC503
        while True:
            if self._exception:
                raise self._exception
            if not self._future_registry.has_in_progress_work():
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
        nodes_to_cancel: List[
            Union["StepNode", "MapNode", "ChildPipelineNode"]
        ] = []
        child_runners_to_shutdown: List["DynamicPipelineRunner"] = []

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
                child_runners_to_shutdown = list(self._child_runners.values())

        logger.debug(
            "Initial pipeline failure detected: %s",
            str(exception),
        )

        startup_cancelled_exception = StartupCancelled(str(exception))
        for node in nodes_to_cancel:
            self._future_registry.set_startup_exception(
                invocation_id=node.node_id,
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

        child_runner_shutdown_reason = StartupCancelled(
            f"Parent pipeline `{self.pipeline.name}` failed."
        )
        for child_runner in child_runners_to_shutdown:
            child_runner.request_shutdown(reason=child_runner_shutdown_reason)
        logger.debug("Requested stopping of child pipelines.")

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

    def raise_if_startup_cancelled(self) -> None:
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

    def _publish_run_status(
        self,
        return_value: Any = None,
        exception: Optional[BaseException] = None,
    ) -> None:
        """Publish a run status update.

        Args:
            return_value: Pipeline entrypoint return value.
            exception: Exception that caused the run to fail.
        """
        if exception is not None:
            pipeline_func = (
                self._pipeline.entrypoint if self._pipeline else None
            )
            exception_info = exception_utils.collect_exception_information(
                exception=exception,
                user_func=pipeline_func,
            )
            self._run = publish_failed_pipeline_run(
                self._run.id, exception_info=exception_info
            )
            return

        if self._is_paused:
            self._run = Client().zen_store.update_run(
                run_id=self._run.id,
                run_update=PipelineRunUpdate(status=ExecutionStatus.PAUSED),
            )
            logger.info("Pausing pipeline run `%s`.", self._run.id)
            return

        outputs = prepare_pipeline_output_artifacts(
            value=return_value,
            pipeline_entrypoint=self.pipeline.entrypoint,
        )
        self._run = Client().zen_store.update_run(
            run_id=self._run.id,
            run_update=PipelineRunUpdate(
                status=ExecutionStatus.COMPLETED, outputs=outputs
            ),
        )
        logger.info(
            "Pipeline `%s` completed successfully.",
            self.snapshot.pipeline.name,
        )

    def request_shutdown(self, reason: BaseException) -> None:
        """Ask the runner to shut down.

        Args:
            reason: Exception describing why shutdown is being requested.
        """
        self._on_failure_detected(exception=reason)

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
        after: Union[AnyOutputFuture, Sequence[AnyOutputFuture], None] = None,
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
            upstream_node_ids = collect_upstream_node_ids(
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
            node, nodes_ready = self._dependency_graph.register_step_node(
                node_id=future.invocation_id,
                upstream_ids=upstream_node_ids,
                state=initial_state,
                step=step,
                inputs=inputs,
                after=after,
                config_overrides=config_overrides,
            )
            if node.state == NodeState.PAUSED:
                self._future_registry.set_startup_exception(
                    invocation_id=node.node_id, exception=RunPaused()
                )
        self.notify_graph_changed(nodes_ready)

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

        self.mark_node_starting(node_id=node.node_id)

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
            self.raise_if_startup_cancelled()

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
                self.mark_node_failed(node_id=step.spec.invocation_id)
                self.record_failure(
                    exception=wrap_step_failure(
                        e, invocation_id=step.spec.invocation_id
                    )
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
                self.mark_node_failed(node_id=step.spec.invocation_id)
                self.record_failure(
                    exception=wrap_step_failure(
                        e, invocation_id=step.spec.invocation_id
                    )
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
        self.mark_node_running(node_id=invocation_id)

    def _record_node_failure(
        self, node_id: str, exception: BaseException
    ) -> None:
        """Record a failure for a registered concurrent node.

        Args:
            node_id: The invocation ID of the failed node.
            exception: The failure exception. Must not be a `RunPaused`
                (see `record_failure`).
        """
        self._future_registry.set_startup_exception(
            invocation_id=node_id, exception=exception
        )
        self.mark_node_failed(node_id=node_id)
        self.record_failure(exception=exception)

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
            self.mark_node_succeeded(node_id=step_run.name)
        elif (
            step_run.status.is_failed
            or step_run.status == ExecutionStatus.STOPPED
        ):
            exception = self._get_step_exception(step_run=step_run)
            self.mark_node_failed(node_id=step_run.name)
            self.record_failure(
                exception=wrap_step_failure(
                    exception, invocation_id=step_run.name
                )
            )

    # Concurrent map lifecycle

    def _register_map_invocation(
        self,
        future: MapResultsFuture,
        step: BaseStep,
        inputs: Dict[str, Any],
        product: bool,
        after: Union[AnyOutputFuture, Sequence[AnyOutputFuture], None] = None,
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
        upstream_node_ids = collect_upstream_node_ids(
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
            node, nodes_ready = self._dependency_graph.register_map_node(
                node_id=node_id,
                step=step,
                inputs=inputs,
                product=product,
                upstream_ids=upstream_node_ids,
                after=after,
            )
            if node.state == NodeState.PAUSED:
                self._future_registry.set_startup_exception(
                    invocation_id=node.node_id, exception=RunPaused()
                )
        self.notify_graph_changed(nodes_ready)

    def _handle_map_ready(self, node: MapNode) -> None:
        """Handle a ready map expansion node.

        Args:
            node: The ready map node to expand.
        """
        self.mark_node_starting(node_id=node.node_id)

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
            self.raise_if_startup_cancelled()

        step_futures = [
            self.launch_step(
                node.step,
                id=f"{MAP_INVOCATION_ID_PREFIX}{node.node_id}:{index}",
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
        self.notify_graph_changed(nodes_ready)

    # Child pipeline lifecycle

    @overload
    def submit_child_pipeline(
        self,
        pipeline: "DynamicPipeline",
        args: Sequence[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
        *,
        concurrent: Literal[True],
    ) -> PipelineFuture: ...

    @overload
    def submit_child_pipeline(
        self,
        pipeline: "DynamicPipeline",
        args: Sequence[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
        *,
        concurrent: Literal[False] = False,
    ) -> PipelineRunOutputs: ...

    def submit_child_pipeline(
        self,
        pipeline: "DynamicPipeline",
        args: Sequence[Any],
        kwargs: Dict[str, Any],
        after: Union[
            "AnyOutputFuture", Sequence["AnyOutputFuture"], None
        ] = None,
        *,
        concurrent: bool = False,
    ) -> Union[PipelineFuture, PipelineRunOutputs]:
        """Submit a child pipeline.

        Args:
            pipeline: Child pipeline to execute.
            args: Positional pipeline arguments.
            kwargs: Keyword pipeline arguments.
            after: Optional dependency futures.
            concurrent: Whether to run the child pipeline concurrently.

        Returns:
            A `PipelineFuture` for concurrent calls or the resolved
            `PipelineRunOutputs` for synchronous calls.
        """
        pipeline = pipeline.copy()
        # Fail early for invalid args/kwargs.
        convert_to_keyword_arguments(pipeline.entrypoint, tuple(args), kwargs)
        node_id = self.allocate_invocation_id(
            base_name=f"{CHILD_PIPELINE_INVOCATION_ID_PREFIX}{pipeline.name}"
        )

        if concurrent:
            pipeline_future = PipelineFuture(
                invocation_id=node_id,
                declared_output_names=get_pipeline_entrypoint_output_names(
                    pipeline.entrypoint
                ),
            )
            self._register_concurrent_child_pipeline_invocation(
                node_id=node_id,
                pipeline=pipeline,
                args=tuple(args),
                kwargs=kwargs,
                after=after,
                future=pipeline_future,
            )
            return pipeline_future
        else:
            child_run = self._prepare_child_run(
                pipeline=pipeline,
                args=args,
                kwargs=kwargs,
                after=after,
                child_invocation_id=node_id,
            )
            child_runner = self._build_child_runner(child_run=child_run)

            with self._lifecycle_lock:
                if self._failure_detected:
                    self._mark_child_run_placeholder_failed(
                        child_run=child_run,
                        reason=(
                            "Parent run shut down before child run started."
                        ),
                    )
                    self.raise_if_startup_cancelled()
                self._child_runners[node_id] = child_runner
            logger.info(
                "Launching child pipeline `%s`", child_runner.pipeline.name
            )
            try:
                # Yield the pipeline thread while the child runner is running
                # sync. This is necessary to avoid the following deadlock:
                # - The child run waits on a wait condition
                # - Us (= the parent runner) reports active work, which causes
                #   the wait condition to never timeout.
                with self._state.release():
                    child_runner.run_pipeline()
                terminal_run = self._validate_successful_child_run(
                    child_runner.run
                )
            finally:
                self._unregister_child_runner(node_id=node_id)
            logger.info(
                "Child pipeline `%s` completed", child_runner.pipeline.name
            )
            return load_pipeline_run_outputs(terminal_run)

    def _register_concurrent_child_pipeline_invocation(
        self,
        node_id: str,
        pipeline: "DynamicPipeline",
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None],
        future: PipelineFuture,
    ) -> None:
        """Register a concurrent child pipeline invocation.

        Args:
            node_id: Dependency graph node ID for the child pipeline.
            pipeline: The child pipeline.
            args: Positional arguments passed to the child pipeline.
            kwargs: Keyword arguments passed to the child pipeline.
            after: Optional upstream futures for startup ordering.
            future: The child pipeline future.
        """
        inputs = convert_to_keyword_arguments(
            pipeline.entrypoint, tuple(args), kwargs
        )
        upstream_node_ids = collect_upstream_node_ids(
            inputs=inputs, after=after
        )

        with self._lifecycle_lock:
            if self._failure_detected:
                future._cancel_startup(
                    StartupCancelled(
                        f"Startup for child pipeline `{node_id}` was cancelled."
                    )
                )
                return
            self._future_registry.register_pipeline_future(
                node_id=node_id,
                future=future,
            )
            node, nodes_ready = (
                self._dependency_graph.register_child_pipeline_node(
                    node_id=node_id,
                    pipeline=pipeline,
                    args=args,
                    kwargs=kwargs,
                    upstream_ids=upstream_node_ids,
                )
            )
            if node.state == NodeState.PAUSED:
                self._future_registry.set_startup_exception(
                    invocation_id=node.node_id, exception=RunPaused()
                )
        self.notify_graph_changed(nodes_ready=nodes_ready)

    def _handle_child_pipeline_ready(self, node: ChildPipelineNode) -> None:
        """Drive a ready child pipeline node to running state.

        Compiles the child run, builds a child runner, submits it to the
        executor and tracks the runner for shutdown propagation.

        Args:
            node: The ready child pipeline node.
        """
        self.mark_node_starting(node_id=node.node_id)

        child_run = self._prepare_child_run(
            pipeline=node.pipeline,
            args=node.args,
            kwargs=node.kwargs,
            after=None,
            child_invocation_id=node.node_id,
        )

        child_runner = self._build_child_runner(child_run=child_run)
        node_id = node.node_id

        def _launch_and_wait() -> "PipelineRunResponse":
            try:
                child_runner.run_pipeline()
                terminal_run = self._validate_successful_child_run(
                    child_runner.run
                )
                logger.info(
                    "Child pipeline `%s` completed", child_runner.pipeline.name
                )
                self.mark_node_succeeded(node_id=node_id)
                return terminal_run
            except RunPaused as paused_exception:
                logger.info(
                    "Child pipeline `%s` paused.", child_runner.pipeline.name
                )
                # Cascade the pause through the dependency graph and
                # settle each cascaded future. Don't record a failure:
                # the parent should keep running.
                for paused_node_id in self._dependency_graph.mark_node_paused(
                    node_id=node_id
                ):
                    self._future_registry.set_startup_exception(
                        invocation_id=paused_node_id,
                        exception=paused_exception,
                    )
                raise
            except BaseException as exception:
                self.mark_node_failed(node_id=node_id)
                self.record_failure(exception=exception)
                raise
            finally:
                self._unregister_child_runner(node_id=node_id)

        with self._lifecycle_lock:
            if self._failure_detected:
                # Failure detected between our placeholder creation and lock
                # acquisition. Mark the placeholder as failed so we don't
                # leak an INITIALIZING run in the DB.
                self._mark_child_run_placeholder_failed(
                    child_run=child_run,
                    reason=("Parent run shut down before child run started."),
                )
                self.raise_if_startup_cancelled()
            self._child_runners[node_id] = child_runner

        logger.info(
            "Launching child pipeline `%s`", child_runner.pipeline.name
        )

        # Run child pipelines on a dedicated daemon thread rather than the
        # parent's bounded step executor. Otherwise, child pipelines could
        # starve sibling step launches.
        context = contextvars.copy_context()
        execution_future: Future["PipelineRunResponse"] = Future()

        def _run_in_thread() -> None:
            try:
                result = context.run(_launch_and_wait)
            except BaseException as exc:
                execution_future.set_exception(exc)
            else:
                execution_future.set_result(result)

        threading.Thread(
            name=f"DynamicPipelineRunner-ChildPipeline-{node_id}",
            target=_run_in_thread,
            daemon=True,
        ).start()

        self._handle_child_pipeline_startup_succeeded(
            node_id=node_id, execution_future=execution_future
        )

    def _handle_child_pipeline_startup_succeeded(
        self,
        node_id: str,
        execution_future: Future["PipelineRunResponse"],
    ) -> None:
        """Bind the execution future to the registered pipeline future.

        Args:
            node_id: The child pipeline node ID.
            execution_future: The future for the started child pipeline.
        """
        pipeline_future = self._future_registry.get_pipeline_future(
            node_id=node_id
        )
        pipeline_future._set_startup_result(execution_future)
        self.mark_node_running(node_id=node_id)

    def _prepare_child_run(
        self,
        pipeline: "DynamicPipeline",
        args: Sequence[Any],
        kwargs: Dict[str, Any],
        after: Union["AnyOutputFuture", Sequence["AnyOutputFuture"], None],
        child_invocation_id: str,
    ) -> "PipelineRunResponse":
        """Prepare a child run.

        Args:
            pipeline: Child pipeline to execute.
            args: Positional pipeline arguments.
            kwargs: Keyword pipeline arguments.
            after: Optional dependency futures to wait on before snapshotting.
            child_invocation_id: Deterministic invocation ID for the child.

        Returns:
            The child run, hydrated with its snapshot.
        """
        if existing_run := self._existing_child_runs.get(child_invocation_id):
            return existing_run

        if after is not None:
            for future in collect_futures(
                after=after, expand_map_results=True
            ):
                future.wait()

        child_snapshot = compile_child_pipeline(
            pipeline=pipeline,
            args=tuple(args),
            kwargs=kwargs,
            parent_snapshot=self._snapshot,
        )
        return create_placeholder_run(
            snapshot=child_snapshot,
            orchestrator_run_id=self._orchestrator_run_id,
            parent_run_id=self._run.id,
            child_key=child_invocation_id,
        )

    def _build_child_runner(
        self, child_run: "PipelineRunResponse"
    ) -> "DynamicPipelineRunner":
        """Construct a runner for a child pipeline run.

        Args:
            child_run: The hydrated child run.

        Returns:
            The child runner.
        """
        assert child_run.snapshot is not None
        return DynamicPipelineRunner(
            snapshot=child_run.snapshot,
            run=child_run,
            orchestrator=self._orchestrator,
            pause_coordinator=self._pause_coordinator,
            parent_runner=self,
        )

    def _load_existing_child_runs(
        self,
    ) -> Dict[str, "PipelineRunResponse"]:
        """Load and return the cache of existing child runs.

        Returns:
            The cache mapping child key to child run.
        """
        child_runs: Dict[str, "PipelineRunResponse"] = {}
        for run in pagination_utils.depaginate(
            Client().list_pipeline_runs,
            parent_run_id=self._run.id,
            size=100,
            hydrate=False,
        ):
            assert run.child_key is not None
            child_runs[run.child_key] = run
        return child_runs

    def _validate_successful_child_run(
        self, child_run: "PipelineRunResponse"
    ) -> "PipelineRunResponse":
        """Validate that a child run reached a successful terminal state.

        Args:
            child_run: The child run.

        Raises:
            RunPaused: If the child paused on a wait condition.
            BaseException: The reconstructed child failure exception if the
                child run failed.

        Returns:
            The successful child run.
        """  # noqa: DOC503
        if child_run.status.is_successful:
            return child_run

        if child_run.status == ExecutionStatus.PAUSED:
            raise RunPaused()

        raise exception_utils.reconstruct_exception(
            exception_info=child_run.exception_info,
            fallback_message=(
                f"Child pipeline `{child_run.name}` failed with status "
                f"`{child_run.status}`."
            ),
        )

    def _mark_child_run_placeholder_failed(
        self, child_run: "PipelineRunResponse", reason: str
    ) -> None:
        """Mark an unstarted placeholder child run as failed.

        Used to clean up after a startup-cancellation race where a placeholder
        run was created but the child never started executing. Best-effort:
        any error here is logged and swallowed so we don't mask the original
        cancellation.

        Args:
            child_run: The child run.
            reason: Status reason to record for the failure.
        """
        if child_run.status not in {
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.PROVISIONING,
        }:
            return
        try:
            publish_pipeline_run_status_update(
                pipeline_run_id=child_run.id,
                status=ExecutionStatus.FAILED,
                status_reason=reason,
            )
        except Exception:
            logger.exception(
                "Failed to mark child placeholder run `%s` as failed.",
                child_run.id,
            )

    def _unregister_child_runner(self, node_id: str) -> None:
        """Drop a child runner from the in-progress map.

        Args:
            node_id: The child pipeline node ID.
        """
        with self._lifecycle_lock:
            self._child_runners.pop(node_id, None)
