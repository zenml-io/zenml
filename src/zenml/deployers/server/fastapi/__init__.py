#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""FastAPI implementation of the deployment app factory and adapters."""


from typing import List, Type
from zenml.deployers.server.app import BaseDeploymentAppRunner, BaseDeploymentAppRunnerFlavor

FASTAPI_APP_RUNNER_FLAVOR_NAME = "fastapi"

class FastAPIDeploymentAppRunnerFlavor(BaseDeploymentAppRunnerFlavor):
    """FastAPI deployment app runner flavor."""

    @property
    def name(self) -> str:
        """The name of the deployment app runner flavor.

        Returns:
            The name of the deployment app runner flavor.
        """
        return FASTAPI_APP_RUNNER_FLAVOR_NAME

    @property
    def implementation_class(self) -> Type[BaseDeploymentAppRunner]:
        """The class that implements the deployment app runner.

        Returns:
            The implementation class for the deployment app runner.
        """
        from zenml.deployers.server.fastapi.app import FastAPIDeploymentAppRunner
        return FastAPIDeploymentAppRunner

    @property
    def requirements(self) -> List[str]:
        """The software requirements for the deployment app runner.

        Returns:
            The software requirements for the deployment app runner.
        """
        return super().requirements + ["fastapi"]