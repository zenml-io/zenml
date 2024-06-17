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
"""Implementation of the ZenML AzureML Step Operator."""

import itertools
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from azureml.core import (
    ComputeTarget,
    Environment,
    Experiment,
    ScriptRunConfig,
    Workspace,
)
from azureml.core.authentication import (
    AbstractAuthentication,
    ServicePrincipalAuthentication,
)
from azureml.core.conda_dependencies import CondaDependencies

import zenml
from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_CONFIG_PATH,
)
from zenml.environment import Environment as ZenMLEnvironment
from zenml.integrations.azure.flavors.azureml_step_operator_flavor import (
    AzureMLStepOperatorConfig,
    AzureMLStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.utils import source_utils
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_ZENML_CONFIG_DIR,
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)


class AzureMLStepOperator(BaseStepOperator):
    """Step operator to run a step on AzureML.

    This class defines code that can set up an AzureML environment and run the
    ZenML entrypoint command in it.
    """

    @property
    def config(self) -> AzureMLStepOperatorConfig:
        """Returns the `AzureMLStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureMLStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AzureML step operator.

        Returns:
            The settings class.
        """
        return AzureMLStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote artifact
            store.
        """

        def _validate_remote_artifact_store(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The AzureML step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the AzureML "
                    "step operator."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_remote_artifact_store,
        )

    def _get_authentication(self) -> Optional[AbstractAuthentication]:
        """Returns the authentication object for the AzureML environment.

        Returns:
            The authentication object for the AzureML environment.
        """
        if (
            self.config.tenant_id
            and self.config.service_principal_id
            and self.config.service_principal_password
        ):
            return ServicePrincipalAuthentication(
                tenant_id=self.config.tenant_id,
                service_principal_id=self.config.service_principal_id,
                service_principal_password=self.config.service_principal_password,
            )
        return None

    def _prepare_environment(
        self,
        workspace: Workspace,
        docker_settings: "DockerSettings",
        run_name: str,
        environment_variables: Dict[str, str],
        environment_name: Optional[str] = None,
    ) -> Environment:
        """Prepares the environment in which Azure will run all jobs.

        Args:
            workspace: The AzureML Workspace that has configuration
                for a storage account, container registry among other
                things.
            docker_settings: The Docker settings for this step.
            run_name: The name of the pipeline run that can be used
                for naming environments and runs.
            environment_variables: Environment variables to set in the
                environment.
            environment_name: Optional name of an existing environment to use.

        Returns:
            The AzureML Environment object.
        """
        docker_image_builder = PipelineDockerImageBuilder()
        requirements_files = docker_image_builder.gather_requirements_files(
            docker_settings=docker_settings,
            stack=Client().active_stack,
            log=False,
        )
        requirements = list(
            itertools.chain.from_iterable(
                r[1].split("\n") for r in requirements_files
            )
        )
        requirements.append(f"zenml=={zenml.__version__}")
        logger.info(
            "Using requirements for AzureML step operator environment: %s",
            requirements,
        )
        if environment_name:
            environment = Environment.get(
                workspace=workspace, name=environment_name
            )
            if not environment.python.conda_dependencies:
                environment.python.conda_dependencies = (
                    CondaDependencies.create(
                        python_version=ZenMLEnvironment.python_version()
                    )
                )

            for requirement in requirements:
                environment.python.conda_dependencies.add_pip_package(
                    requirement
                )
        else:
            environment = Environment(name=f"zenml-{run_name}")
            environment.python.conda_dependencies = CondaDependencies.create(
                pip_packages=requirements,
                python_version=ZenMLEnvironment.python_version(),
            )

            if docker_settings.parent_image:
                # replace the default azure base image
                environment.docker.base_image = docker_settings.parent_image

        # set credentials to access azure storage
        for key in [
            "AZURE_STORAGE_ACCOUNT_KEY",
            "AZURE_STORAGE_ACCOUNT_NAME",
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_SAS_TOKEN",
        ]:
            value = os.getenv(key)
            if value:
                environment_variables[key] = value

        environment_variables[ENV_ZENML_CONFIG_PATH] = (
            f"./{DOCKER_IMAGE_ZENML_CONFIG_DIR}"
        )
        environment_variables.update(docker_settings.environment)
        environment.environment_variables = environment_variables
        return environment

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on AzureML.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        if not info.config.resource_settings.empty:
            logger.warning(
                "Specifying custom step resources is not supported for "
                "the AzureML step operator. If you want to run this step "
                "operator on specific resources, you can do so by creating an "
                "Azure compute target (https://docs.microsoft.com/en-us/azure/machine-learning/concept-compute-target) "
                "with a specific machine type and then updating this step "
                "operator: `zenml step-operator update %s "
                "--compute_target_name=<COMPUTE_TARGET_NAME>`",
                self.name,
            )

        unused_docker_fields = [
            "dockerfile",
            "build_context_root",
            "build_options",
            "skip_build",
            "target_repository",
            "dockerignore",
            "copy_files",
            "copy_global_config",
            "apt_packages",
            "user",
            "source_files",
        ]
        docker_settings = info.config.docker_settings
        ignored_docker_fields = docker_settings.__fields_set__.intersection(
            unused_docker_fields
        )

        if ignored_docker_fields:
            logger.warning(
                "The AzureML step operator currently does not support all "
                "options defined in your Docker settings. Ignoring all "
                "values set for the attributes: %s",
                ignored_docker_fields,
            )

        settings = cast(AzureMLStepOperatorSettings, self.get_settings(info))

        workspace = Workspace.get(
            subscription_id=self.config.subscription_id,
            resource_group=self.config.resource_group,
            name=self.config.workspace_name,
            auth=self._get_authentication(),
        )

        source_directory = source_utils.get_source_root()

        environment = self._prepare_environment(
            workspace=workspace,
            docker_settings=docker_settings,
            run_name=info.run_name,
            environment_variables=environment,
            environment_name=settings.environment_name,
        )
        compute_target = ComputeTarget(
            workspace=workspace, name=self.config.compute_target_name
        )

        run_config = ScriptRunConfig(
            source_directory=source_directory,
            environment=environment,
            compute_target=compute_target,
            command=entrypoint_command,
        )

        experiment = Experiment(workspace=workspace, name=info.pipeline.name)
        run = experiment.submit(config=run_config)

        run.display_name = info.run_name
        info.force_write_logs()
        run.wait_for_completion(show_output=True)
