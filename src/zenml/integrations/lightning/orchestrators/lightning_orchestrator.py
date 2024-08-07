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
"""Implementation of the Lightning orchestrator."""

import itertools
import os
import re
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast
from uuid import uuid4

from lightning_sdk import Machine, Studio

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_CUSTOM_SOURCE_ROOT,
)
from zenml.integrations.lightning.flavors.lightning_orchestrator_flavor import (
    LightningOrchestratorConfig,
    LightningOrchestratorSettings,
)
from zenml.integrations.lightning.orchestrators.lightning_orchestrator_entrypoint_config import (
    LightningEntrypointConfiguration,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators.wheeled_orchestrator import WheeledOrchestrator
from zenml.stack import StackValidator
from zenml.utils import io_utils
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack


logger = get_logger(__name__)
ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID = "ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID"
ZENML_STEP_DEFAULT_ENTRYPOINT_COMMAND = "zenml.entrypoints.entrypoint"
LIGHTNING_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH = "."


class LightningOrchestrator(WheeledOrchestrator):
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
                    f"The Lightning orchestrator runs pipelines remotely, "
                    f"but the '{component.name}' {component.type.value} is "
                    "a local stack component and will not be available in "
                    "the Lightning step.\nPlease ensure that you always "
                    "use non-local stack components with the Lightning "
                    "orchestrator."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_remote_components,
        )

    def _get_lightning_client(
        self,
    ) -> None:
        """Set up the Lightning client using environment variables."""
        os.environ["LIGHTNING_USER_ID"] = (
            "cd5ab9d7-4dcf-4bdb-97eb-d9bea882e72b"
        )
        os.environ["LIGHTNING_API_KEY"] = (
            "7ad6b02d-2d19-4203-9994-da3992eeafd5"
        )
        # os.environ["LIGHTNING_ORG"] = "safoine-zenml"
        os.environ["LIGHTNING_USERNAME"] = "safoineext"
        os.environ["LIGHTNING_TEAMSPACE"] = "vision-model"

    @property
    def config(self) -> LightningOrchestratorConfig:
        """Returns the `LightningOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(LightningOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Type[LightningOrchestratorSettings]:
        """Settings class for the Lightning orchestrator.

        Returns:
            The settings class.
        """
        return LightningOrchestratorSettings

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
            return os.environ[ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID}."
            )

    @property
    def root_directory(self) -> str:
        """Path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "lightning",
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
        """Creates a wheel and uploads the pipeline to Lightning.

        This functions as an intermediary representation of the pipeline which
        is then deployed to the kubeflow pipelines instance.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()`
        method builds a docker image that contains the code for the
        pipeline, all steps the context around these files.

        Based on this docker image a callable is created which builds
        task for each step (`_construct_lightning_pipeline`).
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
            LightningOrchestratorSettings, self.get_settings(deployment)
        )
        if deployment.schedule:
            if (
                deployment.schedule.catchup
                or deployment.schedule.interval_second
            ):
                logger.warning(
                    "Lightning orchestrator only uses schedules with the "
                    "`cron_expression` property, with optional `start_time` and/or `end_time`. "
                    "All other properties are ignored."
                )
            if deployment.schedule.cron_expression is None:
                raise ValueError(
                    "Property `cron_expression` must be set when passing "
                    "schedule to a Lightning orchestrator."
                )
            if (
                deployment.schedule.cron_expression
                and settings.schedule_timezone is None
            ):
                raise ValueError(
                    "Property `schedule_timezone` must be set when passing "
                    "`cron_expression` to a Lightning orchestrator."
                    "Lightning orchestrator requires a Java Timezone ID to run the pipeline on schedule."
                    "Please refer to https://docs.oracle.com/middleware/1221/wcs/tag-ref/MISC/TimeZones.html for more information."
                )

        # Get deployment id
        deployment_id = deployment.id

        # Copy the repository to a temporary directory and add a setup.py file
        repository_temp_dir = (
            self.copy_repository_to_temp_dir_and_add_setup_py()
        )

        # Create a wheel for the package in the temporary directory
        wheel_path = self.create_wheel(temp_dir=repository_temp_dir)

        # Construct the env variables for the pipeline
        env_vars = environment.copy()
        orchestrator_run_id = str(uuid4())
        env_vars[ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID] = orchestrator_run_id
        # Set up some variables for configuration
        env_vars[ENV_ZENML_CUSTOM_SOURCE_ROOT] = (
            LIGHTNING_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH
        )

        # Create a single export command with all environment variables
        export_command = "export " + " ".join(
            [f"{key}='{value}'" for key, value in env_vars.items()]
        )
        steps = {}
        for step_name, step in deployment.step_configurations.items():
            # The arguments are passed to configure the entrypoint of the
            # docker container when the step is called.
            command = LightningEntrypointConfiguration.get_entrypoint_command()
            arguments = (
                LightningEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name,
                    deployment_id=deployment_id,
                    wheel_package=self.package_name,
                )
            )
            entrypoint = command + arguments
            entrypoint = " ".join(entrypoint)

            step_settings = cast(
                LightningOrchestratorSettings, self.get_settings(step)
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

            requirements_to_string = " ".join(f'"{req}"' for req in requirements)
            run_command = f"{export_command} && {entrypoint}"
            commands = [run_command]
            steps[step_name] = {
                "commands": commands,
                "requirements": requirements_to_string,
                "machine": step_settings.machine_type
                if step_settings != settings
                else None,
            }

        self._upload_and_run_pipeline(
            orchestrator_run_id,
            requirements_to_string,
            settings,
            steps,
            wheel_path,
        )
        fileio.rmtree(repository_temp_dir)

    def _upload_and_run_pipeline(
        self,
        orchestrator_run_id: str,
        requirements: str,
        settings: LightningOrchestratorSettings,
        steps_commands: Dict[str, Dict[str, str]],
        wheel_path: str,
    ) -> None:
        """Uploads and run the pipeline on the Lightning jobs.

        Args:
            orchestrator_run_id: The id of the orchestrator run.
            requirements: The requirements to install for the pipeline.
            settings: The settings of the orchestrator.
            steps_commands: The commands to run for each step.
            wheel_path: The path to the wheel file.
        """
        self._get_lightning_client()
        studio_name = sanitize_studio_name(
            f"zenml_{orchestrator_run_id}_pipeline"
        )
        studio = Studio(name=studio_name)
        studio.start(Machine(settings.machine_type))
        studio.upload_file(wheel_path)
        breakpoint()
        studio.run(f"pip install {requirements}")
        studio.run(
            "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git@feature/lightening-studio-orchestrator"
        )
        studio.run(f"pip install {wheel_path.rsplit('/', 1)[-1]}")
        for step_name, details in steps_commands.items():
            if details["machine"]:
                studio_name = sanitize_studio_name(
                    f"zenml_{orchestrator_run_id}_{step_name}"
                )
                studio = Studio(name=studio_name)
                studio.start(Machine(details["machine"]))
                studio.upload_file(wheel_path)
                studio.run(f"pip install {details['requirements']}")
                studio.run(
                    "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git@feature/lightening-studio-orchestrator"
                )
                studio.run(f"pip install {wheel_path.rsplit('/', 1)[-1]}")
                for command in details["commands"]:
                    output = studio.run(command)
                    logger.info(output)
                studio.delete()
            else:
                for command in details["commands"]:
                    output = studio.run(command)
                    logger.info(output)
        studio.delete()


def sanitize_studio_name(studio_name: str) -> str:
    """Sanitize studio_names so they conform to Kubernetes studio naming convention.

    Args:
        studio_name: Arbitrary input studio_name.

    Returns:
        Sanitized pod name.
    """
    studio_name = re.sub(r"[^a-z0-9-]", "-", studio_name.lower())
    studio_name = re.sub(r"^[-]+", "", studio_name)
    return re.sub(r"[-]+", "-", studio_name)
