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
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.constants import (
    ENV_ZENML_DISABLE_STEP_LOGS_STORAGE,
    ENV_ZENML_STEP_OPERATOR,
    handle_bool_env_var,
)
from zenml.enums import ExecutionStatus
from zenml.environment import get_run_environment_dict
from zenml.exceptions import RunInterruptedException, RunStoppedException
from zenml.execution.capture_policy import CapturePolicy
from zenml.execution.factory import get_runtime
from zenml.logger import get_logger
from zenml.logging import step_logging
from zenml.models import (
    LogsRequest,
    PipelineDeploymentResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    StepRunResponse,
)
from zenml.models.v2.core.step_run import StepRunInputResponse
from zenml.orchestrators import output_utils, publish_utils, step_run_utils
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.step_runner import StepRunner
from zenml.stack import Stack
from zenml.utils import exception_utils, string_utils
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
        deployment: PipelineDeploymentResponse,
        step: Step,
        orchestrator_run_id: str,
    ):
        """Initializes the launcher.

        Args:
            deployment: The pipeline deployment.
            step: The step to launch.
            orchestrator_run_id: The orchestrator pipeline run id.

        Raises:
            RuntimeError: If the deployment has no associated stack.
        """
        self._deployment = deployment
        self._step = step
        self._orchestrator_run_id = orchestrator_run_id

        if not deployment.stack:
            raise RuntimeError(
                f"Missing stack for deployment {deployment.id}. This is "
                "probably because the stack was manually deleted."
            )

        self._stack = Stack.from_model(deployment.stack)
        self._step_name = step.spec.pipeline_parameter_name

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
                f"for step '{self._step_name}'..."
            )

            try:
                client = Client()
                pipeline_run = None

                if self._step_run:
                    pipeline_run = client.get_pipeline_run(
                        self._step_run.pipeline_run_id
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
                    raise RunStoppedException("Pipeline run in stopped.")
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

    def launch(self) -> None:
        """Launches the step.

        Raises:
            RunStoppedException: If the pipeline run is stopped by the user.
            BaseException: If the step preparation or execution fails.
        """
        publish_utils.step_exception_info.set(None)
        # Determine tracking toggle purely from pipeline settings
        tracking_disabled = orchestrator_utils.is_tracking_disabled(
            self._deployment.pipeline_configuration.settings
            if self._deployment.pipeline_configuration.settings
            else None
        )

        # Determine capture-based runtime and memory-only mode early
        mode_cfg = getattr(
            self._deployment.pipeline_configuration, "capture", None
        )
        capture_policy = CapturePolicy.from_value(mode_cfg)
        runtime = get_runtime(capture_policy)
        # Store for later use
        self._runtime = runtime
        runs_opt = str(capture_policy.get_option("runs", "on")).lower()
        persistence = str(
            capture_policy.get_option("persistence", "async")
        ).lower()
        memory_only = runs_opt in {"off", "false", "0"} or persistence in {
            "memory",
            "off",
        }

        if memory_only:
            self._launch_memory_only()
            return
        pipeline_run, run_was_created = self._create_or_reuse_run()

        # runtime already constructed above; configure flush behavior
        # Default for serving (REALTIME): do not flush at step end unless user specifies
        import os as _os

        in_serving_ctx = (
            _os.getenv("ZENML_SERVING_CAPTURE_DEFAULT") is not None
        )
        if (
            capture_policy.mode.name == "REALTIME"
            and "flush_on_step_end"
            not in getattr(capture_policy, "options", {})
            and in_serving_ctx
        ):
            flush_opt = False
        else:
            # Honor capture option: flush_on_step_end (default True)
            flush_opt = capture_policy.get_option("flush_on_step_end", True)
        # Configure runtime flush behavior if supported
        set_flush = getattr(runtime, "set_flush_on_step_end", None)
        if callable(set_flush):
            try:
                set_flush(bool(flush_opt))
            except Exception as e:
                logger.debug(
                    "Could not configure runtime flush behavior: %s", e
                )

        # Enable or disable step logs storage
        if (
            handle_bool_env_var(ENV_ZENML_DISABLE_STEP_LOGS_STORAGE, False)
            or tracking_disabled
        ):
            step_logging_enabled = False
        else:
            step_logging_enabled = orchestrator_utils.is_setting_enabled(
                is_enabled_on_step=self._step.config.enable_step_logs,
                is_enabled_on_pipeline=self._deployment.pipeline_configuration.enable_step_logs,
            )

        logs_context = nullcontext()
        logs_model = None

        if step_logging_enabled and not tracking_disabled:
            # Configure the logs
            logs_uri = step_logging.prepare_logs_uri(
                artifact_store=self._stack.artifact_store,
                step_name=self._step_name,
            )

            logs_context = step_logging.PipelineLogsStorageContext(
                logs_uri=logs_uri, artifact_store=self._stack.artifact_store
            )  # type: ignore[assignment]

            logs_model = LogsRequest(
                uri=logs_uri,
                source="execution",
                artifact_store_id=self._stack.artifact_store.id,
            )

        # In no-capture, caching will be disabled via effective config
        with logs_context:
            if run_was_created and not tracking_disabled:
                pipeline_run_metadata = self._stack.get_pipeline_run_metadata(
                    run_id=pipeline_run.id
                )
                runtime.start()
                runtime.publish_pipeline_run_metadata(
                    pipeline_run_id=pipeline_run.id,
                    pipeline_run_metadata=pipeline_run_metadata,
                )
                if model_version := pipeline_run.model_version:
                    step_run_utils.log_model_version_dashboard_url(
                        model_version=model_version
                    )

        # Honor capture.code flag (default True)
        code_opt = capture_policy.get_option("code", True)
        code_enabled = str(code_opt).lower() not in {"false", "0", "off"}

        request_factory = step_run_utils.StepRunRequestFactory(
            deployment=self._deployment,
            pipeline_run=pipeline_run,
            stack=self._stack,
            runtime=runtime,
            skip_code_capture=not code_enabled,
        )
        step_run_request = request_factory.create_request(
            invocation_id=self._step_name
        )
        step_run_request.logs = logs_model

        # If this step has upstream dependencies and runtime uses non-blocking
        # publishes, ensure previous step updates are flushed so input
        # resolution via server succeeds.
        if (
            self._step.spec.upstream_steps
            and not runtime.should_flush_on_step_end()
        ):
            try:
                runtime.flush()
            except Exception as e:
                logger.debug(
                    "Non-blocking flush before input resolution failed: %s", e
                )

        try:
            # Always populate request to ensure proper input/output flow
            request_factory.populate_request(request=step_run_request)

            # In no-capture mode, force fresh execution (bypass cache)
            if tracking_disabled:
                step_run_request.original_step_run_id = None
                step_run_request.outputs = {}
                step_run_request.status = ExecutionStatus.RUNNING
        except BaseException as e:
            logger.exception(f"Failed preparing step `{self._step_name}`.")
            step_run_request.status = ExecutionStatus.FAILED
            step_run_request.end_time = utc_now()
            step_run_request.exception_info = (
                exception_utils.collect_exception_information(e)
            )
            raise
        finally:
            # Always create real step run for proper input/output flow
            step_run = Client().zen_store.create_run_step(step_run_request)
            self._step_run = step_run
            if not tracking_disabled and (
                model_version := step_run.model_version
            ):
                step_run_utils.log_model_version_dashboard_url(
                    model_version=model_version
                )

        if not step_run.status.is_finished:
            logger.info(f"Step `{self._step_name}` has started.")

            try:
                # here pass a forced save_to_file callable to be
                # used as a dump function to use before starting
                # the external jobs in step operators
                if isinstance(
                    logs_context,
                    step_logging.PipelineLogsStorageContext,
                ):
                    force_write_logs = logs_context.storage.send_merge_event
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
                    self._step_name,
                    e,
                )
                if not tracking_disabled:
                    runtime.publish_failed_step_run(step_run_id=step_run.id)
                    if runtime.should_flush_on_step_end():
                        runtime.flush()
                raise
        else:
            logger.info(f"Using cached version of step `{self._step_name}`.")
            if not tracking_disabled:
                if (
                    model_version := step_run.model_version
                    or pipeline_run.model_version
                ):
                    step_run_utils.link_output_artifacts_to_model_version(
                        artifacts=step_run.outputs,
                        model_version=model_version,
                    )
                # Ensure any queued updates are flushed for cached path (if enabled)
                if runtime.should_flush_on_step_end():
                    runtime.flush()
        # Ensure runtime shutdown after launch
        try:
            metrics = {}
            try:
                metrics = runtime.get_metrics() or {}
            except Exception:
                metrics = {}
            runtime.shutdown()
            if metrics:
                logger.info(
                    "Runtime metrics: queued=%s processed=%s failed_total=%s queue_depth=%s",
                    metrics.get("queued"),
                    metrics.get("processed"),
                    metrics.get("failed_total"),
                    metrics.get("queue_depth"),
                )
        except Exception as e:
            logger.debug(f"Runtime shutdown/metrics retrieval error: {e}")

    def _create_or_reuse_run(self) -> Tuple[PipelineRunResponse, bool]:
        """Creates a pipeline run or reuses an existing one.

        Returns:
            The created or existing pipeline run,
            and a boolean indicating whether the run was created or reused.
        """
        # Always create actual pipeline run in DB for proper input/output flow
        start_time = utc_now()
        run_name = string_utils.format_name_template(
            name_template=self._deployment.run_name_template,
            substitutions=self._deployment.pipeline_configuration.finalize_substitutions(
                start_time=start_time,
            ),
        )

        logger.debug("Creating pipeline run %s", run_name)

        client = Client()
        pipeline_run = PipelineRunRequest(
            name=run_name,
            orchestrator_run_id=self._orchestrator_run_id,
            project=client.active_project.id,
            deployment=self._deployment.id,
            pipeline=(
                self._deployment.pipeline.id
                if self._deployment.pipeline
                else None
            ),
            status=ExecutionStatus.RUNNING,
            orchestrator_environment=get_run_environment_dict(),
            start_time=start_time,
            tags=self._deployment.pipeline_configuration.tags,
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
        # Create effective step config with serving overrides and no-capture optimizations
        from zenml.orchestrators import utils as orchestrator_utils

        effective_step_config = self._step.config.model_copy(deep=True)

        # In no-capture mode, disable caching and step operators for speed
        tracking_disabled = orchestrator_utils.is_tracking_disabled(
            self._deployment.pipeline_configuration.settings
        )
        if tracking_disabled:
            effective_step_config = effective_step_config.model_copy(
                update={
                    "enable_cache": False,
                    "step_operator": None,
                    "retry": effective_step_config.retry.model_copy(
                        update={"max_retries": 0, "delay": 0, "backoff": 1}
                    )
                    if effective_step_config.retry
                    else None,
                }
            )

        # Prepare step run information with effective config
        step_run_info = StepRunInfo(
            config=effective_step_config,
            pipeline=self._deployment.pipeline_configuration,
            run_name=pipeline_run.name,
            pipeline_step_name=self._step_name,
            run_id=pipeline_run.id,
            step_run_id=step_run.id,
            force_write_logs=force_write_logs,
        )

        # Always prepare output URIs for proper artifact flow
        output_artifact_uris = output_utils.prepare_output_artifact_uris(
            step_run=step_run, stack=self._stack, step=self._step
        )

        # Run the step.
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
            else:
                self._run_step_without_step_operator(
                    pipeline_run=pipeline_run,
                    step_run=step_run,
                    step_run_info=step_run_info,
                    input_artifacts=step_run.regular_inputs,
                    output_artifact_uris=output_artifact_uris,
                )
        except:  # noqa: E722
            output_utils.remove_artifact_dirs(
                artifact_uris=list(output_artifact_uris.values())
            )
            raise

        duration = time.time() - start_time
        logger.info(
            f"Step `{self._step_name}` has finished in "
            f"`{string_utils.get_human_readable_time(duration)}`."
        )

        # If runtime is non-blocking and there are downstream steps depending
        # on this step, flush now so that downstream input resolution sees
        # this step's outputs on the server.
        runtime = getattr(self, "_runtime", None)
        if runtime is not None and not runtime.should_flush_on_step_end():
            has_downstream = any(
                self._step_name in cfg.spec.upstream_steps
                for name, cfg in self._deployment.step_configurations.items()
            )
            if has_downstream:
                try:
                    runtime.flush()
                except Exception as e:
                    logger.debug(
                        "Non-blocking runtime flush after step finish failed: %s",
                        e,
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
                step_name=self._step_name,
                deployment_id=self._deployment.id,
                step_run_id=str(step_run_info.step_run_id),
            )
        )
        environment, secrets = orchestrator_utils.get_config_environment_vars(
            pipeline_run_id=step_run_info.run_id,
        )
        # TODO: for now, we don't support separate secrets from environment
        # in the step operator environment
        environment.update(secrets)

        environment[ENV_ZENML_STEP_OPERATOR] = "True"
        # Propagate capture mode to the step operator environment so that
        # the entrypoint can construct the appropriate runtime.
        try:
            mode_cfg = getattr(
                self._deployment.pipeline_configuration, "capture", None
            )
            if mode_cfg:
                environment["ZENML_CAPTURE_MODE"] = str(mode_cfg).upper()
                environment["ZENML_ENABLE_STEP_RUNTIME"] = "true"
        except Exception:
            pass
        logger.info(
            "Using step operator `%s` to run step `%s`.",
            step_operator.name,
            self._step_name,
        )
        step_operator.launch(
            info=step_run_info,
            entrypoint_command=entrypoint_command,
            environment=environment,
        )

    def _run_step_without_step_operator(
        self,
        pipeline_run: PipelineRunResponse,
        step_run: StepRunResponse,
        step_run_info: StepRunInfo,
        input_artifacts: Dict[str, StepRunInputResponse],
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
        # Use runtime determined at launch
        runtime = getattr(self, "_runtime", None)
        runner = StepRunner(
            step=self._step, stack=self._stack, runtime=runtime
        )
        runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )

    def _launch_memory_only(self) -> None:
        """Launch the step in pure memory-only mode (no runs, no persistence)."""
        from dataclasses import dataclass
        from typing import Any

        from zenml.config.step_run_info import StepRunInfo
        from zenml.execution.step_runtime import MemoryStepRuntime
        from zenml.utils.time_utils import utc_now

        run_id = self._orchestrator_run_id
        start_time = utc_now()
        substitutions = (
            self._deployment.pipeline_configuration.finalize_substitutions(
                start_time=start_time
            )
        )

        @dataclass
        class _Cfg:
            tags: Any = None

        @dataclass
        class _PipelineRunStub:
            id: str
            model_version: Any = None
            pipeline: Any = None
            config: Any = _Cfg()

        @dataclass
        class _StepCfg:
            substitutions: Any
            outputs: Any

        @dataclass
        class _StepRunStub:
            id: str
            name: str
            model_version: Any
            config: Any
            is_retriable: bool = True

        pipeline_run_stub = _PipelineRunStub(id=run_id)
        step_run_stub = _StepRunStub(
            id=run_id,  # valid UUID string preferred
            name=self._step_name,
            model_version=None,
            config=_StepCfg(
                substitutions=substitutions, outputs=self._step.config.outputs
            ),
            is_retriable=True,
        )

        # Build URIs from declared outputs (no imports needed)
        output_names = list(self._step.config.outputs.keys())
        output_artifact_uris = {
            name: f"memory://{run_id}/{self._step_name}/{name}"
            for name in output_names
        }

        # Resolve inputs via runtime to avoid duplication
        if isinstance(self._runtime, MemoryStepRuntime):
            self._runtime.set_context(
                run_id=run_id, substitutions=substitutions
            )
            input_artifacts = self._runtime.resolve_step_inputs(
                step=self._step, pipeline_run=pipeline_run_stub
            )
        else:
            input_artifacts = {}

        runner = StepRunner(
            step=self._step, stack=self._stack, runtime=self._runtime
        )
        step_run_info = StepRunInfo(
            config=self._step.config,
            pipeline=self._deployment.pipeline_configuration,
            run_name=self._deployment.run_name_template,
            pipeline_step_name=self._step_name,
            run_id=run_id,
            step_run_id=step_run_stub.id,
            force_write_logs=lambda: None,
        )

        from typing import Any, cast

        runner.run(
            pipeline_run=cast(Any, pipeline_run_stub),
            step_run=cast(Any, step_run_stub),
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )
