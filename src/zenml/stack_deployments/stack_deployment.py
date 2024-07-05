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
from typing import ClassVar, Dict, List, Optional, Tuple

from pydantic import BaseModel

from zenml.enums import StackDeploymentProvider
from zenml.models import (
    DeployedStack,
)


class ZenMLCloudStackDeployment(BaseModel):
    """ZenML Cloud Stack CLI Deployment base class."""

    provider: ClassVar[StackDeploymentProvider]
    stack_name: str
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

    @abstractmethod
    def deploy_url(
        self,
        zenml_server_url: str,
        zenml_server_api_token: str,
    ) -> Tuple[str, str]:
        """Return the URL to deploy the ZenML stack to the specified cloud provider.

        The URL should point to a cloud provider console where the user can
        deploy the ZenML stack and should include as many pre-filled parameters
        as possible.

        Args:
            zenml_server_url: The URL of the ZenML server.
            zenml_server_api_token: The API token to authenticate with the ZenML
                server.

        Returns:
            The URL to deploy the ZenML stack to the specified cloud provider
            and a text description of the URL.
        """

    @abstractmethod
    def get_stack(
        self,
        date_start: Optional[datetime.datetime] = None,
    ) -> Optional[DeployedStack]:
        """Return the ZenML stack that was deployed and registered.

        This method is called to retrieve a ZenML stack matching the deployment
        provider and stack name.

        Args:
            date_start: The start date of the deployment.

        Returns:
            The ZenML stack that was deployed and registered or None if the
            stack was not found.
        """
