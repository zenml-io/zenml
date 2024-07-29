#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to deploy a ZenML stack to a cloud provider."""

import datetime
from abc import abstractmethod
from typing import ClassVar, Dict, List, Optional

from pydantic import BaseModel

from zenml.client import Client
from zenml.enums import StackComponentType, StackDeploymentProvider
from zenml.models import (
    DeployedStack,
    StackDeploymentConfig,
    StackDeploymentInfo,
)


class ZenMLCloudStackDeployment(BaseModel):
    """ZenML Cloud Stack CLI Deployment base class."""

    provider: ClassVar[StackDeploymentProvider]
    deployment: ClassVar[str]
    stack_name: str
    zenml_server_url: str
    zenml_server_api_token: str
    location: Optional[str] = None

    @classmethod
    @abstractmethod
    def description(cls) -> str:
        """Return a description of the ZenML Cloud Stack Deployment.

        This will be displayed when the user is prompted to deploy
        the ZenML stack.

        Returns:
            A MarkDown description of the ZenML Cloud Stack Deployment.
        """

    @classmethod
    @abstractmethod
    def instructions(cls) -> str:
        """Return instructions on how to deploy the ZenML stack to the specified cloud provider.

        This will be displayed before the user is prompted to deploy the ZenML
        stack.

        Returns:
            MarkDown instructions on how to deploy the ZenML stack to the
            specified cloud provider.
        """

    @classmethod
    @abstractmethod
    def post_deploy_instructions(cls) -> str:
        """Return instructions on what to do after the deployment is complete.

        This will be displayed after the deployment is complete.

        Returns:
            MarkDown instructions on what to do after the deployment is
            complete.
        """

    @classmethod
    @abstractmethod
    def integrations(cls) -> List[str]:
        """Return the ZenML integrations required for the stack.

        Returns:
            The list of ZenML integrations that need to be installed for the
            stack to be usable.
        """

    @classmethod
    @abstractmethod
    def permissions(cls) -> Dict[str, List[str]]:
        """Return the permissions granted to ZenML to access the cloud resources.

        Returns:
            The permissions granted to ZenML to access the cloud resources, as
            a dictionary grouping permissions by resource.
        """

    @classmethod
    @abstractmethod
    def locations(cls) -> Dict[str, str]:
        """Return the locations where the ZenML stack can be deployed.

        Returns:
            The regions where the ZenML stack can be deployed as a map of region
            names to region descriptions.
        """

    @classmethod
    def skypilot_default_regions(cls) -> Dict[str, str]:
        """Returns the regions supported by default for the Skypilot.

        Returns:
            The regions supported by default for the Skypilot.
        """
        return cls.locations()

    @classmethod
    def get_deployment_info(cls) -> StackDeploymentInfo:
        """Return information about the ZenML Cloud Stack Deployment.

        Returns:
            Information about the ZenML Cloud Stack Deployment.
        """
        return StackDeploymentInfo(
            provider=cls.provider,
            description=cls.description(),
            instructions=cls.instructions(),
            post_deploy_instructions=cls.post_deploy_instructions(),
            integrations=cls.integrations(),
            permissions=cls.permissions(),
            locations=cls.locations(),
            skypilot_default_regions=cls.skypilot_default_regions(),
        )

    @abstractmethod
    def get_deployment_config(
        self,
    ) -> StackDeploymentConfig:
        """Return the configuration to deploy the ZenML stack to the specified cloud provider.

        The configuration should include:

        * a cloud provider console URL where the user will be redirected to
        deploy the ZenML stack. The URL should include as many pre-filled
        URL query parameters as possible.
        * a textual description of the URL
        * some deployment providers may require additional configuration
        parameters or scripts to be passed to the cloud provider in addition to
        the deployment URL query parameters. Where that is the case, this method
        should also return a string that the user can copy and paste into the
        cloud provider console to deploy the ZenML stack (e.g. a set of
        environment variables, YAML configuration snippet, bash or Terraform
        script etc.).

        Returns:
            The configuration or script to deploy the ZenML stack to the
            specified cloud provider.
        """

    def get_stack(
        self, date_start: Optional[datetime.datetime] = None
    ) -> Optional[DeployedStack]:
        """Return the ZenML stack that was deployed and registered.

        This method is called to retrieve a ZenML stack matching the deployment
        provider.

        Args:
            date_start: The date when the deployment started.

        Returns:
            The ZenML stack that was deployed and registered or None if a
            matching stack was not found.
        """
        client = Client()

        # It's difficult to find a stack that matches the CloudFormation
        # deployment 100% because the user can change the stack name before they
        # deploy the stack in GCP.
        #
        # We try to find a full GCP stack that matches the deployment provider
        # that was registered after this deployment was created.

        # Get all stacks created after the start date
        stacks = client.list_stacks(
            created=f"gt:{str(date_start.replace(microsecond=0))}"
            if date_start
            else None,
            sort_by="desc:created",
            size=50,
        )

        if not stacks.items:
            return None

        # Find a stack that best matches the deployment provider
        for stack in stacks.items:
            if not stack.labels:
                continue

            if stack.labels.get("zenml:provider") != self.provider.value:
                continue

            if stack.labels.get("zenml:deployment") != self.deployment:
                continue

            artifact_store = stack.components[
                StackComponentType.ARTIFACT_STORE
            ][0]

            if not artifact_store.connector:
                continue

            return DeployedStack(
                stack=stack,
                service_connector=artifact_store.connector,
            )

        return None
