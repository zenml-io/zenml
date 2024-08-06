#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the Lightening orchestrator."""

import itertools
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast
from uuid import UUID
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_CUSTOM_SOURCE_ROOT,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.integrations.lightening.flavors.lightening_orchestrator_flavor import (
    LighteningOrchestratorConfig,
    LighteningOrchestratorSettings,
)
from zenml.integrations.lightening.orchestrators.lightening_orchestrator_entrypoint_config import (
    LighteningEntrypointConfiguration,
)
from lightning_sdk import Machine, Studio
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.models.v2.core.schedule import ScheduleResponse
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.orchestrators.wheeled_orchestrator import WheeledOrchestrator
from zenml.stack import StackValidator
from zenml.utils import io_utils
from zenml.utils.package_utils import clean_requirements
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack


logger = get_logger(__name__)
ENV_ZENML_LIGHTENING_ORCHESTRATOR_RUN_ID = (
    "ZENML_LIGHTENING_ORCHESTRATOR_RUN_ID"
)
ZENML_STEP_DEFAULT_ENTRYPOINT_COMMAND = "entrypoint.main"

class LighteningOrchestrator(WheeledOrchestrator):
    """Base class for Orchestrator responsible for running pipelines remotely in a VM.

    This orchestrator does not support running on a schedule.
    """

    # The default instance type to use if none is specified in settings
    DEFAULT_INSTANCE_TYPE: Optional[str] = None

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        In the remote case, checks that the stack contains a container registry,
        image builder and only remote components.

        Returns:
            A `StackValidator` instance.
        """

        def _validate_remote_components(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            for component in stack.components.values():
                if not component.config.is_local:
                    continue

                return False, (
                    f"The Lightening orchestrator runs pipelines remotely, "
                    f"but the '{component.name}' {component.type.value} is "
                    "a local stack component and will not be available in "
                    "the Lightening step.\nPlease ensure that you always "
                    "use non-local stack components with the Lightening "
                    "orchestrator."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_remote_components,
        )

    def _get_lightening_client(
        self,
    ) -> None:
        """Set up the Lightening client using environment variables."""
        os.environ["LIGHTNING_USER_ID"] = self.config.user_id
        os.environ["LIGHTNING_API_KEY"] = self.config.user_secret
        
    
    @property
    def config(self) -> LighteningOrchestratorConfig:
        """Returns the `LighteningOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(LighteningOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Type[LighteningOrchestratorSettings]:
        """Settings class for the Lightening orchestrator.

        Returns:
            The settings class.
        """
        return LighteningOrchestratorSettings

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If no run id exists. This happens when this method
                gets called while the orchestrator is not running a pipeline.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id cannot be read from the environment.
        """
        try:
            return os.environ[ENV_ZENML_LIGHTENING_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_LIGHTENING_ORCHESTRATOR_RUN_ID}."
            )

    @property
    def root_directory(self) -> str:
        """Path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "lightening",
            str(self.id),
        )

    @property
    def pipeline_directory(self) -> str:
        """Returns path to a directory in which the kubeflow pipeline files are stored.

        Returns:
            Path to the pipeline directory.
        """
        return os.path.join(self.root_directory, "pipelines")

    def setup_credentials(self) -> None:
        """Set up credentials for the orchestrator."""
        connector = self.get_connector()
        assert connector is not None
        connector.configure_local_client()

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Creates a wheel and uploads the pipeline to Lightening.

        This functions as an intermediary representation of the pipeline which
        is then deployed to the kubeflow pipelines instance.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()`
        method builds a docker image that contains the code for the
        pipeline, all steps the context around these files.

        Based on this docker image a callable is created which builds
        task for each step (`_construct_lightening_pipeline`).
        To do this the entrypoint of the docker image is configured to
        run the correct step within the docker image. The dependencies
        between these task are then also configured onto each
        task by pointing at the downstream steps.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            ValueError: If the schedule is not set or if the cron expression
                is not set.
        """
        settings = cast(
            LighteningOrchestratorSettings, self.get_settings(deployment)
        )
        if deployment.schedule:
            if (
                deployment.schedule.catchup
                or deployment.schedule.interval_second
            ):
                logger.warning(
                    "Lightening orchestrator only uses schedules with the "
                    "`cron_expression` property, with optional `start_time` and/or `end_time`. "
                    "All other properties are ignored."
                )
            if deployment.schedule.cron_expression is None:
                raise ValueError(
                    "Property `cron_expression` must be set when passing "
                    "schedule to a Lightening orchestrator."
                )
            if (
                deployment.schedule.cron_expression
                and settings.schedule_timezone is None
            ):
                raise ValueError(
                    "Property `schedule_timezone` must be set when passing "
                    "`cron_expression` to a Lightening orchestrator."
                    "Lightening orchestrator requires a Java Timezone ID to run the pipeline on schedule."
                    "Please refer to https://docs.oracle.com/middleware/1221/wcs/tag-ref/MISC/TimeZones.html for more information."
                )

        # Get deployment id
        deployment_id = deployment.id

        # Get the orchestrator run name
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )
        
        # Copy the repository to a temporary directory and add a setup.py file
        repository_temp_dir = (
            self.copy_repository_to_temp_dir_and_add_setup_py()
        )

        # Create a wheel for the package in the temporary directory
        wheel_path = self.create_wheel(temp_dir=repository_temp_dir)

        # Create an empty folder in a volume.
        deployment_name = (
            deployment.pipeline.name if deployment.pipeline else "default"
        )
        
        # Construct the env variables for the pipeline
        env_vars = environment.copy()
        spark_env_vars = settings.spark_env_vars
        if spark_env_vars:
            for key, value in spark_env_vars.items():
                env_vars[key] = value
        env_vars[ENV_ZENML_CUSTOM_SOURCE_ROOT] = (
            LIGHTENING_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH
        )

        fileio.rmtree(repository_temp_dir)
        self._get_lightening_client()
        studio = Studio(name="start-stop-delete-demo", create_ok=True)
        studio.upload_file(wheel_path, remote_path="./wheel.whl")
        for step_name, step in deployment.step_configurations.items():
            # The arguments are passed to configure the entrypoint of the
            # docker container when the step is called.
            arguments = LighteningEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name,
                deployment_id=deployment_id,
                wheel_package=self.package_name,
            )

            docker_settings = step.config.docker_settings
            docker_image_builder = PipelineDockerImageBuilder()
            # Gather the requirements files
            requirements_files = (
                docker_image_builder.gather_requirements_files(
                    docker_settings=docker_settings,
                    stack=Client().active_stack,
                    log=False,
                )
            )

            # Extract and clean the requirements
            requirements = list(
                itertools.chain.from_iterable(
                    r[1].strip().split("\n") for r in requirements_files
                )
            )

            # Remove empty items and duplicates
            requirements = sorted(set(filter(None, requirements)))
            
            requirements_to_string = " ".join(requirements)
            studio.run(f"pip install {requirements_to_string}")
            
            arguments_to_string = " ".join(arguments)
            run_command = f"python zenml.{ZENML_STEP_DEFAULT_ENTRYPOINT_COMMAND}.{arguments_to_string}"
            studio.run(run_command)
            
            
    def _upload_and_run_pipeline(
        self,
        pipeline_name: str,
        settings: LighteningOrchestratorSettings,
        env_vars: Dict[str, str],
        job_cluster_key: str,
        schedule: Optional["ScheduleResponse"] = None,
    ) -> None:
        """Uploads and run the pipeline on the Lightening jobs.

        Args:
            pipeline_name: The name of the pipeline.
            tasks: The list of tasks to run.
            env_vars: The environment variables.
            job_cluster_key: The ID of the Lightening job cluster.
            schedule: The schedule to run the pipeline
            settings: The settings for the Lightening orchestrator.

        Raises:
            ValueError: If the `Job Compute` policy is not found.
            ValueError: If the `schedule_timezone` is not set when passing

        """
        self._get_lightening_client()
        s = Studio()


    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        run_url = (
            f"{self.config.host}/jobs/" f"{self.get_orchestrator_run_id()}"
        )
        return {
            METADATA_ORCHESTRATOR_URL: Uri(run_url),
        }
