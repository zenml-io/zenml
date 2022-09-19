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
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, List, Optional

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
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.environment import Environment as ZenMLEnvironment
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.step_operators import BaseStepOperator
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_ZENML_CONFIG_DIR,
    PipelineDockerImageBuilder,
    _include_global_config,
)
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.config.docker_configuration import DockerConfiguration
    from zenml.config.resource_configuration import ResourceConfiguration

logger = get_logger(__name__)


class AzureMLStepOperator(BaseStepOperator):
    """Step operator to run a step on AzureML.

    This class defines code that can set up an AzureML environment and run the
    ZenML entrypoint command in it.
    """

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
        docker_configuration: "DockerConfiguration",
        run_name: str,
    ) -> Environment:
        """Prepares the environment in which Azure will run all jobs.

        Args:
            workspace: The AzureML Workspace that has configuration
                for a storage account, container registry among other
                things.
            docker_configuration: The Docker configuration for this step.
            run_name: The name of the pipeline run that can be used
                for naming environments and runs.

        Returns:
            The AzureML Environment object.
        """
        docker_image_builder = PipelineDockerImageBuilder()
        requirements_files = docker_image_builder._gather_requirements_files(
            docker_configuration=docker_configuration,
            stack=Repository().active_stack,
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
        if self.config.environment_name:
            environment = Environment.get(
                workspace=workspace, name=self.config.environment_name
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

            parent_image = (
                docker_configuration.parent_image
                or self.config.docker_parent_image
            )

            if parent_image:
                # replace the default azure base image
                environment.docker.base_image = parent_image

        environment_variables = {
            "ENV_ZENML_PREVENT_PIPELINE_EXECUTION": "True",
        }
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

        environment_variables[
            ENV_ZENML_CONFIG_PATH
        ] = f"./{DOCKER_IMAGE_ZENML_CONFIG_DIR}"
        environment_variables.update(docker_configuration.environment)

        environment.environment_variables = environment_variables
        return environment

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        docker_configuration: "DockerConfiguration",
        entrypoint_command: List[str],
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Launches a step on AzureML.

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            docker_configuration: The Docker configuration for this step.
            entrypoint_command: Command that executes the step.
            resource_configuration: The resource configuration for this step.
        """
        if not resource_configuration.empty:
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
            "docker_target_repository",
            "dockerignore",
            "copy_files",
            "copy_global_config",
        ]
        ignored_docker_fields = (
            docker_configuration.__fields_set__.intersection(
                unused_docker_fields
            )
        )

        if ignored_docker_fields:
            logger.warning(
                "The AzureML step operator currently does not support all "
                "options defined in your Docker configuration. Ignoring all "
                "values set for the attributes: %s",
                ignored_docker_fields,
            )

        workspace = Workspace.get(
            subscription_id=self.config.subscription_id,
            resource_group=self.config.resource_group,
            name=self.config.workspace_name,
            auth=self._get_authentication(),
        )

        source_directory = get_source_root_path()
        with _include_global_config(
            build_context_root=source_directory,
            load_config_path=PurePosixPath(
                f"./{DOCKER_IMAGE_ZENML_CONFIG_DIR}"
            ),
        ):
            environment = self._prepare_environment(
                workspace=workspace,
                docker_configuration=docker_configuration,
                run_name=run_name,
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

            experiment = Experiment(workspace=workspace, name=pipeline_name)
            run = experiment.submit(config=run_config)

        run.display_name = run_name
        run.wait_for_completion(show_output=True)
