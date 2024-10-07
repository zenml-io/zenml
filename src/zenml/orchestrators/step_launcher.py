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

import os
import time
from contextlib import nullcontext
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.constants import (
    ENV_ZENML_DISABLE_STEP_LOGS_STORAGE,
    ENV_ZENML_IGNORE_FAILURE_HOOK,
    STEP_SOURCE_PARAMETER_NAME,
    TEXT_FIELD_MAX_LENGTH,
    handle_bool_env_var,
)
from zenml.enums import ExecutionStatus
from zenml.environment import get_run_environment_dict
from zenml.logger import get_logger
from zenml.logging import step_logging
from zenml.models import (
    ArtifactVersionResponse,
    LogsRequest,
    PipelineDeploymentResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    StepRunRequest,
    StepRunResponse,
)
from zenml.orchestrators import (
    cache_utils,
    input_utils,
    output_utils,
    publish_utils,
)
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.step_runner import StepRunner
from zenml.stack import Stack
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


def _get_step_operator(
    stack: "Stack", step_operator_name: str
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

    if step_operator_name != step_operator.name:
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

    def launch(self) -> None:
        """Launches the step.

        Raises:
            BaseException: If the step failed to launch, run, or publish.
        """
        pipeline_run, run_was_created = self._create_or_reuse_run()

        # Enable or disable step logs storage
        if handle_bool_env_var(ENV_ZENML_DISABLE_STEP_LOGS_STORAGE, False):
            step_logging_enabled = False
        else:
            step_logging_enabled = orchestrator_utils.is_setting_enabled(
                is_enabled_on_step=self._step.config.enable_step_logs,
                is_enabled_on_pipeline=self._deployment.pipeline_configuration.enable_step_logs,
            )

        logs_context = nullcontext()
        logs_model = None

        if step_logging_enabled:
            # Configure the logs
            logs_uri = step_logging.prepare_logs_uri(
                self._stack.artifact_store,
                self._step.config.name,
            )

            logs_context = step_logging.StepLogsStorageContext(
                logs_uri=logs_uri, artifact_store=self._stack.artifact_store
            )  # type: ignore[assignment]

            logs_model = LogsRequest(
                uri=logs_uri,
                artifact_store_id=self._stack.artifact_store.id,
            )

        try:
            with logs_context:
                if run_was_created:
                    pipeline_run_metadata = (
                        self._stack.get_pipeline_run_metadata(
                            run_id=pipeline_run.id
                        )
                    )
                    publish_utils.publish_pipeline_run_metadata(
                        pipeline_run_id=pipeline_run.id,
                        pipeline_run_metadata=pipeline_run_metadata,
                    )
                client = Client()
                (
                    docstring,
                    source_code,
                ) = self._get_step_docstring_and_source_code()

                code_hash = self._deployment.step_configurations[
                    self._step_name
                ].config.caching_parameters.get(STEP_SOURCE_PARAMETER_NAME)
                step_run = StepRunRequest(
                    name=self._step_name,
                    pipeline_run_id=pipeline_run.id,
                    deployment=self._deployment.id,
                    code_hash=code_hash,
                    status=ExecutionStatus.RUNNING,
                    docstring=docstring,
                    source_code=source_code,
                    start_time=datetime.utcnow(),
                    user=client.active_user.id,
                    workspace=client.active_workspace.id,
                    logs=logs_model,
                )
                try:
                    execution_needed, step_run = self._prepare(
                        step_run=step_run
                    )
                except:
                    logger.exception(
                        f"Failed preparing run step `{self._step_name}`."
                    )
                    step_run.status = ExecutionStatus.FAILED
                    step_run.end_time = datetime.utcnow()
                    raise
                finally:
                    step_run_response = Client().zen_store.create_run_step(
                        step_run
                    )

                    # warm-up and register model version
                    _step_run = None
                    model = (
                        self._deployment.step_configurations[
                            step_run.name
                        ].config.model
                        or self._deployment.pipeline_configuration.model
                    )
                    if self._deployment.step_configurations[
                        step_run.name
                    ].config.model:
                        _step_run = step_run_response

                    if model:
                        prep_logs_to_show = (
                            model._prepare_model_version_before_step_launch(
                                pipeline_run=pipeline_run,
                                step_run=_step_run,
                                return_logs=True,
                            )
                        )
                        if prep_logs_to_show:
                            logger.info(prep_logs_to_show)

                logger.info(f"Step `{self._step_name}` has started.")
                if execution_needed:
                    retries = 0
                    last_retry = True
                    max_retries = (
                        step_run_response.config.retry.max_retries
                        if step_run_response.config.retry
                        else 1
                    )
                    delay = (
                        step_run_response.config.retry.delay
                        if step_run_response.config.retry
                        else 0
                    )
                    backoff = (
                        step_run_response.config.retry.backoff
                        if step_run_response.config.retry
                        else 1
                    )

                    while retries < max_retries:
                        last_retry = retries == max_retries - 1
                        try:
                            # here pass a forced save_to_file callable to be
                            # used as a dump function to use before starting
                            # the external jobs in step operators
                            if isinstance(
                                logs_context,
                                step_logging.StepLogsStorageContext,
                            ):
                                force_write_logs = partial(
                                    logs_context.storage.save_to_file,
                                    force=True,
                                )
                            else:

                                def _bypass() -> None:
                                    return None

                                force_write_logs = _bypass
                            self._run_step(
                                pipeline_run=pipeline_run,
                                step_run=step_run_response,
                                last_retry=last_retry,
                                force_write_logs=force_write_logs,
                            )
                            logger.info(
                                f"Step `{self._step_name}` completed successfully."
                            )
                            break
                        except BaseException as e:  # noqa: E722
                            retries += 1
                            if retries < max_retries:
                                logger.error(
                                    f"Failed to run step `{self._step_name}`. Retrying..."
                                )
                                logger.exception(e)
                                logger.info(
                                    f"Sleeping for {delay} seconds before retrying."
                                )
                                time.sleep(delay)
                                delay *= backoff
                            else:
                                logger.error(
                                    f"Failed to run step `{self._step_name}` after {max_retries} retries. Exiting."
                                )
                                logger.exception(e)
                                publish_utils.publish_failed_step_run(
                                    step_run_response.id
                                )
                                raise
                else:
                    orchestrator_utils._link_cached_artifacts_to_model(
                        model_from_context=model,
                        step_run=step_run,
                        step_source=self._step.spec.source,
                    )
                    if model:
                        orchestrator_utils._link_pipeline_run_to_model_from_context(
                            pipeline_run_id=step_run.pipeline_run_id,
                            model=model,
                        )

        except:  # noqa: E722
            logger.error(f"Pipeline run `{pipeline_run.name}` failed.")
            publish_utils.publish_failed_pipeline_run(pipeline_run.id)
            raise

    def _get_step_docstring_and_source_code(self) -> Tuple[Optional[str], str]:
        """Gets the docstring and source code of the step.

        If any of the two is longer than 1000 characters, it will be truncated.

        Returns:
            The docstring and source code of the step.
        """
        from zenml.steps.base_step import BaseStep

        step_instance = BaseStep.load_from_source(self._step.spec.source)

        docstring = step_instance.docstring
        if docstring and len(docstring) > TEXT_FIELD_MAX_LENGTH:
            docstring = docstring[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."

        source_code = step_instance.source_code
        if source_code and len(source_code) > TEXT_FIELD_MAX_LENGTH:
            source_code = source_code[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."

        return docstring, source_code

    def _create_or_reuse_run(self) -> Tuple[PipelineRunResponse, bool]:
        """Creates a pipeline run or reuses an existing one.

        Returns:
            The created or existing pipeline run,
            and a boolean indicating whether the run was created or reused.
        """
        run_name = orchestrator_utils.get_run_name(
            run_name_template=self._deployment.run_name_template
        )

        logger.debug("Creating pipeline run %s", run_name)

        client = Client()
        pipeline_run = PipelineRunRequest(
            name=run_name,
            orchestrator_run_id=self._orchestrator_run_id,
            user=client.active_user.id,
            workspace=client.active_workspace.id,
            deployment=self._deployment.id,
            pipeline=(
                self._deployment.pipeline.id
                if self._deployment.pipeline
                else None
            ),
            status=ExecutionStatus.RUNNING,
            orchestrator_environment=get_run_environment_dict(),
            start_time=datetime.utcnow(),
        )
        return client.zen_store.get_or_create_run(pipeline_run)

    def _prepare(
        self,
        step_run: StepRunRequest,
    ) -> Tuple[bool, StepRunRequest]:
        """Prepares running the step.

        Args:
            step_run: The step to run.

        Returns:
            Tuple that specifies whether the step needs to be executed as
            well as the response model of the registered step run.
        """
        input_artifacts, parent_step_ids = input_utils.resolve_step_inputs(
            step=self._step,
            run_id=step_run.pipeline_run_id,
        )
        input_artifact_ids = {
            input_name: artifact.id
            for input_name, artifact in input_artifacts.items()
        }

        cache_key = cache_utils.generate_cache_key(
            step=self._step,
            input_artifact_ids=input_artifact_ids,
            artifact_store=self._stack.artifact_store,
            workspace_id=Client().active_workspace.id,
        )

        step_run.inputs = input_artifact_ids
        step_run.parent_step_ids = parent_step_ids
        step_run.cache_key = cache_key

        cache_enabled = orchestrator_utils.is_setting_enabled(
            is_enabled_on_step=self._step.config.enable_cache,
            is_enabled_on_pipeline=self._deployment.pipeline_configuration.enable_cache,
        )

        step_cache = self._step.config.enable_cache
        if step_cache is not None:
            logger.info(
                f"Caching {'`enabled`' if step_cache else '`disabled`'} "
                f"explicitly for `{self._step_name}`."
            )

        execution_needed = True
        if cache_enabled:
            cached_step_run = cache_utils.get_cached_step_run(
                cache_key=cache_key
            )
            if cached_step_run:
                logger.info(f"Using cached version of `{self._step_name}`.")
                execution_needed = False
                cached_outputs = cached_step_run.outputs
                step_run.original_step_run_id = cached_step_run.id

                step_run.outputs = {
                    output_name: artifact.id
                    for output_name, artifact in cached_outputs.items()
                }

                step_run.status = ExecutionStatus.CACHED
                step_run.end_time = step_run.start_time

        return execution_needed, step_run

    def _run_step(
        self,
        pipeline_run: PipelineRunResponse,
        step_run: StepRunResponse,
        force_write_logs: Callable[..., Any],
        last_retry: bool = True,
    ) -> None:
        """Runs the current step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            force_write_logs: The context for the step logs.
            last_retry: Whether this is the last retry of the step.
        """
        # Prepare step run information.
        step_run_info = StepRunInfo(
            config=self._step.config,
            pipeline=self._deployment.pipeline_configuration,
            run_name=pipeline_run.name,
            pipeline_step_name=self._step_name,
            run_id=pipeline_run.id,
            step_run_id=step_run.id,
            force_write_logs=force_write_logs,
        )

        output_artifact_uris = output_utils.prepare_output_artifact_uris(
            step_run=step_run, stack=self._stack, step=self._step
        )

        # Run the step.
        start_time = time.time()
        try:
            if self._step.config.step_operator:
                self._run_step_with_step_operator(
                    step_operator_name=self._step.config.step_operator,
                    step_run_info=step_run_info,
                    last_retry=last_retry,
                )
            else:
                self._run_step_without_step_operator(
                    pipeline_run=pipeline_run,
                    step_run=step_run,
                    step_run_info=step_run_info,
                    input_artifacts=step_run.inputs,
                    output_artifact_uris=output_artifact_uris,
                    last_retry=last_retry,
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

    def _run_step_with_step_operator(
        self,
        step_operator_name: str,
        step_run_info: StepRunInfo,
        last_retry: bool,
    ) -> None:
        """Runs the current step with a step operator.

        Args:
            step_operator_name: The name of the step operator to use.
            step_run_info: Additional information needed to run the step.
            last_retry: Whether this is the last retry of the step.
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
        environment = orchestrator_utils.get_config_environment_vars(
            deployment=self._deployment
        )
        if last_retry:
            environment[ENV_ZENML_IGNORE_FAILURE_HOOK] = str(False)
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
        input_artifacts: Dict[str, ArtifactVersionResponse],
        output_artifact_uris: Dict[str, str],
        last_retry: bool,
    ) -> None:
        """Runs the current step without a step operator.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            step_run_info: Additional information needed to run the step.
            input_artifacts: The input artifact versions of the current step.
            output_artifact_uris: The output artifact URIs of the current step.
            last_retry: Whether this is the last retry of the step.
        """
        if last_retry:
            os.environ[ENV_ZENML_IGNORE_FAILURE_HOOK] = "false"
        runner = StepRunner(step=self._step, stack=self._stack)
        runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )
