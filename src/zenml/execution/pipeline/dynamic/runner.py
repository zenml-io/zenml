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

import copy
import inspect
import itertools
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
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
from zenml.execution.pipeline.dynamic.interactive_input_utils import (
    maybe_enable_interactive_wait_prompt,
    poll_interactive_wait_condition_input,
)
from zenml.execution.pipeline.dynamic.invocation_state import InvocationState
from zenml.execution.pipeline.dynamic.outputs import (
    AnyStepFuture,
    ArtifactFuture,
    BaseFuture,
    BaseStepFuture,
    MapResultsFuture,
    OutputArtifact,
    StepFuture,
    StepRunOutputs,
    _InlineStepFuture,
    _IsolatedStepFuture,
)
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.execution.pipeline.dynamic.startup_controller import (
    StartupController,
    _StartupStatus,
)
from zenml.execution.pipeline.dynamic.utils import (
    _Unmapped,
    load_step_run_outputs,
    wait_for_step_to_finish,
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
    publish_failed_pipeline_run,
    publish_failed_step_run,
    publish_stopped_step_run,
    publish_successful_pipeline_run,
)
from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.stack import Stack
from zenml.steps.entrypoint_function_utils import StepArtifact
from zenml.steps.step_invocation import StepInvocation
from zenml.steps.utils import OutputSignature
from zenml.utils import (
    context_utils,
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
    from zenml.steps import BaseStep


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


class _PreparedStepLaunch(NamedTuple):
    """Prepared launch state for a ready step invocation."""

    compiled_step: "Step"
    runtime: StepRuntime
    remaining_retries: Optional[int]
    existing_step_run: Optional["StepRunResponse"]


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

        worker_count = handle_int_env_var(
            ENV_ZENML_DYNAMIC_PIPELINE_WORKER_COUNT, default=10
        )
        self._executor = ThreadPoolExecutor(max_workers=worker_count)
        if orchestrator:
            self._orchestrator = orchestrator
        else:
            self._orchestrator = Stack.from_model(snapshot.stack).orchestrator

        self._step_operator = Stack.from_model(snapshot.stack).step_operator
        self._futures: Dict[str, "StepFuture"] = {}
        self._invocation_states: Dict[str, InvocationState] = {}
        self._invocation_ids: Set[str] = set()
        self._state_lock = threading.RLock()

        self._run, self._orchestrator_run_id = self._prepare_run(run)
        self._existing_step_runs = self._run.steps

        self._steps_to_monitor: Dict[str, "StepRunResponse"] = {}
        self._shutdown_event = threading.Event()
        self._startup_controller = StartupController(self)

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
    def run(self) -> "PipelineRunResponse":
        """The pipeline run being executed.

        Returns:
            The pipeline run being executed.
        """
        return self._run

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

    def _track_future(self, invocation_id: str, future: "StepFuture") -> None:
        """Track a step future for shutdown and waiting.

        Args:
            invocation_id: The invocation ID of the step.
            future: The future to track.
        """
        with self._state_lock:
            self._futures[invocation_id] = future

    def _track_invocation_state(
        self, invocation_id: str, invocation_state: InvocationState
    ) -> None:
        """Track invocation state for monitor and completion callbacks.

        Args:
            invocation_id: The invocation ID of the step.
            invocation_state: The invocation state to track.
        """
        with self._state_lock:
            self._invocation_states[invocation_id] = invocation_state

    def _forget_invocation_state(self, invocation_id: str) -> None:
        """Drop runner-owned invocation state after terminal completion.

        Args:
            invocation_id: The invocation ID of the step.
        """
        with self._state_lock:
            self._invocation_states.pop(invocation_id, None)

    def _create_startup_step_future(
        self,
        *,
        invocation_id: str,
        output_keys: List[str],
        runtime: StepRuntime,
    ) -> tuple[InvocationState, StepFuture]:
        """Create a step future and invocation state for controller startup.

        Args:
            invocation_id: The invocation ID of the step.
            output_keys: The output keys of the step.
            runtime: The predicted runtime of the step.

        Returns:
            The shared invocation state and the public step future.
        """
        invocation_state = InvocationState(invocation_id=invocation_id)
        if runtime == StepRuntime.INLINE:
            wrapped_future: Union[_InlineStepFuture, _IsolatedStepFuture] = (
                _InlineStepFuture(
                    invocation_id=invocation_id,
                    state=invocation_state,
                )
            )
        else:
            wrapped_future = _IsolatedStepFuture(
                pipeline_run_id=self.run.id,
                invocation_id=invocation_id,
                state=invocation_state,
            )

        future = StepFuture(wrapped=wrapped_future, output_keys=output_keys)
        self._track_future(invocation_id=invocation_id, future=future)
        self._track_invocation_state(
            invocation_id=invocation_id,
            invocation_state=invocation_state,
        )
        return invocation_state, future

    def _submit_startup_step(
        self,
        *,
        step: "BaseStep",
        invocation_id: str,
        inputs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
        step_config: Optional["StepConfigurationUpdate"],
        waiting_for_steps: List[str],
    ) -> StepFuture:
        """Create and register a concurrent step future.

        Args:
            step: The submitted step.
            invocation_id: The invocation ID of the step.
            inputs: The submitted step inputs.
            after: Optional upstream futures for ordering metadata.
            step_config: Optional step configuration overrides.
            waiting_for_steps: Running upstream invocation IDs for logging.

        Returns:
            The public future for the submitted step.
        """
        runtime = self._predict_step_runtime(step=step, step_config=step_config)
        invocation_state, future = self._create_startup_step_future(
            invocation_id=invocation_id,
            output_keys=list(step.entrypoint_definition.outputs),
            runtime=runtime,
        )
        self._startup_controller.register_step(
            step=step,
            invocation_id=invocation_id,
            inputs=inputs,
            after=after,
            step_config=step_config,
            invocation_state=invocation_state,
            waiting_for_steps=waiting_for_steps,
        )
        return future

    def _reserve_invocation_id(
        self, step: "BaseStep", custom_id: Optional[str]
    ) -> str:
        """Reserve the next invocation ID for a submitted step.

        Args:
            step: The submitted step.
            custom_id: Optional explicit invocation ID.

        Returns:
            The reserved invocation ID.
        """
        with self._state_lock:
            invocation_id = compute_invocation_id(
                existing_invocations=self._invocation_ids,
                step=step,
                custom_id=custom_id,
                allow_suffix=not custom_id,
            )
            self._invocation_ids.add(invocation_id)

        return invocation_id

    def _create_step_config(
        self, group: Optional["GroupInfo"]
    ) -> Optional["StepConfigurationUpdate"]:
        """Create deployment or group-specific step configuration overrides.

        Args:
            group: Optional group information for the step.

        Returns:
            Optional step configuration overrides.
        """
        if self._run and self._run.triggered_by_deployment:
            return StepConfigurationUpdate(
                enable_cache=False,
                step_operator=None,
                parameters={},
                runtime=StepRuntime.INLINE,
                group=group,
            )
        elif group:
            return StepConfigurationUpdate(group=group)

        return None

    def _log_waiting_for_steps(
        self, waiting_for_steps: List[str], invocation_id: str
    ) -> None:
        """Log that a step is waiting on upstream work.

        Args:
            waiting_for_steps: The upstream invocation IDs that are in progress.
            invocation_id: The downstream invocation ID.
        """
        logger.info(
            "Waiting for step(s) `%s` to finish before executing step `%s`.",
            ", ".join(waiting_for_steps),
            invocation_id,
        )

    def _predict_step_runtime(
        self,
        step: "BaseStep",
        step_config: Optional["StepConfigurationUpdate"],
    ) -> StepRuntime:
        """Predict the runtime of a step before dispatch.

        Args:
            step: The step to predict.
            step_config: Optional step configuration overrides.

        Returns:
            The predicted runtime of the step.
        """
        config = step.configuration.model_copy(deep=True)
        if template := get_config_template(self._snapshot, step, self.pipeline):
            config = template.config.model_copy(
                update={"template": template.spec.invocation_id}
            )

        if step_config:
            config = config.model_copy(
                update=step_config.model_dump(exclude_unset=True)
            )

        return get_step_runtime(
            step_config=config,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            orchestrator=self._orchestrator,
        )

    def _resolve_step_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve already-ready dynamic step inputs.

        Args:
            inputs: The step inputs to resolve.

        Returns:
            The resolved step inputs.
        """
        return await_step_inputs(inputs)

    def _expand_map_inputs(
        self, inputs: Dict[str, Any], product: bool
    ) -> List[Dict[str, Any]]:
        """Expand mapped step inputs after dependencies are ready.

        Args:
            inputs: The concrete step inputs.
            product: Whether to create a cartesian product expansion.

        Returns:
            The expanded step input dictionaries.
        """
        return expand_mapped_inputs(inputs, product=product)

    def _get_running_upstream_steps_for_startup(
        self,
        inputs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
    ) -> List[str]:
        """Get currently running upstream step IDs without blocking.

        Args:
            inputs: The raw step inputs.
            after: Optional upstream ordering futures.

        Returns:
            The running upstream invocation IDs.
        """
        return _get_running_upstream_steps(inputs=inputs, after=after)

    def _monitoring_loop(self) -> None:
        """Monitoring loop.

        This should run in a separate thread and monitors the running steps.
        """
        monitoring_interval = handle_float_env_var(
            ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_INTERVAL, default=10.0
        )
        monitoring_delay = handle_float_env_var(
            ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY, default=0.1
        )

        while not self._shutdown_event.is_set():
            start_time = time.time()
            finished_step_runs: List[Tuple[str, "StepRunResponse"]] = []

            # Copy the steps to avoid the dictionary getting modified by
            # the main thread while we're iterating over it.
            with self._state_lock:
                monitored_step_runs = list(self._steps_to_monitor.items())

            for invocation_id, step_run in monitored_step_runs:
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
                # Store the refreshed step run
                with self._state_lock:
                    self._steps_to_monitor[invocation_id] = step_run

                db_status = step_run.status

                if infra_status is None and db_status in [
                    ExecutionStatus.INITIALIZING,
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                ]:
                    # Step is running in the DB and we have no information on
                    # the infra side, so we wait for the next
                    # monitoring interval to check again.
                    continue

                finished_step_runs.append((invocation_id, step_run))

                if db_status == ExecutionStatus.STOPPING:
                    # The step runner sets the status to STOPPING when receiving
                    # a heartbeat response that the pipeline should be stopped.
                    # We now update this status to STOPPED.
                    step_run = publish_stopped_step_run(step_run.id)
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
                elif db_status == ExecutionStatus.STOPPED:
                    if duration_string:
                        logger.info(
                            "Step `%s` stopped after %s.",
                            invocation_id,
                            duration_string,
                        )
                    else:
                        logger.info("Step `%s` stopped.", invocation_id)
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

                    if remaining_retries > 0:
                        self._retry_isolated_step(step_run=step_run)
                    else:
                        exception = self._reconstruct_step_run_exception(
                            invocation_id=invocation_id,
                            step_run=step_run,
                        )
                        with self._state_lock:
                            invocation_state = self._invocation_states.get(
                                invocation_id
                            )
                        if invocation_state is not None:
                            invocation_state.mark_failure(exception)
                            self._startup_controller.wake()
                            self._forget_invocation_state(invocation_id)
                else:
                    if step_run.status.is_successful:
                        with self._state_lock:
                            invocation_state = self._invocation_states.get(
                                invocation_id
                            )
                        if invocation_state is not None:
                            invocation_state.mark_success(step_run)
                            self._startup_controller.wake()
                            self._forget_invocation_state(invocation_id)
                        continue

                    exception = self._reconstruct_step_run_exception(
                        invocation_id=invocation_id,
                        step_run=step_run,
                    )
                    with self._state_lock:
                        invocation_state = self._invocation_states.get(
                            invocation_id
                        )
                    if invocation_state is not None:
                        invocation_state.mark_failure(exception)
                        self._startup_controller.wake()
                        self._forget_invocation_state(invocation_id)

                time.sleep(monitoring_delay)

            for invocation_id, finished_step_run in finished_step_runs:
                with self._state_lock:
                    current_step_run = self._steps_to_monitor.get(invocation_id)
                    if (
                        current_step_run
                        and current_step_run.id == finished_step_run.id
                    ):
                        self._steps_to_monitor.pop(invocation_id)

            duration = time.time() - start_time
            time_to_sleep = max(0, monitoring_interval - duration)
            self._shutdown_event.wait(timeout=time_to_sleep)

    def _maybe_stop_isolated_steps(self) -> None:
        """Maybe stop all isolated in progress steps.

        This method will only stop concurrent isolated steps if the execution
        mode is FAIL_FAST.
        """
        if (
            self._snapshot.pipeline_configuration.execution_mode
            != ExecutionMode.FAIL_FAST
        ):
            return

        logger.info("Stopping isolated steps.")

        with self._state_lock:
            step_runs_to_stop = list(self._steps_to_monitor.values())

        for step_run in step_runs_to_stop:
            try:
                self._stop_isolated_step(step_run)
            except Exception:
                logger.exception("Failed to stop step `%s`.", step_run.name)

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
                monitoring_thread = threading.Thread(
                    name="DynamicPipelineRunner-Monitoring-Loop",
                    target=lambda: context_utils.run_in_current_context(
                        self._monitoring_loop
                    ),
                    daemon=True,
                )
                monitoring_thread.start()
                if not self._run.triggered_by_deployment:
                    # Only run the init hook if the run is not triggered by
                    # a deployment, as the deployment service will have
                    # already run the init hook.
                    self._orchestrator.run_init_hook(snapshot=self._snapshot)

                try:
                    # TODO: what should be allowed as pipeline returns?
                    #  (artifacts, json serializable, anything?)
                    #  how do we show it in the UI?
                    params = self.pipeline.configuration.parameters or {}
                    self.pipeline._call_entrypoint(**params)
                    # The pipeline function finished successfully, but some
                    # steps might still be running. We now wait for all of
                    # them and raise any exceptions that occurred.
                    self.await_all_step_futures()
                except _WaitConditionPollTimeout:
                    logger.info("Pausing pipeline run `%s`.", self._run.id)
                except _WaitConditionAborted:
                    logger.info(
                        "Stopping pipeline run `%s` because a wait condition "
                        "was aborted.",
                        self._run.id,
                    )
                except Exception as e:
                    exception_info = (
                        exception_utils.collect_exception_information(
                            exception=e,
                            user_func=self.pipeline.entrypoint,
                        )
                    )
                    # TODO: this call already invalidates the token, so
                    # the steps will keep running but won't be able to
                    # report their status back to ZenML.
                    publish_failed_pipeline_run(
                        self._run.id, exception_info=exception_info
                    )
                    raise
                finally:
                    self._shutdown_event.set()

                    if not self._run.triggered_by_deployment:
                        # Only run the cleanup hook if the run is not
                        # triggered by a deployment, as the deployment
                        # service will have already run the cleanup hook.
                        self._orchestrator.run_cleanup_hook(
                            snapshot=self._snapshot
                        )

                    self._maybe_stop_isolated_steps()
                    monitoring_thread.join()
                    self._startup_controller.shutdown()
                    self._executor.shutdown(wait=True, cancel_futures=True)

                self._run = Client().zen_store.get_run(
                    self._run.id, hydrate=False
                )
                if self._run.status == ExecutionStatus.RUNNING:
                    publish_successful_pipeline_run(self._run.id)
                    logger.info("Pipeline completed successfully.")

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

        # noqa: DAR401
        Raises:
            BaseException: If the step failed.

        Returns:
            The step run outputs or a future for the step run outputs.
        """
        step = step.copy()
        step_config = self._create_step_config(group=group)
        inputs = convert_to_keyword_arguments(step.entrypoint, args, kwargs)
        invocation_id = self._reserve_invocation_id(step=step, custom_id=id)
        waiting_for_steps = _get_running_upstream_steps(inputs, after)

        if concurrent:
            return self._submit_startup_step(
                step=step,
                invocation_id=invocation_id,
                inputs=inputs,
                after=after,
                step_config=step_config,
                waiting_for_steps=waiting_for_steps,
            )

        if waiting_for_steps:
            self._log_waiting_for_steps(
                waiting_for_steps=waiting_for_steps,
                invocation_id=invocation_id,
            )

        compiled_step = compile_dynamic_step_invocation(
            snapshot=self._snapshot,
            pipeline=self.pipeline,
            step=step,
            invocation_id=invocation_id,
            inputs=inputs,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            after=after,
            config=step_config,
        )
        prepared = self._prepare_compiled_step_launch(
            invocation_id=invocation_id,
            compiled_step=compiled_step,
        )
        existing_step_result = self._maybe_handle_existing_step_run_sync(
            invocation_id=invocation_id,
            prepared=prepared,
        )
        if existing_step_result is not None:
            return existing_step_result

        step_run = self._run_sync_step(
            step=prepared.compiled_step,
            remaining_retries=prepared.remaining_retries,
        )
        return load_step_run_outputs(step_run.id)

    def _prepare_ready_step_launch(
        self,
        step: "BaseStep",
        invocation_id: str,
        inputs: Dict[str, Any],
        after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
        step_config: Optional["StepConfigurationUpdate"],
    ) -> _PreparedStepLaunch:
        """Prepare a dependency-ready invocation for dispatch.

        Args:
            step: The submitted step.
            invocation_id: The invocation ID of the step.
            inputs: The already-resolved step inputs.
            after: Optional upstream futures for ordering metadata.
            step_config: Optional step configuration overrides.

        Returns:
            The prepared launch state.
        """
        upstream_steps = _collect_upstream_steps(after=after, inputs=inputs)
        compiled_step = compile_resolved_dynamic_step_invocation(
            snapshot=self._snapshot,
            pipeline=self.pipeline,
            step=step,
            invocation_id=invocation_id,
            inputs=inputs,
            upstream_steps=upstream_steps,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            config=step_config,
        )
        return self._prepare_compiled_step_launch(
            invocation_id=invocation_id,
            compiled_step=compiled_step,
        )

    def _prepare_compiled_step_launch(
        self, invocation_id: str, compiled_step: "Step"
    ) -> _PreparedStepLaunch:
        """Prepare a compiled step launch.

        Args:
            invocation_id: The invocation ID of the step.
            compiled_step: The compiled step configuration.

        Returns:
            The prepared launch state.
        """
        step_run = self._existing_step_runs.get(invocation_id)
        runtime = get_step_runtime(
            step_config=compiled_step.config,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            orchestrator=self._orchestrator,
        )
        remaining_retries = None

        if step_run:
            old_config = step_run.config.model_copy(deep=True)
            old_config.substitutions.pop("date")
            old_config.substitutions.pop("time")

            if (
                old_config.model_dump_json()
                != compiled_step.config.model_dump_json()
            ):
                compiled_step = Step(
                    spec=step_run.spec,
                    config=old_config,
                    step_config_overrides=old_config,
                )
                logger.warning(
                    "Configuration for step `%s` changed since the the "
                    "orchestration environment was restarted. If the step "
                    "needs to be retried, it will use the old configuration.",
                    step_run.name,
                )

            if (
                runtime == StepRuntime.INLINE
                and step_run.status == ExecutionStatus.RUNNING
            ):
                step_run = publish_failed_step_run(step_run.id)

            remaining_retries = get_remaining_retries(step_run=step_run)

        return _PreparedStepLaunch(
            compiled_step=compiled_step,
            runtime=runtime,
            remaining_retries=remaining_retries,
            existing_step_run=step_run,
        )

    # TODO: when a step run exists, we need to make sure that the new cache
    # key is identical to the old one, and fail otherwise.
    def _maybe_handle_existing_step_run_sync(
        self, invocation_id: str, prepared: _PreparedStepLaunch
    ) -> Optional[StepRunOutputs]:
        """Handle reuse of an existing step run in the sync path.

        Args:
            invocation_id: The invocation ID of the step.
            prepared: The prepared launch state.

        Raises:
            BaseException: If the existing step run failed.

        Returns:
            The existing step outputs if handled, otherwise `None`.
        """
        step_run = prepared.existing_step_run
        if not step_run:
            return None

        if step_run.status.is_successful:
            return load_step_run_outputs(step_run.id)

        if step_run.status.is_failed:
            raise self._reconstruct_step_run_exception(
                invocation_id=invocation_id, step_run=step_run
            )

        if step_run.status == ExecutionStatus.RUNNING:
            logger.info(
                "Restarting the monitoring of existing step `%s` "
                "(ID: %s). Remaining retries: %d",
                step_run.name,
                step_run.id,
                prepared.remaining_retries,
            )
            with self._state_lock:
                self._steps_to_monitor[invocation_id] = step_run

            step_run = wait_for_step_to_finish(
                pipeline_run_id=self._run.id,
                step_name=invocation_id,
            )
            return load_step_run_outputs(step_run.id)

        return None

    def _maybe_handle_existing_step_run_for_startup(
        self,
        invocation_id: str,
        prepared: _PreparedStepLaunch,
        invocation_state: InvocationState,
    ) -> Optional["_StartupStatus"]:
        """Handle reuse of an existing step run before dispatch.

        Args:
            invocation_id: The invocation ID of the step.
            prepared: The prepared launch state.
            invocation_state: The shared invocation lifecycle state.

        Returns:
            The resulting startup status if handled, otherwise `None`.
        """
        step_run = prepared.existing_step_run
        if not step_run:
            return None

        if step_run.status.is_successful:
            invocation_state.mark_success(step_run)
            return _StartupStatus.FINISHED_SUCCESS

        if step_run.status.is_failed:
            invocation_state.mark_failure(
                self._reconstruct_step_run_exception(
                    invocation_id=invocation_id,
                    step_run=step_run,
                )
            )
            return _StartupStatus.FINISHED_FAILED

        if step_run.status == ExecutionStatus.RUNNING:
            logger.info(
                "Restarting the monitoring of existing step `%s` "
                "(ID: %s). Remaining retries: %d",
                step_run.name,
                step_run.id,
                prepared.remaining_retries,
            )
            with self._state_lock:
                self._steps_to_monitor[invocation_id] = step_run
            invocation_state.mark_dispatched()
            return _StartupStatus.ACTIVE_ISOLATED

        return None

    def _launch_ready_inline_step(
        self,
        step: "Step",
        invocation_state: InvocationState,
        remaining_retries: Optional[int] = None,
    ) -> Future["StepRunResponse"]:
        """Launch a dependency-ready inline step in the runner executor.

        Args:
            step: The inline step to launch.
            invocation_state: The shared invocation lifecycle state.
            remaining_retries: The remaining retry budget.

        Returns:
            The executor future of the inline execution.
        """

        def _launch_and_wait() -> StepRunResponse:
            return self._run_sync_step(
                step=step, remaining_retries=remaining_retries
            )

        executor_future = self._executor.submit(
            context_utils.run_in_current_context, _launch_and_wait
        )
        invocation_state.bind_inline_future(executor_future)
        executor_future.add_done_callback(
            lambda future: self._complete_inline_step(
                invocation_state=invocation_state,
                future=future,
            )
        )
        return executor_future

    def _complete_inline_step(
        self,
        invocation_state: InvocationState,
        future: Future["StepRunResponse"],
    ) -> None:
        """Persist the terminal inline outcome in invocation state.

        Args:
            invocation_state: The invocation state of the inline step.
            future: The executor future of the inline execution.
        """
        try:
            step_run = future.result()
        except BaseException as exception:
            invocation_state.mark_failure(exception)
        else:
            invocation_state.mark_success(step_run)

        self._startup_controller.wake()
        self._forget_invocation_state(invocation_state.invocation_id)

    def _launch_ready_isolated_step(
        self,
        step: "Step",
        invocation_state: Optional[InvocationState] = None,
    ) -> "StepRunResponse":
        """Launch a dependency-ready isolated step and start monitoring it.

        Args:
            step: The isolated step to launch.
            invocation_state: Optional shared invocation lifecycle state.

        Returns:
            The launched step run.
        """
        step_run = launch_step(
            snapshot=self._snapshot,
            step=step,
            orchestrator_run_id=self._orchestrator_run_id,
            wait=False,
            retry=False,
        )
        with self._state_lock:
            self._steps_to_monitor[step.spec.invocation_id] = step_run
        if invocation_state is not None:
            invocation_state.mark_dispatched()
        return step_run

    def _retry_isolated_step(
        self,
        step_run: "StepRunResponse",
    ) -> "StepRunResponse":
        """Retry an isolated step run.

        Args:
            step_run: The failed step run to retry.

        Returns:
            The relaunched step run.
        """
        step = Step(
            spec=step_run.spec,
            config=step_run.config,
            step_config_overrides=step_run.config,
        )
        return self._launch_ready_isolated_step(
            step=step,
        )

    def _reconstruct_step_run_exception(
        self, invocation_id: str, step_run: "StepRunResponse"
    ) -> BaseException:
        """Reconstruct the exception of a failed step run.

        Args:
            invocation_id: The invocation ID of the step.
            step_run: The failed step run.

        Returns:
            The reconstructed exception.
        """
        return exception_utils.reconstruct_exception(
            exception_info=step_run.exception_info,
            fallback_message=(
                f"Step `{invocation_id}` failed with status "
                f"`{step_run.status}`."
            ),
        )

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
        kwargs = convert_to_keyword_arguments(step.entrypoint, args, kwargs)

        # This will overwrite any user-configured groups for the step, but
        # capturing the mapping information is more important until we introduce
        # a more flexible group system.
        group_info = GroupInfo(
            id=str(uuid4()),
            name=step.name,
            type=GroupType.MAP,
        )
        expansion_future: Future[List[StepFuture]] = Future()
        map_future = MapResultsFuture(wrapped=expansion_future)
        self._startup_controller.register_map(
            step=step.copy(),
            kwargs=kwargs,
            after=after,
            product=product,
            group_info=group_info,
            expansion_future=expansion_future,
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

        if isinstance(after, BaseStepFuture):
            after.result()
        elif isinstance(after, MapResultsFuture):
            for future in after:
                future.result()
        elif isinstance(after, Sequence):
            for item in after:
                if isinstance(item, BaseStepFuture):
                    item.result()
                elif isinstance(item, MapResultsFuture):
                    for future in item:
                        future.result()

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
                while time.time() < deadline or self.has_in_progress_steps():
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

    def await_all_step_futures(self) -> None:
        """Await all step futures."""
        self._startup_controller.await_all()
        with self._state_lock:
            futures = list(self._futures.values())
        first_exception: Optional[BaseException] = None
        try:
            for future in futures:
                try:
                    future.wait()
                except BaseException as exception:
                    if first_exception is None:
                        first_exception = exception
        finally:
            with self._state_lock:
                self._futures = {}
                self._invocation_states = {}

        if first_exception is not None:
            raise first_exception

    def has_in_progress_steps(self) -> bool:
        """Check if there are any in-progress steps.

        Returns:
            True if there are any in-progress steps, False otherwise.
        """
        with self._state_lock:
            futures = list(self._futures.values())

        return self._startup_controller.has_in_progress_steps() or any(
            future.running() for future in futures
        )


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
    inputs = await_step_inputs(inputs)
    upstream_steps = _collect_upstream_steps(after=after, inputs=inputs)
    return compile_resolved_dynamic_step_invocation(
        snapshot=snapshot,
        pipeline=pipeline,
        step=step,
        invocation_id=invocation_id,
        inputs=inputs,
        upstream_steps=upstream_steps,
        pipeline_docker_settings=pipeline_docker_settings,
        config=config,
    )


def compile_resolved_dynamic_step_invocation(
    snapshot: "PipelineSnapshotResponse",
    pipeline: "DynamicPipeline",
    step: "BaseStep",
    invocation_id: str,
    inputs: Dict[str, Any],
    upstream_steps: Set[str],
    pipeline_docker_settings: "DockerSettings",
    config: Optional[StepConfigurationUpdate] = None,
) -> "Step":
    """Compile a dynamic step invocation with already-resolved inputs.

    Args:
        snapshot: The pipeline snapshot.
        pipeline: The dynamic pipeline.
        step: The step to compile.
        invocation_id: The invocation ID of the step.
        inputs: The already-resolved step inputs.
        upstream_steps: The upstream invocation IDs of the step.
        pipeline_docker_settings: The Docker settings of the parent pipeline.
        config: Optional step configuration overrides.

    Returns:
        The compiled step.
    """
    input_artifacts = {}
    external_artifacts = {}
    for name, value in inputs.items():
        if isinstance(value, OutputArtifact):
            input_artifacts[name] = [
                StepArtifact(
                    invocation_id=value.step_name,
                    output_name=value.output_name,
                    annotation=OutputSignature(resolved_annotation=Any),
                    pipeline=pipeline,
                    chunk_index=value.chunk_index,
                    chunk_size=value.chunk_size,
                )
            ]
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


def _collect_upstream_steps(
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
    inputs: Dict[str, Any],
) -> Set[str]:
    """Collect upstream invocation IDs from resolved inputs and `after`.

    Args:
        after: Optional upstream futures used for ordering.
        inputs: The already-resolved step inputs.

    Returns:
        The upstream invocation IDs of the step.
    """
    upstream_steps = set()

    if isinstance(after, BaseStepFuture):
        upstream_steps.add(after.invocation_id)
    elif isinstance(after, MapResultsFuture):
        upstream_steps.update(future.invocation_id for future in after)
    elif isinstance(after, Sequence):
        for item in after:
            if isinstance(item, BaseStepFuture):
                upstream_steps.add(item.invocation_id)
            elif isinstance(item, MapResultsFuture):
                upstream_steps.update(
                    future.invocation_id for future in item
                )

    for value in inputs.values():
        if isinstance(value, OutputArtifact):
            upstream_steps.add(value.step_name)
        elif (
            isinstance(value, Sequence)
            and value
            and all(isinstance(item, OutputArtifact) for item in value)
        ):
            upstream_steps.update(item.step_name for item in value)

    return upstream_steps


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


def _get_running_upstream_steps(
    inputs: Dict[str, Any],
    after: Union["AnyStepFuture", Sequence["AnyStepFuture"], None],
) -> List[str]:
    """Get all running upstream steps for a step.

    Args:
        inputs: The inputs of the step.
        after: The step run futures to wait for.

    Raises:
        TypeError: If an unexpected future type is passed.

    Returns:
        The list of running upstream steps.
    """
    futures: List[BaseFuture] = []

    for value in inputs.values():
        if isinstance(value, BaseFuture):
            futures.append(value)
        elif isinstance(value, Sequence) and all(
            isinstance(item, BaseFuture) for item in value
        ):
            futures.extend(value)

    if isinstance(after, BaseFuture):
        futures.append(after)
    elif isinstance(after, Sequence):
        futures.extend(after)

    steps = []

    for future in futures:
        if isinstance(future, MapResultsFuture):
            expanded_futures = future.expanded_futures()
            if expanded_futures is None:
                continue
            for item in expanded_futures:
                if item.running():
                    steps.append(item.invocation_id)
        elif isinstance(future, BaseStepFuture):
            if future.running():
                steps.append(future.invocation_id)
        else:
            raise TypeError(f"Unexpected future type: {type(future)}")

    return steps


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
