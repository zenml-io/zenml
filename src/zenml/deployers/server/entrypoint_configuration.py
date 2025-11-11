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
"""ZenML Pipeline Deployment Entrypoint Configuration."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import DeploymentResponse, PipelineSnapshotResponse
from zenml.utils import uuid_utils

logger = get_logger(__name__)

# Deployment-specific entrypoint options
DEPLOYMENT_ID_OPTION = "deployment_id"


class DeploymentEntrypointConfiguration(BaseEntrypointConfiguration):
    """Entrypoint configuration for ZenML Pipeline Deployment.

    This entrypoint configuration handles the startup and configuration
    of the ZenML pipeline deployment FastAPI application.
    """

    def __init__(self, arguments: List[str]):
        """Initializes the entrypoint configuration.

        Args:
            arguments: Command line arguments to configure this object.
        """
        super().__init__(arguments)
        self._deployment: Optional["DeploymentResponse"] = None

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for the deployment entrypoint.

        Returns:
            Set of required option names
        """
        return {
            DEPLOYMENT_ID_OPTION: True,
        }

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Gets arguments for the deployment entrypoint command.

        Args:
            **kwargs: Keyword arguments containing deployment configuration

        Returns:
            List of command-line arguments

        Raises:
            ValueError: If the deployment ID is not a valid UUID.
        """
        # Get base arguments (snapshot_id, etc.)
        base_args = super().get_entrypoint_arguments(**kwargs)

        deployment_id = kwargs.get(DEPLOYMENT_ID_OPTION)
        if not uuid_utils.is_valid_uuid(deployment_id):
            raise ValueError(
                f"Missing or invalid deployment ID as argument for entrypoint "
                f"configuration. Please make sure to pass a valid UUID to "
                f"`{cls.__name__}.{cls.get_entrypoint_arguments.__name__}"
                f"({DEPLOYMENT_ID_OPTION}=<UUID>)`."
            )

        # Add deployment-specific arguments with defaults
        deployment_args = [
            f"--{DEPLOYMENT_ID_OPTION}",
            str(kwargs.get(DEPLOYMENT_ID_OPTION, "")),
        ]

        return base_args + deployment_args

    @property
    def snapshot(self) -> "PipelineSnapshotResponse":
        """The snapshot configured for this entrypoint configuration.

        Returns:
            The snapshot.

        Raises:
            RuntimeError: If the deployment has no snapshot.
        """
        if self._snapshot is None:
            snapshot = self.deployment.snapshot
            if snapshot is None:
                raise RuntimeError(
                    f"Deployment {self.deployment.id} has no snapshot"
                )
            self._snapshot = snapshot
        return self._snapshot

    @property
    def deployment(self) -> "DeploymentResponse":
        """The deployment configured for this entrypoint configuration.

        Returns:
            The deployment.
        """
        if self._deployment is None:
            self._deployment = self._load_deployment()
        return self._deployment

    def _load_deployment(self) -> "DeploymentResponse":
        """Loads the deployment.

        Returns:
            The deployment.
        """
        deployment_id = UUID(self.entrypoint_args[DEPLOYMENT_ID_OPTION])
        deployment = Client().zen_store.get_deployment(
            deployment_id=deployment_id
        )
        return deployment

    def run(self) -> None:
        """Run the ZenML pipeline deployment application.

        This method starts the FastAPI server with the configured parameters
        and the specified pipeline deployment.
        """
        from zenml.deployers.server.app import BaseDeploymentAppRunner

        # Activate integrations to ensure all components are available
        integration_registry.activate_integrations()

        # Download code if necessary (for remote execution environments)
        self.download_code_if_necessary()

        app_runner = BaseDeploymentAppRunner.load_app_runner(self.deployment)
        app_runner.run()
