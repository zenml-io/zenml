#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

import os
from typing import Any, List, Set
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models.v2.core.pipeline_snapshot import PipelineSnapshotResponse
from zenml.utils import uuid_utils

logger = get_logger(__name__)

# Deployment-specific entrypoint options
DEPLOYMENT_ID_OPTION = "deployment_id"
HOST_OPTION = "host"
PORT_OPTION = "port"
WORKERS_OPTION = "workers"
LOG_LEVEL_OPTION = "log_level"
CREATE_RUNS_OPTION = "create_runs"
AUTH_KEY_OPTION = "auth_key"


class DeploymentEntrypointConfiguration(BaseEntrypointConfiguration):
    """Entrypoint configuration for ZenML Pipeline Deployment.

    This entrypoint configuration handles the startup and configuration
    of the ZenML pipeline deployment FastAPI application.
    """

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for the deployment entrypoint.

        Returns:
            Set of required option names
        """
        return {
            DEPLOYMENT_ID_OPTION,
            HOST_OPTION,
            PORT_OPTION,
            WORKERS_OPTION,
            LOG_LEVEL_OPTION,
            CREATE_RUNS_OPTION,
            AUTH_KEY_OPTION,
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
            f"--{HOST_OPTION}",
            str(kwargs.get(HOST_OPTION, "0.0.0.0")),  # nosec
            f"--{PORT_OPTION}",
            str(kwargs.get(PORT_OPTION, 8001)),
            f"--{WORKERS_OPTION}",
            str(kwargs.get(WORKERS_OPTION, 1)),
            f"--{LOG_LEVEL_OPTION}",
            str(kwargs.get(LOG_LEVEL_OPTION, "info")),
            f"--{CREATE_RUNS_OPTION}",
            str(kwargs.get(CREATE_RUNS_OPTION, "false")),
            f"--{AUTH_KEY_OPTION}",
            str(kwargs.get(AUTH_KEY_OPTION, "")),
        ]

        return base_args + deployment_args

    def load_snapshot(self) -> "PipelineSnapshotResponse":
        """Loads the deployment snapshot.

        Returns:
            The deployment snapshot.

        Raises:
            RuntimeError: If the deployment has no snapshot.
        """
        deployment_id = UUID(self.entrypoint_args[DEPLOYMENT_ID_OPTION])
        deployment = Client().zen_store.get_deployment(
            deployment_id=deployment_id
        )
        if deployment.snapshot is None:
            raise RuntimeError("Deployment has no snapshot")
        return deployment.snapshot

    def run(self) -> None:
        """Run the ZenML pipeline deployment application.

        This method starts the FastAPI server with the configured parameters
        and the specified pipeline deployment.

        Raises:
            Exception: If the server fails to start.
        """
        import uvicorn

        # Activate integrations to ensure all components are available
        integration_registry.activate_integrations()

        # Extract configuration from entrypoint args
        deployment_id = self.entrypoint_args[DEPLOYMENT_ID_OPTION]
        host = self.entrypoint_args.get(HOST_OPTION, "0.0.0.0")  # nosec
        port = int(self.entrypoint_args.get(PORT_OPTION, 8001))
        workers = int(self.entrypoint_args.get(WORKERS_OPTION, 1))
        log_level = self.entrypoint_args.get(LOG_LEVEL_OPTION, "info")
        create_runs = (
            self.entrypoint_args.get(CREATE_RUNS_OPTION, "false").lower()
            == "true"
        )
        auth_key = self.entrypoint_args.get(AUTH_KEY_OPTION, None)

        snapshot = self.load_snapshot()

        # Download code if necessary (for remote execution environments)
        self.download_code_if_necessary(snapshot=snapshot)

        # Set environment variables for the deployment application
        os.environ["ZENML_DEPLOYMENT_ID"] = deployment_id
        if create_runs:
            os.environ["ZENML_DEPLOYMENT_CREATE_RUNS"] = "true"
        if auth_key:
            os.environ["ZENML_DEPLOYMENT_AUTH_KEY"] = auth_key

        logger.info("🚀 Starting ZenML Pipeline Deployment...")
        logger.info(f"   Deployment ID: {deployment_id}")
        logger.info(f"   Snapshot ID: {snapshot.id}")
        logger.info(f"   Host: {host}")
        logger.info(f"   Port: {port}")
        logger.info(f"   Workers: {workers}")
        logger.info(f"   Log Level: {log_level}")
        logger.info(f"   Create Runs: {create_runs}")
        logger.info("")
        logger.info(f"📖 API Documentation: http://{host}:{port}/docs")
        logger.info(f"🔍 Health Check: http://{host}:{port}/health")
        logger.info("")

        try:
            # Start the FastAPI server
            uvicorn.run(
                "zenml.deployers.server.app:app",
                host=host,
                port=port,
                workers=workers,
                log_level=log_level.lower(),
                access_log=True,
            )
        except KeyboardInterrupt:
            logger.info("\n🛑 Deployment stopped by user")
        except Exception as e:
            logger.error(f"❌ Failed to start deployment: {str(e)}")
            raise
