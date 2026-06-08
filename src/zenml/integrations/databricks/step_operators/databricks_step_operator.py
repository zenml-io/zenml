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

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from databricks.sdk import WorkspaceClient as DatabricksClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.jobs import SubmitRunResponse

from zenml import __version__
from zenml.config.base_settings import BaseSettings
from zenml.constants import ENV_ZENML_CUSTOM_SOURCE_ROOT
from zenml.enums import ExecutionStatus
from zenml.integrations.databricks.flavors.databricks_step_operator_flavor import (
    DatabricksStepOperatorConfig,
    DatabricksStepOperatorSettings,
)
from zenml.integrations.databricks.step_operators.databricks_step_operator_entrypoint_config import (
    WHEEL_PACKAGE_OPTION,
    DatabricksStepOperatorEntrypointConfiguration,
)
from zenml.integrations.databricks.utils.databricks_utils import (
    DATABRICKS_WHEELS_DIRECTORY_PREFIX,
    DATABRICKS_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH,
    build_access_control_list,
    build_databricks_cluster_spec,
    collect_requirements,
    convert_step_to_submit_task,
    delete_workspace_directory,
    get_databricks_wheel_source,
    map_databricks_run_to_execution_status,
    upload_wheel_to_workspace,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.orchestrators.wheel_build_utils import (
    create_wheel,
    get_wheel_package_name,
    prepare_repository_copy_for_wheel,
    sanitize_name,
)
from zenml.stack.stack import Stack
from zenml.stack.stack_validator import StackValidator
from zenml.step_operators.base_step_operator import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import ResourceRequestResponse, StepRunResponse

logger = get_logger(__name__)

DATABRICKS_STEP_RUN_ID_METADATA_KEY = "run_id"
DATABRICKS_STEP_JOB_ID_METADATA_KEY = "job_id"
DATABRICKS_STEP_RUN_URL_METADATA_KEY = "run_page_url"
DATABRICKS_STEP_WHEEL_DIRECTORY_METADATA_KEY = "wheel_directory"


class DatabricksStepOperator(BaseStepOperator):
    """Step operator to run individual steps on Databricks."""

    # Initialized lazily because stack components are deserialized before use.
    _client: Optional[DatabricksClient] = None
    _cleaned_wheel_directories: Optional[set[str]] = None

    @property
    def client(self) -> DatabricksClient:
        """Get or create the Databricks client.

        Returns:
            The Databricks client instance.
        """
        if self._client is None:
            if (
                self.config.client_id is not None
                and self.config.client_secret is not None
            ):
                self._client = DatabricksClient(
                    host=self.config.host,
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                )
            else:
                self._client = DatabricksClient(host=self.config.host)
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

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
        allocated_resource_request: Optional["ResourceRequestResponse"] = None,
    ) -> None:
        """Submit a step run to Databricks.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
            allocated_resource_request: The allocated resource request for the
                step, if any.

        Raises:
            Exception: If wheel upload or Databricks run submission fails
                after cleanup.
            RuntimeError: If the stack or Databricks run ID is missing.
        """
        settings = cast(
            DatabricksStepOperatorSettings, self.get_settings(info)
        )
        stack_model = info.snapshot.stack
        if stack_model is None:
            raise RuntimeError(
                "Missing stack for Databricks step operator submission."
            )

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
        databricks_directory = (
            f"{DATABRICKS_WHEELS_DIRECTORY_PREFIX}/"
            f"{sanitize_name(info.pipeline.name)}/"
            f"{sanitize_name(str(info.run_id))}/steps/{info.step_run_id}"
        )
        try:
            wheel_path = create_wheel(repository_temp_dir)
            try:
                databricks_wheel_path = upload_wheel_to_workspace(
                    databricks_client=self.client,
                    wheel_path=wheel_path,
                    databricks_directory=databricks_directory,
                )
            except Exception:
                delete_workspace_directory(
                    databricks_client=self.client,
                    databricks_directory=databricks_directory,
                    context="failed wheel upload",
                )
                raise

            try:
                environment = environment.copy()
                if settings.spark_env_vars:
                    environment.update(settings.spark_env_vars)
                environment[ENV_ZENML_CUSTOM_SOURCE_ROOT] = (
                    DATABRICKS_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH
                )

                entrypoint_arguments = entrypoint_command[1:] + [
                    f"--{WHEEL_PACKAGE_OPTION}",
                    package_name,
                ]
                task = convert_step_to_submit_task(
                    task_name=str(info.step_run_id),
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
                submitted_run = self.client.jobs.submit(
                    access_control_list=build_access_control_list(settings),
                    run_name=f"{info.run_name}-{info.pipeline_step_name}",
                    tasks=[task],
                    timeout_seconds=settings.timeout_seconds,
                )
            except Exception:
                delete_workspace_directory(
                    databricks_client=self.client,
                    databricks_directory=databricks_directory,
                    context="failed run submission",
                )
                raise
        finally:
            fileio.rmtree(repository_temp_dir)

        submit_response = cast(SubmitRunResponse, submitted_run.response)
        run_id = submit_response.run_id
        if run_id is None:
            delete_workspace_directory(
                databricks_client=self.client,
                databricks_directory=databricks_directory,
                context="run submission without run ID",
            )
            raise RuntimeError(
                "Databricks did not return a run ID for the submitted step."
            )

        metadata: Dict[str, MetadataType] = {
            DATABRICKS_STEP_RUN_ID_METADATA_KEY: str(run_id),
            DATABRICKS_STEP_WHEEL_DIRECTORY_METADATA_KEY: (
                databricks_directory
            ),
        }
        publish_step_run_metadata(info.step_run_id, {self.id: metadata})
        info.step_run.run_metadata.update(metadata)
        try:
            run = self.client.jobs.get_run(run_id=run_id)
        except NotFound:
            logger.warning(
                "Submitted Databricks run '%s' for step '%s', but the run "
                "was not found while retrieving additional metadata.",
                run_id,
                info.pipeline_step_name,
            )
        else:
            extra_metadata: Dict[str, MetadataType] = {}
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
        if not isinstance(run_id, (str, int)):
            raise RuntimeError(
                "Unable to determine the Databricks run ID for step run "
                f"`{step_run.id}` because run metadata key "
                f"`{DATABRICKS_STEP_RUN_ID_METADATA_KEY}` is missing."
            )
        return int(run_id)

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

        status = map_databricks_run_to_execution_status(run)
        if status == ExecutionStatus.COMPLETED:
            self._cleanup_uploaded_wheel_directory(step_run)
        return status

    def _cleanup_uploaded_wheel_directory(
        self, step_run: "StepRunResponse"
    ) -> None:
        """Delete the uploaded wheel directory after successful completion.

        Args:
            step_run: The step run whose metadata contains the wheel directory.
        """
        databricks_directory = step_run.run_metadata.get(
            DATABRICKS_STEP_WHEEL_DIRECTORY_METADATA_KEY
        )
        if not databricks_directory:
            return

        databricks_directory = str(databricks_directory)
        if self._cleaned_wheel_directories is None:
            self._cleaned_wheel_directories = set()
        if databricks_directory in self._cleaned_wheel_directories:
            return

        delete_workspace_directory(
            databricks_client=self.client,
            databricks_directory=databricks_directory,
            context=f"successful completion of step run `{step_run.id}`",
        )
        self._cleaned_wheel_directories.add(databricks_directory)

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
