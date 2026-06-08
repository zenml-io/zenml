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
"""Class to launch (run directly or using a step operator) steps."""

import inspect
import time
from contextlib import nullcontext
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ContextManager,
    Dict,
    List,
    Optional,
    Tuple,
)

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.constants import (
    ENV_ZENML_STEP_OPERATOR,
)
from zenml.enums import (
    ExecutionStatus,
    ResourceRequestStatus,
    StepRuntime,
)
from zenml.environment import get_run_environment_dict
from zenml.exceptions import RunStoppedException
from zenml.execution.context import ExecutionContext, record_step_run
from zenml.logger import get_logger
from zenml.models import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineSnapshotResponse,
    ResourceRequestRenewalRequest,
    ResourceRequestResponse,
    StepRunResponse,
)
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators import output_utils, publish_utils, step_run_utils
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.signal_handler import SignalHandler
from zenml.orchestrators.step_runner import StepRunner
from zenml.stack import Stack
from zenml.steps import StepHeartBeatTerminationException
from zenml.steps.heartbeat import StepHeartbeatWorker
from zenml.utils import env_utils, exception_utils, string_utils
from zenml.utils.logging_utils import (
    LoggingContext,
    is_step_logging_enabled,
    setup_logging_context,
)
from zenml.utils.time_utils import exponential_backoff_delays, utc_now

if TYPE_CHECKING:
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


def _call_with_optional_allocated_resource_request(
    method: Callable[..., Any],
    allocated_resource_request: Optional["ResourceRequestResponse"],
    **kwargs: Any,
) -> Any:
    """Call a method with the allocation keyword when it is supported."""
    parameters = inspect.signature(method).parameters
    if "allocated_resource_request" in parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        kwargs["allocated_resource_request"] = allocated_resource_request

    return method(**kwargs)


def _get_step_operator(
    stack: "Stack", step_operator_name: Optional[str]
) -> "BaseStepOperator":
    """Fetches the step operator from the stack.

    Args:
        stack: Stack on which the step is being run.
        step_operator_name: Name of the step operator to get.

    Returns:
        The step operator to run a step.

    Raises:
        RuntimeError: If no active step operator is found.
    """
    if step_operator_name is None:
        step_operator = stack.step_operator
        if step_operator is None:
            raise RuntimeError(
                f"No step operators specified for active stack '{stack.name}'."
            )
        return step_operator

    step_operator = stack.step_operators.get(step_operator_name)
    if step_operator is None:
        raise RuntimeError(
            f"No step operator named '{step_operator_name}' found in active "
            f"stack '{stack.name}'. Available step operators: {list(stack.step_operators)}."
        )

    return step_operator


class StepLauncher:
    """A class responsible for launching a step of a ZenML pipeline.

    This class follows these steps to launch and publish a ZenML step:
    1. Publish or reuse a `PipelineRun`
    2. Resolve the input artifacts of the step
    3. Generate a cache key for the step
    4. Check if the step can be cached or not
    5. Publish a new `StepRun`
    6. If the step can't be cached, the step will be executed in one of these
    two ways depending on its configuration:
        - Calling a `step operator` to run the step in a different environment
        - Calling a `step runner` to run the step in the current environment
    7. Update the status of the previously published `StepRun`
    8. Update the status of the `PipelineRun`
    """

    def __init__(
        self,
        snapshot: PipelineSnapshotResponse,
        step: Step,
        orchestrator_run_id: str,
        wait: bool = True,
    ):
        """Initializes the launcher.

        Args:
            snapshot: The pipeline snapshot.
            step: The step to launch.
            orchestrator_run_id: The orchestrator pipeline run id.
            wait: Whether to wait for the step to finish.

        Raises:
            RuntimeError: If the snapshot has no associated stack.
        """
        self._snapshot = snapshot
        self._step = step
        self._orchestrator_run_id = orchestrator_run_id
        self._wait = wait

        if not snapshot.stack:
            raise RuntimeError(
                f"Missing stack for snapshot {snapshot.id}. This is "
                "probably because the stack was manually deleted."
            )

        self._stack = Stack.from_model(snapshot.stack)
        self._invocation_id = step.spec.invocation_id

        # Internal properties and methods
        self._step_run: Optional[StepRunResponse] = None

    def launch(self) -> StepRunResponse:
        """Launches the step.

        Raises:
            RunStoppedException: If the pipeline run is stopped by the user.
            BaseException: If the step preparation or execution fails.
            RuntimeError: If an unexpected step run status is encountered.

        Returns:
            The step run response.
        """
        publish_utils.step_exception_info.set(None)

        logs_context: ContextManager[Any] = nullcontext()

        if is_step_logging_enabled(
            step_configuration=self._step.config,
            pipeline_configuration=self._snapshot.pipeline_configuration,
        ):
            logs_context = setup_logging_context(source="prepare_step")

        with logs_context:
            pipeline_run, run_was_created = self._create_or_reuse_run()

            if isinstance(logs_context, LoggingContext):
                logs_context.update(pipeline_run=pipeline_run)

            if run_was_created:
                pipeline_run_metadata = self._stack.get_pipeline_run_metadata(
                    run_id=pipeline_run.id
                )
                publish_utils.publish_pipeline_run_metadata(
                    pipeline_run_id=pipeline_run.id,
                    pipeline_run_metadata=pipeline_run_metadata,
                )
                if model_version := pipeline_run.model_version:
                    step_run_utils.log_model_version_dashboard_url(
                        model_version=model_version
                    )

            request_factory = step_run_utils.StepRunRequestFactory(
                snapshot=self._snapshot,
                pipeline_run=pipeline_run,
                stack=self._stack,
            )
            dynamic_config = self._step if self._snapshot.is_dynamic else None
            step_run_request = request_factory.create_request(
                invocation_id=self._invocation_id,
                dynamic_config=dynamic_config,
            )
            step_run_request.status = self._get_initial_step_run_status()
            if isinstance(logs_context, LoggingContext):
                step_run_request.logs = logs_context.log_model.id

            try:
                request_factory.populate_request(request=step_run_request)
            except BaseException as e:
                logger.exception(
                    f"Failed preparing step `{self._invocation_id}`."
                )
                step_run_request.status = ExecutionStatus.FAILED
                step_run_request.end_time = utc_now()
                step_run_request.exception_info = (
                    exception_utils.collect_exception_information(e)
                )
                raise
            finally:
                step_run = Client().zen_store.create_run_step(step_run_request)

                if isinstance(logs_context, LoggingContext):
                    logs_context.update(step_run=step_run)

                self._step_run = step_run
                if model_version := step_run.model_version:
                    step_run_utils.log_model_version_dashboard_url(
                        model_version=model_version
                    )

                if not step_run.status.is_finished:
                    logger.info(f"Step `{self._invocation_id}` has started.")

                    signal_handler: Optional[SignalHandler] = None
                    start_time = time.time()
                    try:
                        if self._should_register_signal_handler():
                            signal_handler = SignalHandler(
                                step_run=step_run,
                                execution_mode=self._snapshot.pipeline_configuration.execution_mode,
                            )
                            signal_handler.register()

                        if terminal_step_run := self._run_step(
                            pipeline_run=pipeline_run,
                            step_run=step_run,
                            force_write_logs=lambda: None,
                        ):
                            step_run = terminal_step_run
                    except RunStoppedException as e:
                        raise e
                    except BaseException as e:  # noqa: E722
                        step_run = Client().get_run_step(
                            step_run_id=step_run.id
                        )

                        if step_run.status == ExecutionStatus.CANCELLING:
                            publish_utils.publish_cancelled_step_run(
                                step_run_id=step_run.id
                            )
                        elif (
                            isinstance(e, StepHeartBeatTerminationException)
                            or step_run.status == ExecutionStatus.STOPPING
                        ):
                            # Handle as a non-failure as exception is a propagation of graceful termination.
                            publish_utils.publish_stopped_step_run(step_run.id)

                        else:
                            logger.error(
                                "Failed to run step `%s`: %s",
                                self._invocation_id,
                                e,
                            )
                            if step_run.status in {
                                ExecutionStatus.PROVISIONING,
                                ExecutionStatus.RUNNING,
                                ExecutionStatus.QUEUED,
                            }:
                                # Only update the status if the step runner
                                # somehow failed to do so.
                                publish_utils.publish_failed_step_run(
                                    step_run.id
                                )
                        raise
                    finally:
                        if signal_handler:
                            signal_handler.unregister()

                    if self._wait:
                        duration = time.time() - start_time
                        logger.info(
                            f"Step `{self._invocation_id}` has finished in "
                            f"`{string_utils.get_human_readable_time(duration)}`."
                        )
                    else:
                        logger.info("Step `%s` launched.", self._invocation_id)
                elif step_run.status == ExecutionStatus.CACHED:
                    logger.info(
                        f"Using cached version of step `{self._invocation_id}`."
                    )
                    if (
                        model_version := step_run.model_version
                        or pipeline_run.model_version
                    ):
                        step_run_utils.link_output_artifacts_to_model_version(
                            artifacts=step_run.outputs,
                            model_version=model_version,
                        )
                elif step_run.status == ExecutionStatus.SKIPPED:
                    logger.info("Skipping step `%s`.", self._invocation_id)
                    if (
                        model_version := step_run.model_version
                        or pipeline_run.model_version
                    ):
                        step_run_utils.link_output_artifacts_to_model_version(
                            artifacts=step_run.outputs,
                            model_version=model_version,
                        )
                elif step_run.status == ExecutionStatus.FAILED:
                    # No need to link anything for a failed step run.
                    pass
                else:
                    raise RuntimeError(
                        f"Unexpected step run status `{step_run.status}` for "
                        f"step `{self._invocation_id}`."
                    )

        record_step_run(step_run)

        return step_run

    def _create_or_reuse_run(self) -> Tuple[PipelineRunResponse, bool]:
        """Creates a pipeline run or reuses an existing one.

        Returns:
            The created or existing pipeline run,
            and a boolean indicating whether the run was created or reused.
        """
        execution_context = ExecutionContext.get()
        if execution_context and execution_context.pipeline_run:
            return execution_context.pipeline_run, False

        start_time = utc_now()
        run_name = string_utils.format_name_template(
            name_template=self._snapshot.run_name_template,
            substitutions=self._snapshot.pipeline_configuration.finalize_substitutions(
                start_time=start_time,
            ),
        )

        logger.debug("Creating pipeline run %s", run_name)

        client = Client()
        pipeline_run_request = PipelineRunRequest(
            name=run_name,
            orchestrator_run_id=self._orchestrator_run_id,
            project=client.active_project.id,
            snapshot=self._snapshot.id,
            status=ExecutionStatus.RUNNING,
            orchestrator_environment=get_run_environment_dict(),
            start_time=start_time,
            tags=self._snapshot.pipeline_configuration.tags,
        )
        pipeline_run, run_was_created = client.zen_store.get_or_create_run(
            pipeline_run_request
        )
        if execution_context:
            execution_context.pipeline_run = pipeline_run

        return pipeline_run, run_was_created

    def _run_step(
        self,
        pipeline_run: PipelineRunResponse,
        step_run: StepRunResponse,
        force_write_logs: Callable[..., Any],
    ) -> Optional[StepRunResponse]:
        """Runs the current step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            force_write_logs: The context for the step logs.

        Returns:
            The terminal step run if available, None otherwise.
        """  # noqa: DOC501
        from zenml.deployers.server import runtime

        step_run_info = StepRunInfo(
            step_run=step_run,
            config=self._step.config,
            spec=self._step.spec,
            pipeline=self._snapshot.pipeline_configuration,
            run_name=pipeline_run.name,
            pipeline_step_name=self._invocation_id,
            run_id=pipeline_run.id,
            step_run_id=step_run.id,
            force_write_logs=force_write_logs,
            snapshot=self._snapshot,
        )

        output_artifact_uris = output_utils.prepare_output_artifact_uris(
            step_run=step_run,
            stack=self._stack,
            step=self._step,
            skip_artifact_materialization=runtime.should_skip_artifact_materialization(),
        )

        allocated_resource_request: Optional[ResourceRequestResponse] = None
        if self._snapshot.is_dynamic:
            allocated_resource_request = self._wait_until_resources_acquired(
                step_run_info
            )

        terminal_step_run = None
        try:
            if self._step.config.step_operator:
                step_operator_name = None
                if isinstance(self._step.config.step_operator, str):
                    step_operator_name = self._step.config.step_operator

                terminal_step_run = self._run_step_with_step_operator(
                    step_operator_name=step_operator_name,
                    step_run_info=step_run_info,
                    allocated_resource_request=allocated_resource_request,
                )
            elif not self._snapshot.is_dynamic:
                terminal_step_run = self._run_step_in_current_thread(
                    pipeline_run=pipeline_run,
                    step_run=step_run,
                    step_run_info=step_run_info,
                    input_artifacts=step_run.regular_inputs,
                    output_artifact_uris=output_artifact_uris,
                )
            else:
                from zenml.execution.pipeline.dynamic.compilation import (
                    get_step_runtime,
                )

                step_runtime = get_step_runtime(
                    step_config=self._step.config,
                    pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
                    orchestrator=self._stack.orchestrator,
                )

                if step_runtime == StepRuntime.INLINE:
                    if self._step.config.runtime == StepRuntime.ISOLATED:
                        # The step was configured to run in an isolated runtime,
                        # but the orchestrator doesn't support it.
                        logger.warning(
                            "The %s does not support running steps "
                            "in isolated runtimes. Running step `%s` in inline "
                            "runtime instead.",
                            self._stack.orchestrator.__class__.__name__,
                            self._invocation_id,
                        )

                    terminal_step_run = self._run_step_in_current_thread(
                        pipeline_run=pipeline_run,
                        step_run=step_run,
                        step_run_info=step_run_info,
                        input_artifacts=step_run.regular_inputs,
                        output_artifact_uris=output_artifact_uris,
                    )
                else:
                    terminal_step_run = self._run_step_with_dynamic_orchestrator(
                        step_run_info=step_run_info,
                        allocated_resource_request=allocated_resource_request,
                    )
        except:  # noqa: E722
            output_utils.remove_artifact_dirs(
                artifact_uris=list(output_artifact_uris.values())
            )
            raise

        return terminal_step_run

    def _run_step_with_step_operator(
        self,
        step_operator_name: Optional[str],
        step_run_info: StepRunInfo,
        allocated_resource_request: Optional[ResourceRequestResponse],
    ) -> Optional[StepRunResponse]:
        """Runs the current step with a step operator.

        Args:
            step_operator_name: The name of the step operator to use.
            step_run_info: Additional information needed to run the step.
            allocated_resource_request: The allocated resource request for the
                step, if any.

        Raises:
            RuntimeError: If trying to use a step operator that does not support
                running asynchronously in a dynamic pipeline.
            NotImplementedError: If the step operator does not implement the
                `submit(...)` or `launch(...)` methods.
            BaseException: If the step run failed.

        Returns:
            The terminal step run if available, None otherwise.
        """  # noqa: DOC502, DOC503
        step_operator = _get_step_operator(
            stack=self._stack,
            step_operator_name=step_operator_name,
        )

        command, args = orchestrator_utils.get_step_entrypoint_command(
            invocation_id=self._invocation_id,
            config=self._step.config,
            entrypoint_config_class=step_operator.entrypoint_config_class,
            snapshot_id=self._snapshot.id,
            step_run_id=str(step_run_info.step_run_id),
        )
        entrypoint_command = command + args
        environment, secrets = orchestrator_utils.get_config_environment_vars(
            pipeline_run_id=step_run_info.run_id,
        )
        # TODO: for now, we don't support separate secrets from environment
        # in the step operator environment
        environment.update(secrets)

        environment.update(
            env_utils.get_runtime_environment(
                config=step_run_info.config,
                stack=self._stack,
            )
        )
        environment[ENV_ZENML_STEP_OPERATOR] = "True"
        logger.info(
            "Using step operator `%s` to run step `%s`.",
            step_operator.name,
            self._invocation_id,
        )

        try:
            _call_with_optional_allocated_resource_request(
                step_operator.submit,
                allocated_resource_request=allocated_resource_request,
                info=step_run_info,
                entrypoint_command=entrypoint_command,
                environment=environment,
            )
        except NotImplementedError:
            if not self._wait:
                # We're running in a dynamic pipeline and for the monitoring to
                # work correctly, we only allow running with step operators that
                # support running asynchronously.
                raise RuntimeError(
                    f"The step operator `{step_operator.name}` does not "
                    "support running asynchronously and therefore cannot be "
                    "used in dynamic pipelines. To solve this, please "
                    "implement the `submit(...)` and `get_status(...)` methods "
                    "in the step operator class."
                )

            if hasattr(step_operator, "launch") and callable(
                step_operator.launch
            ):
                # We fallback to the legacy launch method if it is implemented.
                # The launch method is synchronous and will block until the step
                # run is finished, so there is no need to wait for it.
                logger.debug(
                    "Falling back to the legacy launch method for "
                    "step operator `%s`.",
                    step_operator.name,
                )
                try:
                    _call_with_optional_allocated_resource_request(
                        step_operator.launch,
                        allocated_resource_request=allocated_resource_request,
                        info=step_run_info,
                        entrypoint_command=entrypoint_command,
                        environment=environment,
                    )
                finally:
                    try:
                        step_operator.cleanup_step_submission(
                            step_run_info.step_run
                        )
                    except Exception:
                        logger.exception(
                            "Failed to clean up for step `%s`.",
                            self._invocation_id,
                        )
            else:
                raise NotImplementedError(
                    f"The step operator `{step_operator.name}` does not "
                    "implement the `submit(...)` or `launch(...)` methods."
                )
        else:
            # We submitted the step run asynchronously, now we potentially need
            # to wait for it to finish.
            if self._wait:
                try:
                    status = step_operator.wait(
                        step_run=step_run_info.step_run,
                    )
                    return self._finalize_remote_step(
                        status=status, step_run_info=step_run_info
                    )
                finally:
                    self._cleanup_remote_step(step_run_info.step_run)

        return None

    def _run_step_with_dynamic_orchestrator(
        self,
        step_run_info: StepRunInfo,
        allocated_resource_request: Optional[ResourceRequestResponse],
    ) -> Optional[StepRunResponse]:
        """Runs the current step with a dynamic orchestrator.

        Args:
            step_run_info: Additional information needed to run the step.
            allocated_resource_request: The allocated resource request for the
                step, if any.

        Raises:
            BaseException: If the step run failed.

        Returns:
            The terminal step run if available, None otherwise.
        """  # noqa: DOC502, DOC503
        # If we don't pass the run ID here, does it reuse the existing token?
        environment, secrets = orchestrator_utils.get_config_environment_vars(
            pipeline_run_id=step_run_info.run_id,
        )
        environment.update(secrets)

        environment.update(
            env_utils.get_runtime_environment(
                config=step_run_info.config,
                stack=self._stack,
            )
        )
        _call_with_optional_allocated_resource_request(
            self._stack.orchestrator.submit_isolated_step,
            allocated_resource_request=allocated_resource_request,
            step_run_info=step_run_info,
            environment=environment,
        )
        if self._wait:
            try:
                status = self._stack.orchestrator.wait_for_isolated_step(
                    step_run_info.step_run
                )
                return self._finalize_remote_step(
                    status=status, step_run_info=step_run_info
                )
            finally:
                self._cleanup_remote_step(step_run_info.step_run)

        return None

    def _finalize_remote_step(
        self, status: ExecutionStatus, step_run_info: StepRunInfo
    ) -> Optional[StepRunResponse]:
        """Finalizes a step that was executed in a remote environment.

        Args:
            status: The status reported by the remote environment.
            step_run_info: Additional information needed to run the step.

        Raises:
            BaseException: If the step run failed.

        Returns:
            The terminal step run if available, None otherwise.
        """  # noqa: DOC502, DOC503
        if not status.is_successful:
            step_run = Client().get_run_step(step_run_info.step_run_id)
            raise exception_utils.reconstruct_exception(
                exception_info=step_run.exception_info,
                fallback_message=(
                    f"Step `{step_run_info.pipeline_step_name}` failed "
                    f"with status `{status}`."
                ),
            )

        if self._step.config.command is not None:
            # Nothing in the execution environment publishes the status for
            # a command step, so we do it here.
            return publish_utils.publish_successful_step_run(
                step_run_id=step_run_info.step_run_id,
                output_artifact_ids={},
            )

        return None

    def _cleanup_remote_step(self, step_run: StepRunResponse) -> None:
        """Clean up infrastructure after a remote step has finished.

        Args:
            step_run: The finished step run.
        """
        try:
            if self._step.config.step_operator:
                step_operator_name = (
                    self._step.config.step_operator
                    if isinstance(self._step.config.step_operator, str)
                    else None
                )
                step_operator = _get_step_operator(
                    stack=self._stack,
                    step_operator_name=step_operator_name,
                )
                step_operator.cleanup_step_submission(step_run)
            else:
                self._stack.orchestrator.cleanup_isolated_step(step_run)
        except Exception:
            logger.exception(
                "Failed to clean up for step `%s`.",
                self._invocation_id,
            )

    def _run_step_in_current_thread(
        self,
        pipeline_run: PipelineRunResponse,
        step_run: StepRunResponse,
        step_run_info: StepRunInfo,
        input_artifacts: Dict[str, List["StepRunInputResponse"]],
        output_artifact_uris: Dict[str, str],
    ) -> StepRunResponse:
        """Runs the current step without a step operator.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            step_run_info: Additional information needed to run the step.
            input_artifacts: The input artifact versions of the current step.
            output_artifact_uris: The output artifact URIs of the current step.

        Returns:
            The updated step run.
        """
        runner = StepRunner(step=self._step, stack=self._stack)
        return runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )

    def _should_register_signal_handler(self) -> bool:
        """Whether the signal handler should be registered.

        Returns:
            Whether the signal handler should be registered.
        """
        if not self._snapshot.is_dynamic:
            # In static pipelines we always register the signal handler.
            return True

        if self._step.config.step_operator:
            return False

        from zenml.execution.pipeline.dynamic.compilation import (
            get_step_runtime,
        )

        step_runtime = get_step_runtime(
            step_config=self._step.config,
            pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
            orchestrator=self._stack.orchestrator,
        )
        return step_runtime == StepRuntime.INLINE

    def _get_initial_step_run_status(self) -> ExecutionStatus:
        """Gets the initial status of the step run.

        Returns:
            The initial status of the step run.
        """
        if self._snapshot.is_dynamic:
            from zenml.execution.pipeline.dynamic.compilation import (
                get_step_runtime,
            )

            if self._step.config.command is not None:
                # Command steps can't report themselves as running once the
                # container started, so we start them in a running state.
                # Once we extend all orchestrator/step operator implementations
                # to distinguish between the provisioning and running states,
                # we can remove this special case.
                return ExecutionStatus.RUNNING

            step_runtime = get_step_runtime(
                step_config=self._step.config,
                pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
                orchestrator=self._stack.orchestrator,
            )
            if step_runtime == StepRuntime.ISOLATED:
                return ExecutionStatus.PROVISIONING

        return ExecutionStatus.RUNNING

    def _wait_until_resources_acquired(
        self, step_run_info: StepRunInfo
    ) -> Optional[ResourceRequestResponse]:
        """Waits until the resources are acquired.

        Args:
            step_run_info: Step run information.

        Returns:
            The allocated resource request response, if the step has one.

        Raises:
            RuntimeError: If the resource request was not found, or
                was rejected, preempted, or cancelled.
        """
        resource_request_id = step_run_info.step_run.resource_request_id
        resource_request = step_run_info.step_run.resource_request
        if not resource_request_id:
            if resource_request is None:
                return None
            resource_request_id = resource_request.id
        elif (
            resource_request is not None
            and resource_request.id != resource_request_id
        ):
            resource_request = None

        step_name = step_run_info.pipeline_step_name
        zen_store = Client().zen_store
        resource_settings = step_run_info.config.resource_settings
        allocation_wait_timeout = timedelta(
            seconds=resource_settings.allocation_wait_timeout_seconds
        )
        initialization_lease = timedelta(
            seconds=resource_settings.initialization_lease_seconds
        )
        wait_started_at = utc_now()

        for delay in exponential_backoff_delays(
            initial_delay=1.0,
            max_delay=20.0,
            factor=2.0,
            jitter="equal",
        ):
            if utc_now() - wait_started_at >= allocation_wait_timeout:
                raise RuntimeError(
                    f"Timed out after {resource_settings.allocation_wait_timeout_seconds} "
                    f"seconds waiting for resource request `{resource_request_id}` "
                    f"for step `{step_name}` to be allocated. Increase "
                    f"`ResourceSettings.allocation_wait_timeout_seconds` on this "
                    "step to wait longer."
                )

            if resource_request is None:
                try:
                    resource_request = zen_store.renew_resource_request(
                        resource_request_id,
                        ResourceRequestRenewalRequest(
                            lease_expires_at=(
                                StepHeartbeatWorker.resource_request_lease_expires_at()
                                + timedelta(seconds=delay)
                            ),
                        ),
                    )
                except KeyError as e:
                    raise RuntimeError(
                        f"Resource request `{resource_request_id}` for step "
                        f"`{step_name}` not found. This is most likely because "
                        "someone deleted the resource request."
                    ) from e

            if resource_request.status == ResourceRequestStatus.ALLOCATED:
                resource_request = zen_store.renew_resource_request(
                    resource_request_id,
                    ResourceRequestRenewalRequest(
                        lease_expires_at=utc_now() + initialization_lease,
                    ),
                )
                logger.info(
                    "Resource request `%s` for step `%s` was approved.",
                    resource_request.id,
                    step_name,
                )
                publish_utils.publish_step_run_status_update(
                    step_run_id=step_run_info.step_run_id,
                    status=ExecutionStatus.RUNNING,
                )
                return resource_request
            if resource_request.status == ResourceRequestStatus.REJECTED:
                reason = resource_request.status_reason or "Unknown reason"
                raise RuntimeError(
                    f"Resource request `{resource_request.id}` for step "
                    f"`{step_name}` was rejected: {reason}"
                )
            if resource_request.status in {
                ResourceRequestStatus.PREEMPTING,
                ResourceRequestStatus.PREEMPTED,
                ResourceRequestStatus.RELEASED,
                ResourceRequestStatus.EXPIRED,
            }:
                reason = resource_request.status_reason or "Unknown reason"
                raise RuntimeError(
                    f"Resource request `{resource_request.id}` for step "
                    f"`{step_name}` reached status "
                    f"`{resource_request.status}`: {reason}"
                )
            if resource_request.status == ResourceRequestStatus.CANCELLED:
                reason = resource_request.status_reason or "Unknown reason"
                raise RuntimeError(
                    f"Resource request `{resource_request.id}` for step "
                    f"`{step_name}` was cancelled: {reason}"
                )

            logger.info(
                "Waiting for resource request `%s` of step `%s` to be "
                "approved...",
                resource_request.id,
                step_name,
            )
            time.sleep(delay)
            resource_request = None
