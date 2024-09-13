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

import os
import tempfile
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast
from uuid import uuid4

from lightning_sdk import Machine, Studio

from zenml.constants import (
    ENV_ZENML_CUSTOM_SOURCE_ROOT,
    ENV_ZENML_WHEEL_PACKAGE_NAME,
)
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.lightning.flavors.lightning_orchestrator_flavor import (
    LightningOrchestratorConfig,
    LightningOrchestratorSettings,
)
from zenml.integrations.lightning.orchestrators.lightning_orchestrator_entrypoint_configuration import (
    LightningOrchestratorEntrypointConfiguration,
)
from zenml.integrations.lightning.orchestrators.utils import (
    gather_requirements,
    sanitize_studio_name,
)
from zenml.logger import get_logger
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.orchestrators.wheeled_orchestrator import WheeledOrchestrator
from zenml.stack import StackValidator
from zenml.utils import code_utils, io_utils, source_utils

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

                # return False, (
                #    f"The Lightning orchestrator runs pipelines remotely, "
                #    f"but the '{component.name}' {component.type.value} is "
                #    "a local stack component and will not be available in "
                #    "the Lightning step.\nPlease ensure that you always "
                #    "use non-local stack components with the Lightning "
                #    "orchestrator."
                # )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_remote_components,
        )

    def _set_lightning_env_vars(
        self,
        deployment: "PipelineDeploymentResponse",
    ) -> None:
        """Set up the Lightning client using environment variables.

        Args:
            deployment: The pipeline deployment to prepare or run.

        Raises:
            ValueError: If the user id and api key or username and organization
        """
        settings = cast(
            LightningOrchestratorSettings, self.get_settings(deployment)
        )
        if not settings.user_id or not settings.api_key:
            raise ValueError(
                "Lightning orchestrator requires either `user_id` and `api_key` to be set in the settings."
            )
        if settings.user_id and settings.api_key:
            os.environ["LIGHTNING_USER_ID"] = settings.user_id
            os.environ["LIGHTNING_API_KEY"] = settings.api_key
            if settings.username:
                os.environ["LIGHTNING_USERNAME"] = settings.username
            elif settings.organization:
                os.environ["LIGHTNING_ORG"] = settings.organization
            else:
                raise ValueError(
                    "Lightning orchestrator requires either `username` or `organization` to be set in the settings."
                )
            if settings.teamspace:
                os.environ["LIGHTNING_TEAMSPACE"] = settings.teamspace
        else:
            raise ValueError(
                "Lightning orchestrator requires either `user_id` and `api_key` or `username` or `organization` to be set in the settings."
            )

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
            if deployment.schedule.cron_expression:
                raise ValueError(
                    "Property `schedule_timezone` must be set when passing "
                    "`cron_expression` to a Lightning orchestrator."
                    "Lightning orchestrator requires a Java Timezone ID to run the pipeline on schedule."
                    "Please refer to https://docs.oracle.com/middleware/1221/wcs/tag-ref/MISC/TimeZones.html for more information."
                )

        # Get deployment id
        deployment_id = deployment.id

        pipeline_name = deployment.pipeline_configuration.name
        orchestrator_run_name = get_orchestrator_run_name(pipeline_name)

        # Copy the repository to a temporary directory and add a setup.py file
        # repository_temp_dir = (
        #    self.copy_repository_to_temp_dir_and_add_setup_py()
        # )

        # Create a wheel for the package in the temporary directory
        # wheel_path = self.create_wheel(temp_dir=repository_temp_dir)
        code_archive = code_utils.CodeArchive(
            root=source_utils.get_source_root()
        )
        logger.info("Archiving pipeline code...")
        with tempfile.NamedTemporaryFile(
            mode="w+b", delete=False, suffix=".tar.gz"
        ) as code_file:
            code_archive.write_archive(code_file)
            code_path = code_file.name
        filename = f"{orchestrator_run_name}.tar.gz"
        # Construct the env variables for the pipeline
        env_vars = environment.copy()
        orchestrator_run_id = str(uuid4())
        env_vars[ENV_ZENML_LIGHTNING_ORCHESTRATOR_RUN_ID] = orchestrator_run_id
        # Set up some variables for configuration
        env_vars[ENV_ZENML_CUSTOM_SOURCE_ROOT] = (
            LIGHTNING_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH
        )
        env_vars[ENV_ZENML_WHEEL_PACKAGE_NAME] = self.package_name

        # Create a line-by-line export of environment variables
        env_exports = "\n".join(
            [f"export {key}='{value}'" for key, value in env_vars.items()]
        )

        # Write the environment variables to a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".studiorc"
        ) as temp_file:
            temp_file.write(env_exports)
            env_file_path = temp_file.name

        # Gather the requirements
        pipeline_docker_settings = (
            deployment.pipeline_configuration.docker_settings
        )
        pipeline_requirements = gather_requirements(pipeline_docker_settings)
        pipeline_requirements_to_string = " ".join(
            f'"{req}"' for req in pipeline_requirements
        )

        def _construct_lightning_steps(
            deployment: "PipelineDeploymentResponse",
        ) -> Dict[str, Dict[str, Any]]:
            """Construct the steps for the pipeline.

            Args:
                deployment: The pipeline deployment to prepare or run.

            Returns:
                The steps for the pipeline.
            """
            steps = {}
            for step_name, step in deployment.step_configurations.items():
                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                entrypoint_command = (
                    StepEntrypointConfiguration.get_entrypoint_command()
                )
                entrypoint_arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name,
                        deployment_id=deployment_id,
                    )
                )
                entrypoint = entrypoint_command + entrypoint_arguments
                entrypoint_string = " ".join(entrypoint)

                step_settings = cast(
                    LightningOrchestratorSettings, self.get_settings(step)
                )

                # Gather the requirements
                step_docker_settings = step.config.docker_settings
                step_requirements = gather_requirements(step_docker_settings)
                step_requirements_to_string = " ".join(
                    f'"{req}"' for req in step_requirements
                )

                # Construct the command to run the step
                run_command = f"{entrypoint_string}"
                commands = [run_command]
                steps[step_name] = {
                    "commands": commands,
                    "requirements": step_requirements_to_string,
                    "machine": step_settings.machine_type
                    if step_settings != settings
                    else None,
                }
            return steps

        if not settings.synchronous:
            entrypoint_command = LightningOrchestratorEntrypointConfiguration.get_entrypoint_command()
            entrypoint_arguments = LightningOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                run_name=orchestrator_run_name,
                deployment_id=deployment.id,
            )
            entrypoint = entrypoint_command + entrypoint_arguments
            entrypoint_string = " ".join(entrypoint)
            logger.info("Setting up Lightning AI client")
            self._set_lightning_env_vars(deployment)

            studio_name = sanitize_studio_name(
                "zenml_async_orchestrator_studio"
            )
            logger.info(f"Creating main studio: {studio_name}")
            studio = Studio(name=studio_name)
            studio.start()

            logger.info(
                "Uploading wheel package and installing dependencies on main studio"
            )
            studio.run(
                f"mkdir -p /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]}"
            )
            studio.upload_file(
                code_path,
                remote_path=f"/teamspace/studios/this_studio/zenml_codes/{filename}",
            )
            time.sleep(10)
            studio.run(
                f"tar -xvzf /teamspace/studios/this_studio/zenml_codes/{filename} -C /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]}"
            )
            studio.upload_file(
                env_file_path,
                remote_path="/teamspace/studios/this_studio/.lightning_studio/.studiorc",
            )
            studio.run("pip install uv")
            logger.info(
                f"Installing requirements: {pipeline_requirements_to_string}"
            )
            studio.run(f"uv pip install {pipeline_requirements_to_string}")
            studio.run(
                "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git"
            )

            for custom_command in settings.custom_commands or []:
                studio.run(
                    f"cd /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]} && {custom_command}"
                )
            # studio.run(f"pip install {wheel_path.rsplit('/', 1)[-1]}")
            logger.info("Running pipeline in async mode")
            studio.run(
                f"nohup bash -c 'cd /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]} && {entrypoint_string}' > log_{filename.rsplit('.', 2)[0]}.txt 2>&1 &"
            )
            logger.info(
                f"The pipeline is running in async mode, you can keep checking the logs by running the following command: `lightning download -s vision-model/zenml-async-orchestrator-studio -p /teamspace/studios/this_studio/log_{filename.rsplit('.', 2)[0]}.txt && cat log_{filename.rsplit('.', 2)[0]}.txt`"
            )
        else:
            self._upload_and_run_pipeline(
                deployment,
                orchestrator_run_id,
                pipeline_requirements_to_string,
                settings,
                _construct_lightning_steps(deployment),
                code_path,
                filename,
                env_file_path,
            )
        os.unlink(env_file_path)

    def _upload_and_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        orchestrator_run_id: str,
        requirements: str,
        settings: LightningOrchestratorSettings,
        steps_commands: Dict[str, Dict[str, Any]],
        code_path: str,
        filename: str,
        env_file_path: str,
    ) -> None:
        """Upload and run the pipeline on Lightning Studio.

        Args:
            deployment: The pipeline deployment to prepare or run.
            orchestrator_run_id: The orchestrator run id.
            requirements: The requirements for the pipeline.
            settings: The orchestrator settings.
            steps_commands: The commands for the steps.
            code_path: The path to the wheel package.
            filename: The name of the code archive.
            env_file_path: The path to the environment file.

        Raises:
            Exception: If an error occurs while running the pipeline.
        """
        logger.info("Setting up Lightning AI client")
        self._set_lightning_env_vars(deployment)

        if settings.main_studio_name:
            studio_name = settings.main_studio_name
            studio = Studio(name=studio_name)
            if (
                studio.machine != settings.machine_type
                and settings.machine_type
            ):
                studio.switch_machine(Machine(settings.machine_type))
        else:
            studio_name = sanitize_studio_name(
                f"zenml_{orchestrator_run_id}_pipeline"
            )
            logger.info(f"Creating main studio: {studio_name}")
            studio = Studio(name=studio_name)
            if settings.machine_type:
                studio.start(Machine(settings.machine_type))
            else:
                studio.start()
        try:
            studio.run(
                f"mkdir -p /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]}"
            )
            studio.upload_file(
                code_path,
                remote_path=f"/teamspace/studios/this_studio/zenml_codes/{filename}",
            )
            studio.upload_file(
                "/var/folders/0_/5_j3kkj525s3yz7tt0y3jb0r0000gn/T/tmphfwgyyzc.tar.gz",
            )
            studio.run(
                f"tar -xvzf /teamspace/studios/this_studio/zenml_codes/{filename} -C /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]}"
            )
            logger.info(
                "Uploading wheel package and installing dependencies on main studio"
            )
            studio.upload_file(
                env_file_path,
                remote_path="/teamspace/studios/this_studio/.lightning_studio/.studiorc",
            )
            studio.run("pip install uv")
            studio.run(f"uv pip install {requirements}")
            studio.run(
                "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git"
            )
            # studio.run(f"pip install {wheel_path.rsplit('/', 1)[-1]}")
            for command in settings.custom_commands or []:
                output = studio.run(
                    f"cd /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]} && {command}"
                )
                logger.info(f"Custom command output: {output}")

            for step_name, details in steps_commands.items():
                if details["machine"]:
                    logger.info(f"Executing step: {step_name} in new studio")
                    self._run_step_in_new_studio(
                        orchestrator_run_id,
                        step_name,
                        details,
                        code_path,
                        filename,
                        env_file_path,
                        settings.custom_commands,
                    )
                else:
                    logger.info(f"Executing step: {step_name} in main studio")
                    self._run_step_in_main_studio(studio, details, filename)
        except Exception as e:
            logger.error(f"Error running pipeline: {e}")
            raise e
        finally:
            if (
                studio.status != studio.status.NotCreated
                and settings.main_studio_name is None
            ):
                logger.info("Deleting main studio")
                studio.delete()

    def _run_step_in_new_studio(
        self,
        orchestrator_run_id: str,
        step_name: str,
        details: Dict[str, Any],
        code_path: str,
        filename: str,
        env_file_path: str,
        custom_commands: Optional[List[str]] = None,
    ) -> None:
        """Run a step in a new studio.

        Args:
            orchestrator_run_id: The orchestrator run id.
            step_name: The name of the step.
            details: The details of the step.
            code_path: The path to the wheel package.
            filename: The name of the code archive.
            env_file_path: The path to the environment file.
            custom_commands: Custom commands to run.
        """
        studio_name = sanitize_studio_name(
            f"zenml_{orchestrator_run_id}_{step_name}"
        )
        logger.info(f"Creating new studio for step {step_name}: {studio_name}")
        studio = Studio(name=studio_name)
        studio.start(Machine(details["machine"]))
        studio.run(
            f"mkdir -p /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]}"
        )
        studio.upload_file(code_path, remote_path=f"/zenml_codes/{filename}")
        studio.run(
            f"tar -xvzf /teamspace/studios/this_studio/zenml_codes/{filename} -C /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]}"
        )
        studio.upload_file(
            env_file_path, remote_path=".lightning_studio/.studiorc"
        )
        studio.run("pip install uv")
        studio.run(f"uv pip install {details['requirements']}")
        studio.run(
            "pip uninstall zenml -y && pip install git+https://github.com/zenml-io/zenml.git"
        )
        # studio.run(f"pip install {wheel_path.rsplit('/', 1)[-1]}")
        for command in custom_commands or []:
            output = studio.run(
                f"cd /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]} && {command}"
            )
            logger.info(f"Custom command output: {output}")
        for command in details["commands"]:
            output = studio.run(
                f"cd /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]} && {command}"
            )
            logger.info(f"Step {step_name} output: {output}")
        studio.delete()

    def _run_step_in_main_studio(
        self, studio: Studio, details: Dict[str, Any], filename: str
    ) -> None:
        """Run a step in the main studio.

        Args:
            studio: The studio to run the step in.
            details: The details of the step.
            filename: The name of the code archive.
        """
        for command in details["commands"]:
            output = studio.run(
                f"cd /teamspace/studios/this_studio/zenml_codes/{filename.rsplit('.', 2)[0]} && {command}"
            )
            logger.info(f"Step output: {output}")
