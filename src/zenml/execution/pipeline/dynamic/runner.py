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
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ContextManager,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    overload,
)
from uuid import uuid4

from zenml import ExternalArtifact
from zenml.artifacts.in_memory_cache import InMemoryArtifactCache
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.step_configurations import GroupInfo, StepConfigurationUpdate
from zenml.constants import (
    ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_DELAY,
    ENV_ZENML_DYNAMIC_PIPELINE_MONITORING_INTERVAL,
    ENV_ZENML_DYNAMIC_PIPELINE_WORKER_COUNT,
    handle_float_env_var,
    handle_int_env_var,
)
from zenml.enums import ExecutionMode, ExecutionStatus, GroupType, StepRuntime
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
from zenml.execution.pipeline.dynamic.utils import (
    _Unmapped,
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
    source_utils,
    string_utils,
)
from zenml.utils.logging_utils import (
    LoggingContext,
    is_pipeline_logging_enabled,
    setup_logging_context,
)

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.config.step_configurations import Step, StepConfiguration
    from zenml.orchestrators import BaseOrchestrator
    from zenml.steps import BaseStep


logger = get_logger(__name__)


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
        self._futures: Dict[str, "StepFuture"] = {}
        self._invocation_ids: Set[str] = set()

        self._run, self._orchestrator_run_id = self._prepare_run(run)
        self._existing_step_runs = self._run.steps

        self._steps_to_monitor: Dict[str, "StepRunResponse"] = {}
        self._shutdown_event = threading.Event()

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

        while not self._shutdown_event.is_set():
            start_time = time.time()
            finished_step_runs = []

            for invocation_id, step_run in self._steps_to_monitor.items():
                orchestrator_status: Optional[ExecutionStatus] = None
                try:
                    orchestrator_status = (
                        self._orchestrator.get_isolated_step_status(step_run)
                    )
                except Exception as e:
                    logger.error(
                        "Failed to get orchestrator status for step `%s`: %s",
                        invocation_id,
                        e,
                    )
                else:
                    logger.debug(
                        "Step `%s` orchestrator status: %s.",
                        invocation_id,
                        orchestrator_status,
                    )

                if orchestrator_status in [
                    ExecutionStatus.INITIALIZING,
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                ]:
                    # Step still running on the orchestrator side, no need to
                    # do anything here.
                    continue

                step_run = Client().get_run_step(step_run.id)
                # Store the refreshed step run
                self._steps_to_monitor[invocation_id] = step_run

                db_status = step_run.status

                if orchestrator_status is None and db_status in [
                    ExecutionStatus.INITIALIZING,
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                ]:
                    # Step is running in the DB and we have no information on
                    # the orchestrator side, so we wait for the next
                    # monitoring interval to check again.
                    continue

                finished_step_runs.append(invocation_id)

                if db_status == ExecutionStatus.STOPPING:
                    # The step runner sets the status to STOPPING when receiving
                    # a heartbeat response that the pipeline should be stopped.
                    # We now update this status to STOPPED.
                    step_run = publish_stopped_step_run(step_run.id)
                elif (
                    orchestrator_status
                    in [ExecutionStatus.FAILED, ExecutionStatus.STOPPED]
                    and db_status == ExecutionStatus.RUNNING
                ):
                    # Step failed/stopped on the orchestrator side, but the
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
                        step = Step(
                            spec=step_run.spec,
                            config=step_run.config,
                            step_config_overrides=step_run.config,
                        )
                        self._queue_concurrent_isolated_step(step=step)

                time.sleep(monitoring_delay)

            for invocation_id in finished_step_runs:
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

        if not self._orchestrator.can_stop_isolated_steps:
            logger.warning(
                "The orchestrator `%s` does not support stopping isolated "
                "steps. All in progress steps will be left running.",
                self._orchestrator.__class__.__name__,
            )
            return

        logger.info("Stopping isolated steps.")

        for invocation_id, step_run in self._steps_to_monitor.items():
            try:
                self._orchestrator.stop_isolated_step(step_run)
            except Exception:
                logger.exception("Failed to stop step `%s`.", invocation_id)

    def run_pipeline(self) -> None:
        """Run the pipeline.

        Raises:
            Exception: If the pipeline run failed.
        """
        logs_context: ContextManager[Any] = nullcontext()
        if is_pipeline_logging_enabled(self._snapshot.pipeline_configuration):
            logs_context = setup_logging_context(source="orchestrator")
        
        with logs_context:
            if self._run.status.is_finished:
                logger.info("Run `%s` is already finished.", str(self._run.id))
                return
            if self._run.status == ExecutionStatus.RUNNING:
                logger.info("Continuing existing run `%s`.", str(self._run.id))

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
                except Exception as e:
                    exception_info = exception_utils.collect_exception_information(
                        exception=e,
                        user_func=self.pipeline.entrypoint,
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
                    self._executor.shutdown(wait=True, cancel_futures=True)
                    monitoring_thread.join()

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

        Returns:
            The step run outputs or a future for the step run outputs.
        """
        step = step.copy()
        step_config = None
        if self._run and self._run.triggered_by_deployment:
            # Deployment-specific step overrides
            step_config = StepConfigurationUpdate(
                enable_cache=False,
                step_operator=None,
                parameters={},
                runtime=StepRuntime.INLINE,
                group=group,
            )
        elif group:
            step_config = StepConfigurationUpdate(
                group=group,
            )

        inputs = convert_to_keyword_arguments(step.entrypoint, args, kwargs)

        invocation_id = compute_invocation_id(
            existing_invocations=self._invocation_ids,
            step=step,
            custom_id=id,
            allow_suffix=not id,
        )
        self._invocation_ids.add(invocation_id)

        if waiting_for_steps := _get_running_upstream_steps(inputs, after):
            logger.info(
                "Waiting for step(s) `%s` to finish before executing step `%s`.",
                ", ".join(waiting_for_steps),
                invocation_id,
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

        step_run = self._existing_step_runs.get(invocation_id)
        runtime = get_step_runtime(
            step_config=compiled_step.config,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            orchestrator=self._orchestrator,
        )
        remaining_retries = None

        if step_run:
            old_config = step_run.config.model_copy(deep=True)
            # The server includes the date/time substitutions based on the
            # actual DB start time of the pipeline run. We want to compare this
            # to the newly compiled step config, so we remove them.
            old_config.substitutions.pop("date")
            old_config.substitutions.pop("time")

            if (
                old_config.model_dump_json()
                != compiled_step.config.model_dump_json()
            ):
                # We use the old config here to keep the behavior aligned across
                # all step retries: When the orchestration environment is
                # restarted while an isolated step is running, the code below
                # will start monitoring that existing execution. If that step
                # then fails, the monitoring loop will restart it with the
                # configuration of the step run that just failed, which is the
                # old (=compiled in previous orchestration environment) config.
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

            if step_run.status.is_successful:
                # The step finished successfully, but we still need to return
                # a future in case the step was launched concurrently so the
                # caller gets the correct object back.
                if concurrent:
                    return StepFuture(
                        wrapped=_IsolatedStepFuture(
                            pipeline_run_id=self._run.id,
                            invocation_id=invocation_id,
                        ),
                        output_keys=list(compiled_step.config.outputs),
                    )
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

            remaining_retries = get_remaining_retries(step_run=step_run)

            if step_run.status == ExecutionStatus.RUNNING:
                logger.info(
                    "Restarting the monitoring of existing step `%s` "
                    "(ID: %s). Remaining retries: %d",
                    step_run.name,
                    step_run.id,
                    remaining_retries,
                )
                self._steps_to_monitor[invocation_id] = step_run
                monitoring_future = StepFuture(
                    wrapped=_IsolatedStepFuture(
                        pipeline_run_id=self._run.id,
                        invocation_id=invocation_id,
                    ),
                    output_keys=list(compiled_step.config.outputs),
                )
                self._futures[invocation_id] = monitoring_future
                return monitoring_future

        if not concurrent:
            step_run = self._run_sync_step(
                step=compiled_step, remaining_retries=remaining_retries
            )
            return load_step_run_outputs(step_run.id)
        elif runtime == StepRuntime.INLINE:
            return self._queue_concurrent_inline_step(
                step=compiled_step, remaining_retries=remaining_retries
            )
        else:
            return self._queue_concurrent_isolated_step(step=compiled_step)

    def _queue_concurrent_isolated_step(self, step: "Step") -> StepFuture:
        """Queue a concurrent isolated step.

        Args:
            step: The step to queue.

        Returns:
            The step future.
        """

        def _launch_no_wait() -> StepRunResponse:
            uses_step_operator = bool(step.config.step_operator)

            step_run = launch_step(
                snapshot=self._snapshot,
                step=step,
                orchestrator_run_id=self._orchestrator_run_id,
                # - Retry if the step uses a step operator
                # - When running isolated steps using the orchestrator, the
                #   monitoring loop is responsible for retrying failed steps.
                retry=uses_step_operator,
                # Step operators only support sync execution right now -> We
                # wait for the step to finish synchronously.
                wait=uses_step_operator,
            )

            if not uses_step_operator:
                # Only monitor isolated steps using the orchestrator in the
                # monitoring loop.
                self._steps_to_monitor[step.spec.invocation_id] = step_run

            return step_run

        concurrent_future = self._executor.submit(
            context_utils.run_in_current_context, _launch_no_wait
        )
        future = StepFuture(
            wrapped=_IsolatedStepFuture(
                wrapped=concurrent_future,
                pipeline_run_id=self._run.id,
                invocation_id=step.spec.invocation_id,
            ),
            output_keys=list(step.config.outputs),
        )
        self._futures[step.spec.invocation_id] = future
        return future

    def _queue_concurrent_inline_step(
        self, step: "Step", remaining_retries: Optional[int] = None
    ) -> StepFuture:
        """Queue a concurrent inline step.

        Args:
            step: The step to queue.
            remaining_retries: The remaining retries for the step.

        Returns:
            The step future.
        """

        def _launch_and_wait() -> StepRunResponse:
            return self._run_sync_step(
                step=step, remaining_retries=remaining_retries
            )

        concurrent_future = self._executor.submit(
            context_utils.run_in_current_context, _launch_and_wait
        )
        future = StepFuture(
            wrapped=_InlineStepFuture(
                wrapped=concurrent_future,
                invocation_id=step.spec.invocation_id,
            ),
            output_keys=list(step.config.outputs),
        )
        self._futures[step.spec.invocation_id] = future
        return future

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
            retry=True,
            remaining_retries=remaining_retries,
            wait=True,
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
        kwargs = await_step_inputs(kwargs)
        step_inputs = expand_mapped_inputs(kwargs, product=product)

        # This will overwrite any user-configured groups for the step, but
        # capturing the mapping information is more important until we introduce
        # a more flexible group system.
        group_info = GroupInfo(
            id=str(uuid4()),
            name=step.name,
            type=GroupType.MAP,
        )

        step_futures = [
            self.launch_step(
                step,
                id=None,
                args=(),
                kwargs=inputs,
                after=after,
                group=group_info,
                concurrent=True,
            )
            for inputs in step_inputs
        ]

        return MapResultsFuture(futures=step_futures)

    def await_all_step_futures(self) -> None:
        """Await all step futures."""
        for future in self._futures.values():
            future.wait()
        self._futures = {}


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

    if isinstance(after, BaseStepFuture):
        after.result()
        upstream_steps.add(after.invocation_id)
    elif isinstance(after, MapResultsFuture):
        for future in after:
            future.result()
            upstream_steps.add(future.invocation_id)
    elif isinstance(after, Sequence):
        for item in after:
            if isinstance(item, BaseStepFuture):
                item.result()
                upstream_steps.add(item.invocation_id)
            elif isinstance(item, MapResultsFuture):
                for future in item:
                    future.result()
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

    default_parameters = {
        key: value
        for key, value in convert_to_keyword_arguments(
            step.entrypoint, (), inputs, apply_defaults=True
        ).items()
        if key not in inputs
    }

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
            # TODO: should some of these be parameters?
            external_artifacts[name] = ExternalArtifact(value=value)

    if template := get_config_template(snapshot, step, pipeline):
        step._configuration = template.config.model_copy(
            update={"template": template.spec.invocation_id}
        )

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
            for item in future.futures:
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
