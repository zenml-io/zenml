#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Databricks step operator implementation."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast

from databricks.sdk import WorkspaceClient as DatabricksClient
from databricks.sdk.errors import NotFound

from zenml import __version__
from zenml.config.base_settings import BaseSettings
from zenml.constants import ENV_ZENML_CUSTOM_SOURCE_ROOT
from zenml.enums import ExecutionStatus
from zenml.integrations.databricks.flavors.databricks_step_operator_flavor import (
    DatabricksStepOperatorConfig,
    DatabricksStepOperatorSettings,
)
from zenml.integrations.databricks.step_operators.databricks_step_operator_entrypoint_config import (
    DatabricksStepOperatorEntrypointConfiguration,
)
from zenml.integrations.databricks.utils.databricks_utils import (
    DATABRICKS_WHEELS_DIRECTORY_PREFIX,
    DATABRICKS_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH,
    build_databricks_cluster_spec,
    build_submit_access_control_list,
    collect_requirements,
    convert_step_to_submit_task,
    get_databricks_wheel_source,
    map_databricks_run_to_execution_status,
    upload_wheel_to_workspace,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.orchestrators.wheel_build_utils import (
    create_wheel,
    get_wheel_package_name,
    prepare_repository_copy_for_wheel,
    sanitize_name,
)
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import StepRunResponse

logger = get_logger(__name__)

DATABRICKS_STEP_RUN_ID_METADATA_KEY = "run_id"
DATABRICKS_STEP_JOB_ID_METADATA_KEY = "job_id"
DATABRICKS_STEP_RUN_URL_METADATA_KEY = "run_page_url"


class DatabricksStepOperator(BaseStepOperator):
    """Step operator to run individual steps on Databricks."""

    _client: Optional[DatabricksClient] = None

    @property
    def client(self) -> DatabricksClient:
        """Get or create the Databricks client.

        Returns:
            The Databricks client instance.
        """
        if self._client is None:
            self._client = DatabricksClient(
                host=self.config.host,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
            )
        return self._client

    @property
    def config(self) -> DatabricksStepOperatorConfig:
        """Returns the step operator config.

        Returns:
            The configuration.
        """
        return cast(DatabricksStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type[BaseSettings]]:
        """Settings class for the Databricks step operator.

        Returns:
            The settings class.
        """
        return DatabricksStepOperatorSettings

    @property
    def entrypoint_config_class(
        self,
    ) -> Type[DatabricksStepOperatorEntrypointConfiguration]:
        """Returns the entrypoint configuration class for Databricks steps.

        Returns:
            The Databricks step operator entrypoint configuration class.
        """
        return DatabricksStepOperatorEntrypointConfiguration

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack for Databricks step operator execution.

        Returns:
            A validator that checks for a remote artifact store.
        """

        def _validate_remote_components(stack: Stack) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Databricks step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the "
                    "Databricks step operator."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_remote_components
        )

    def _warn_about_ignored_settings(
        self,
        info: "StepRunInfo",
        settings: DatabricksStepOperatorSettings,
    ) -> None:
        """Warn about settings that the one-time-run path cannot honor.

        Args:
            info: Information about the step run.
            settings: Databricks step operator settings.
        """
        if not info.config.resource_settings.empty:
            logger.warning(
                "Specifying custom step resources is not supported for the "
                "Databricks step operator. Configure Databricks cluster "
                "resources through the Databricks step operator settings "
                "instead."
            )

        ignored_settings = []
        if settings.schedule_timezone is not None:
            ignored_settings.append("schedule_timezone")
        if settings.job_tags:
            ignored_settings.append("job_tags")
        if settings.max_concurrent_runs is not None:
            ignored_settings.append("max_concurrent_runs")
        if settings.max_retries is not None:
            ignored_settings.append("max_retries")
        if settings.min_retry_interval_millis is not None:
            ignored_settings.append("min_retry_interval_millis")
        if settings.retry_on_timeout is not None:
            ignored_settings.append("retry_on_timeout")

        if ignored_settings:
            logger.warning(
                "The Databricks step operator does not apply the following "
                "settings for one-time Databricks runs: %s.",
                ", ".join(sorted(ignored_settings)),
            )

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: list[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step run to Databricks.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.

        Raises:
            RuntimeError: If Databricks run submission fails.
        """
        settings = cast(
            DatabricksStepOperatorSettings, self.get_settings(info)
        )
        stack_model = info.snapshot.stack
        if stack_model is None:
            raise RuntimeError(
                "Missing stack for Databricks step operator submission."
            )

        self._warn_about_ignored_settings(info=info, settings=settings)
        info.force_write_logs()

        wheel_source = get_databricks_wheel_source()
        if wheel_source:
            source_root, package_name = wheel_source
        else:
            source_root = None
            package_name = get_wheel_package_name()
        repository_temp_dir = prepare_repository_copy_for_wheel(
            package_name=package_name,
            package_version=__version__,
            source_root=source_root,
        )
        try:
            wheel_path = create_wheel(repository_temp_dir)
            databricks_directory = (
                f"{DATABRICKS_WHEELS_DIRECTORY_PREFIX}/"
                f"{sanitize_name(info.pipeline.name)}/{info.step_run_id}"
            )
            databricks_wheel_path = upload_wheel_to_workspace(
                databricks_client=self.client,
                wheel_path=wheel_path,
                databricks_directory=databricks_directory,
            )

            environment = environment.copy()
            if settings.spark_env_vars:
                environment.update(settings.spark_env_vars)
            environment[ENV_ZENML_CUSTOM_SOURCE_ROOT] = (
                DATABRICKS_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH
            )

            entrypoint_arguments = DatabricksStepOperatorEntrypointConfiguration.get_entrypoint_arguments(
                step_name=info.pipeline_step_name,
                snapshot_id=info.snapshot.id,
                step_run_id=str(info.step_run_id),
                wheel_package=package_name,
            )
            task = convert_step_to_submit_task(
                task_name=f"{info.step_run_id}",
                command=entrypoint_command[0],
                arguments=entrypoint_arguments,
                libraries=collect_requirements(
                    docker_settings=info.config.docker_settings,
                    stack=Stack.from_model(stack_model),
                ),
                zenml_project_wheel=databricks_wheel_path,
                new_cluster=build_databricks_cluster_spec(
                    databricks_client=self.client,
                    settings=settings,
                    env_vars=environment,
                ),
                timeout_seconds=settings.task_timeout_seconds,
            )
            submitted_run = cast(
                Any,
                self.client.jobs.submit(
                    access_control_list=cast(
                        Any, build_submit_access_control_list(settings)
                    ),
                    run_name=f"{info.run_name}-{info.pipeline_step_name}",
                    tasks=[task],
                    timeout_seconds=settings.timeout_seconds,
                ),
            )
        finally:
            fileio.rmtree(repository_temp_dir)

        run_id = cast(
            int, submitted_run.response.run_id or submitted_run.run_id
        )
        if run_id is None:
            raise RuntimeError(
                "Databricks did not return a run ID for the submitted step."
            )

        metadata = cast(
            Dict[str, Any],
            {DATABRICKS_STEP_RUN_ID_METADATA_KEY: str(run_id)},
        )
        publish_step_run_metadata(info.step_run_id, {self.id: metadata})
        info.step_run.run_metadata.update(metadata)
        try:
            run = self.client.jobs.get_run(run_id=run_id)
        except Exception as e:
            logger.warning(
                "Submitted Databricks run '%s' for step '%s', but failed to "
                "retrieve additional run metadata: %s",
                run_id,
                info.pipeline_step_name,
                e,
            )
        else:
            extra_metadata: Dict[str, Any] = {}
            if run.job_id is not None:
                extra_metadata[DATABRICKS_STEP_JOB_ID_METADATA_KEY] = str(
                    run.job_id
                )
            if run.run_page_url:
                extra_metadata[DATABRICKS_STEP_RUN_URL_METADATA_KEY] = (
                    run.run_page_url
                )
            if extra_metadata:
                publish_step_run_metadata(
                    info.step_run_id, {self.id: extra_metadata}
                )
                info.step_run.run_metadata.update(extra_metadata)

        logger.info(
            "Submitted step '%s' to Databricks as run '%s'.",
            info.pipeline_step_name,
            run_id,
        )

    def _get_run_id(self, step_run: "StepRunResponse") -> int:
        """Get the Databricks run ID from step run metadata.

        Args:
            step_run: The step run.

        Returns:
            The Databricks run ID.

        Raises:
            RuntimeError: If the Databricks run ID is missing.
        """
        run_id = step_run.run_metadata.get(DATABRICKS_STEP_RUN_ID_METADATA_KEY)
        if not run_id:
            raise RuntimeError(
                "Unable to determine the Databricks run ID for step run "
                f"`{step_run.id}` because run metadata key "
                f"`{DATABRICKS_STEP_RUN_ID_METADATA_KEY}` is missing."
            )
        return int(str(run_id))

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the status of a Databricks step run.

        Args:
            step_run: The step run to get the status of.

        Returns:
            The ZenML step execution status.
        """
        run_id = self._get_run_id(step_run)

        try:
            run = self.client.jobs.get_run(run_id=run_id)
        except NotFound:
            logger.warning(
                "Databricks run `%s` for step run `%s` was not found.",
                run_id,
                step_run.id,
            )
            return ExecutionStatus.FAILED

        return map_databricks_run_to_execution_status(run)

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a Databricks step run.

        Args:
            step_run: The step run to cancel.
        """
        run_id = self._get_run_id(step_run)

        try:
            self.client.jobs.cancel_run(run_id=run_id)
        except NotFound:
            logger.warning(
                "Databricks run `%s` for step run `%s` was not found during "
                "cancellation.",
                run_id,
                step_run.id,
            )
