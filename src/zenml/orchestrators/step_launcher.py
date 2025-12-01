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

import signal
import time
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.constants import (
    ENV_ZENML_DISABLE_STEP_LOGS_STORAGE,
    ENV_ZENML_STEP_OPERATOR,
    handle_bool_env_var,
)
from zenml.enums import ExecutionMode, ExecutionStatus, StepRuntime
from zenml.environment import get_run_environment_dict
from zenml.exceptions import RunInterruptedException, RunStoppedException
from zenml.logger import get_logger
from zenml.logging import step_logging
from zenml.models import (
    LogsRequest,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineSnapshotResponse,
    StepRunResponse,
)
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators import output_utils, publish_utils, step_run_utils
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.step_runner import StepRunner
from zenml.stack import Stack
from zenml.utils import env_utils, exception_utils, string_utils
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


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
    step_operator = stack.step_operator

    # the two following errors should never happen as the stack gets
    # validated before running the pipeline
    if not step_operator:
        raise RuntimeError(
            f"No step operator specified for active stack '{stack.name}'."
        )

    if step_operator_name and step_operator_name != step_operator.name:
        raise RuntimeError(
            f"No step operator named '{step_operator_name}' in active "
            f"stack '{stack.name}'."
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
    ):
        """Initializes the launcher.

        Args:
            snapshot: The pipeline snapshot.
            step: The step to launch.
            orchestrator_run_id: The orchestrator pipeline run id.

        Raises:
            RuntimeError: If the snapshot has no associated stack.
        """
        self._snapshot = snapshot
        self._step = step
        self._orchestrator_run_id = orchestrator_run_id

        if not snapshot.stack:
            raise RuntimeError(
                f"Missing stack for snapshot {snapshot.id}. This is "
                "probably because the stack was manually deleted."
            )

        self._stack = Stack.from_model(snapshot.stack)
        self._invocation_id = step.spec.invocation_id

        # Internal properties and methods
        self._step_run: Optional[StepRunResponse] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown, chaining previous handlers."""
        try:
            # Save previous handlers
            self._prev_sigterm_handler = signal.getsignal(signal.SIGTERM)
            self._prev_sigint_handler = signal.getsignal(signal.SIGINT)
        except ValueError as e:
            # This happens when not in the main thread
            logger.debug(f"Cannot set up signal handlers: {e}")
            self._prev_sigterm_handler = None
            self._prev_sigint_handler = None
            return

        def signal_handler(signum: int, frame: Any) -> None:
            """Handle shutdown signals gracefully.

            Args:
                signum: The signal number.
                frame: The frame of the signal handler.

            Raises:
                RunStoppedException: If the pipeline run is stopped by the user.
                RunInterruptedException: If the execution is interrupted for any
                    other reason.
            """
            logger.info(
                f"Received signal shutdown {signum}. Requesting shutdown "
                f"for step '{self._invocation_id}'..."
            )

            try:
                client = Client()

                if self._step_run:
                    pipeline_run = client.get_pipeline_run(
                        self._step_run.pipeline_run_id, hydrate=False
                    )
                else:
                    raise RunInterruptedException(
                        "The execution was interrupted and the step does not "
                        "exist yet."
                    )

                if pipeline_run and pipeline_run.status in [
                    ExecutionStatus.STOPPING,
                    ExecutionStatus.STOPPED,
                ]:
                    if self._step_run:
                        publish_utils.publish_step_run_status_update(
                            step_run_id=self._step_run.id,
                            status=ExecutionStatus.STOPPED,
                            end_time=utc_now(),
                        )
                    raise RunStoppedException("Pipeline run is stopped.")

                step_run = client.get_run_step(
                    self._step_run.id, hydrate=False
                )

                if (
                    pipeline_run.status == ExecutionStatus.FAILED
                    and step_run.status == ExecutionStatus.RUNNING
                    and self._snapshot.pipeline_configuration.execution_mode
                    == ExecutionMode.FAIL_FAST
                ):
                    publish_utils.publish_step_run_status_update(
                        step_run_id=self._step_run.id,
                        status=ExecutionStatus.STOPPED,
                        end_time=utc_now(),
                    )
                    raise RunStoppedException(
                        "Step run was stopped due to a failure in the pipeline "
                        "run and the execution mode 'FAIL_FAST'."
                    )

                elif step_run.status == ExecutionStatus.STOPPING:
                    publish_utils.publish_step_run_status_update(
                        step_run_id=step_run.id,
                        status=ExecutionStatus.STOPPED,
                        end_time=utc_now(),
                    )
                    raise RunStoppedException("Pipeline run is stopped.")
                else:
                    raise RunInterruptedException(
                        "The execution was interrupted."
                    )
            except (RunStoppedException, RunInterruptedException):
                raise
            except Exception as e:
                raise RunInterruptedException(str(e))
            finally:
                # Chain to previous handler if it exists and is not default/ignore
                if signum == signal.SIGTERM and callable(
                    self._prev_sigterm_handler
                ):
                    self._prev_sigterm_handler(signum, frame)
                elif signum == signal.SIGINT and callable(
                    self._prev_sigint_handler
                ):
                    self._prev_sigint_handler(signum, frame)

        # Register handlers for common termination signals
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except ValueError as e:
            # This happens when not in the main thread
            logger.debug(f"Cannot register signal handlers: {e}")
            # Continue without signal handling - the step will still run

    def launch(self) -> StepRunResponse:
        """Launches the step.

        Raises:
            RunStoppedException: If the pipeline run is stopped by the user.
            BaseException: If the step preparation or execution fails.

        Returns:
            The step run response.
        """
        publish_utils.step_exception_info.set(None)
        pipeline_run, run_was_created = self._create_or_reuse_run()

        # Enable or disable step logs storage
        if handle_bool_env_var(ENV_ZENML_DISABLE_STEP_LOGS_STORAGE, False):
            step_logging_enabled = False
        else:
            step_logging_enabled = orchestrator_utils.is_setting_enabled(
                is_enabled_on_step=self._step.config.enable_step_logs,
                is_enabled_on_pipeline=self._snapshot.pipeline_configuration.enable_step_logs,
            )

        logs_context = nullcontext()
        logs_model = None

        if step_logging_enabled:
            # Configure the logs
            logs_uri = step_logging.prepare_logs_uri(
                artifact_store=self._stack.artifact_store,
                step_name=self._invocation_id,
            )

            logs_context = step_logging.PipelineLogsStorageContext(
                logs_uri=logs_uri, artifact_store=self._stack.artifact_store
            )  # type: ignore[assignment]

            logs_model = LogsRequest(
                uri=logs_uri,
                source="execution",
                artifact_store_id=self._stack.artifact_store.id,
            )

        with logs_context:
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
            step_run_request.logs = logs_model

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
                self._step_run = step_run
                if model_version := step_run.model_version:
                    step_run_utils.log_model_version_dashboard_url(
                        model_version=model_version
                    )

            if not step_run.status.is_finished:
                logger.info(f"Step `{self._invocation_id}` has started.")

                try:
                    # here pass a forced save_to_file callable to be
                    # used as a dump function to use before starting
                    # the external jobs in step operators
                    if isinstance(
                        logs_context,
                        step_logging.PipelineLogsStorageContext,
                    ):
                        force_write_logs = (
                            logs_context.storage.send_merge_event
                        )
                    else:

                        def _bypass() -> None:
                            return None

                        force_write_logs = _bypass
                    self._run_step(
                        pipeline_run=pipeline_run,
                        step_run=step_run,
                        force_write_logs=force_write_logs,
                    )
                except RunStoppedException as e:
                    raise e
                except BaseException as e:  # noqa: E722
                    logger.error(
                        "Failed to run step `%s`: %s",
                        self._invocation_id,
                        e,
                    )
                    publish_utils.publish_failed_step_run(step_run.id)
                    raise
            else:
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

        return step_run

    def _create_or_reuse_run(self) -> Tuple[PipelineRunResponse, bool]:
        """Creates a pipeline run or reuses an existing one.

        Returns:
            The created or existing pipeline run,
            and a boolean indicating whether the run was created or reused.
        """
        start_time = utc_now()
        run_name = string_utils.format_name_template(
            name_template=self._snapshot.run_name_template,
            substitutions=self._snapshot.pipeline_configuration.finalize_substitutions(
                start_time=start_time,
            ),
        )

        logger.debug("Creating pipeline run %s", run_name)

        client = Client()
        pipeline_run = PipelineRunRequest(
            name=run_name,
            orchestrator_run_id=self._orchestrator_run_id,
            project=client.active_project.id,
            snapshot=self._snapshot.id,
            pipeline=(
                self._snapshot.pipeline.id if self._snapshot.pipeline else None
            ),
            status=ExecutionStatus.RUNNING,
            orchestrator_environment=get_run_environment_dict(),
            start_time=start_time,
            tags=self._snapshot.pipeline_configuration.tags,
        )
        return client.zen_store.get_or_create_run(pipeline_run)

    def _run_step(
        self,
        pipeline_run: PipelineRunResponse,
        step_run: StepRunResponse,
        force_write_logs: Callable[..., Any],
    ) -> None:
        """Runs the current step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            force_write_logs: The context for the step logs.

        """
        from zenml.deployers.server import runtime

        step_run_info = StepRunInfo(
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

        start_time = time.time()

        try:
            if self._step.config.step_operator:
                step_operator_name = None
                if isinstance(self._step.config.step_operator, str):
                    step_operator_name = self._step.config.step_operator

                self._run_step_with_step_operator(
                    step_operator_name=step_operator_name,
                    step_run_info=step_run_info,
                )
            elif not self._snapshot.is_dynamic:
                self._run_step_in_current_thread(
                    pipeline_run=pipeline_run,
                    step_run=step_run,
                    step_run_info=step_run_info,
                    input_artifacts=step_run.regular_inputs,
                    output_artifact_uris=output_artifact_uris,
                )
            else:
                from zenml.execution.pipeline.dynamic.runner import (
                    get_step_runtime,
                )

                step_runtime = get_step_runtime(
                    step_config=self._step.config,
                    pipeline_docker_settings=self._snapshot.pipeline_configuration.docker_settings,
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

                    self._run_step_in_current_thread(
                        pipeline_run=pipeline_run,
                        step_run=step_run,
                        step_run_info=step_run_info,
                        input_artifacts=step_run.regular_inputs,
                        output_artifact_uris=output_artifact_uris,
                    )
                else:
                    self._run_step_with_dynamic_orchestrator(
                        step_run_info=step_run_info
                    )
        except:  # noqa: E722
            output_utils.remove_artifact_dirs(
                artifact_uris=list(output_artifact_uris.values())
            )
            raise

        duration = time.time() - start_time
        logger.info(
            f"Step `{self._invocation_id}` has finished in "
            f"`{string_utils.get_human_readable_time(duration)}`."
        )

    def _run_step_with_step_operator(
        self,
        step_operator_name: Optional[str],
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the current step with a step operator.

        Args:
            step_operator_name: The name of the step operator to use.
            step_run_info: Additional information needed to run the step.
        """
        step_operator = _get_step_operator(
            stack=self._stack,
            step_operator_name=step_operator_name,
        )
        entrypoint_cfg_class = step_operator.entrypoint_config_class
        entrypoint_command = (
            entrypoint_cfg_class.get_entrypoint_command()
            + entrypoint_cfg_class.get_entrypoint_arguments(
                step_name=self._invocation_id,
                snapshot_id=self._snapshot.id,
                step_run_id=str(step_run_info.step_run_id),
            )
        )
        environment, secrets = orchestrator_utils.get_config_environment_vars(
            pipeline_run_id=step_run_info.run_id,
        )
        # TODO: for now, we don't support separate secrets from environment
        # in the step operator environment
        environment.update(secrets)

        environment.update(
            env_utils.get_step_environment(
                step_config=step_run_info.config,
                stack=self._stack,
            )
        )
        environment[ENV_ZENML_STEP_OPERATOR] = "True"
        logger.info(
            "Using step operator `%s` to run step `%s`.",
            step_operator.name,
            self._invocation_id,
        )
        step_operator.launch(
            info=step_run_info,
            entrypoint_command=entrypoint_command,
            environment=environment,
        )

    def _run_step_with_dynamic_orchestrator(
        self,
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the current step with a dynamic orchestrator.

        Args:
            step_run_info: Additional information needed to run the step.
        """
        # If we don't pass the run ID here, does it reuse the existing token?
        environment, secrets = orchestrator_utils.get_config_environment_vars(
            pipeline_run_id=step_run_info.run_id,
        )
        environment.update(secrets)

        environment.update(
            env_utils.get_step_environment(
                step_config=step_run_info.config,
                stack=self._stack,
            )
        )
        self._stack.orchestrator.run_isolated_step(
            step_run_info=step_run_info,
            environment=environment,
        )

    def _run_step_in_current_thread(
        self,
        pipeline_run: PipelineRunResponse,
        step_run: StepRunResponse,
        step_run_info: StepRunInfo,
        input_artifacts: Dict[str, List["StepRunInputResponse"]],
        output_artifact_uris: Dict[str, str],
    ) -> None:
        """Runs the current step without a step operator.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            step_run_info: Additional information needed to run the step.
            input_artifacts: The input artifact versions of the current step.
            output_artifact_uris: The output artifact URIs of the current step.
        """
        runner = StepRunner(step=self._step, stack=self._stack)
        runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )
