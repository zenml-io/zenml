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

import os
from typing import ClassVar, List, Optional

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

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.environment import Environment as ZenMLEnvironment
from zenml.integrations.azureml import AZUREML_STEP_OPERATOR_FLAVOR
from zenml.io import fileio
from zenml.step_operators import BaseStepOperator
from zenml.utils.docker_utils import CONTAINER_ZENML_CONFIG_DIR
from zenml.utils.source_utils import get_source_root_path


class AzureMLStepOperator(BaseStepOperator):
    """Step operator to run a step on AzureML.

    This class defines code that can set up an AzureML environment and run the
    ZenML entrypoint command in it.

    Attributes:
        subscription_id: The Azure account's subscription ID
        resource_group: The resource group to which the AzureML workspace
            is deployed.
        workspace_name: The name of the AzureML Workspace.
        compute_target_name: The name of the configured ComputeTarget.
            An instance of it has to be created on the portal if it doesn't
            exist already.
        environment_name: [Optional] The name of the environment if there
            already exists one.
        docker_base_image: [Optional] The custom docker base image that the
            environment should use.
        tenant_id: The Azure Tenant ID.
        service_principal_id: The ID for the service principal that is created
            to allow apps to access secure resources.
        service_principal_password: Password for the service principal.
    """

    subscription_id: str
    resource_group: str
    workspace_name: str
    compute_target_name: str

    # Environment
    environment_name: Optional[str] = None
    docker_base_image: Optional[str] = None

    # Service principal authentication
    # https://docs.microsoft.com/en-us/azure/machine-learning/how-to-setup-authentication#configure-a-service-principal
    tenant_id: Optional[str] = None
    service_principal_id: Optional[str] = None
    service_principal_password: Optional[str] = None

    # Class Configuration
    FLAVOR: ClassVar[str] = AZUREML_STEP_OPERATOR_FLAVOR

    def _get_authentication(self) -> Optional[AbstractAuthentication]:
        if (
            self.tenant_id
            and self.service_principal_id
            and self.service_principal_password
        ):
            return ServicePrincipalAuthentication(
                tenant_id=self.tenant_id,
                service_principal_id=self.service_principal_id,
                service_principal_password=self.service_principal_password,
            )
        return None

    def _prepare_environment(
        self, workspace: Workspace, requirements: List[str], run_name: str
    ) -> Environment:
        """Prepares the environment in which Azure will run all jobs.

        Args:
            workspace: The AzureML Workspace that has configuration
                for a storage account, container registry among other
                things.
            requirements: The list of requirements to be installed
                in the environment.
            run_name: The name of the pipeline run that can be used
                for naming environments and runs.
        """
        if self.environment_name:
            environment = Environment.get(
                workspace=workspace, name=self.environment_name
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

            if self.docker_base_image:
                # replace the default azure base image
                environment.docker.base_image = self.docker_base_image

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
        ] = f"./{CONTAINER_ZENML_CONFIG_DIR}"

        environment.environment_variables = environment_variables
        return environment

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> None:
        """Launches a step on AzureML.

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            entrypoint_command: Command that executes the step.
            requirements: List of pip requirements that must be installed
                inside the step operator environment.
        """
        workspace = Workspace.get(
            subscription_id=self.subscription_id,
            resource_group=self.resource_group,
            name=self.workspace_name,
            auth=self._get_authentication(),
        )

        source_directory = get_source_root_path()
        config_path = os.path.join(source_directory, CONTAINER_ZENML_CONFIG_DIR)
        try:

            # Save a copy of the current global configuration with the
            # active profile contents into the build context, to have
            # the configured stacks accessible from within the Azure ML
            # environment.
            GlobalConfiguration().copy_active_configuration(
                config_path,
                load_config_path=f"./{CONTAINER_ZENML_CONFIG_DIR}",
            )

            environment = self._prepare_environment(
                workspace=workspace,
                requirements=requirements,
                run_name=run_name,
            )
            compute_target = ComputeTarget(
                workspace=workspace, name=self.compute_target_name
            )

            run_config = ScriptRunConfig(
                source_directory=source_directory,
                environment=environment,
                compute_target=compute_target,
                command=entrypoint_command,
            )

            experiment = Experiment(workspace=workspace, name=pipeline_name)
            run = experiment.submit(config=run_config)

        finally:
            # Clean up the temporary build files
            fileio.rmtree(config_path)

        run.display_name = run_name
        run.wait_for_completion(show_output=True)
