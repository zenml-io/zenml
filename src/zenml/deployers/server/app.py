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
"""Base deployment app runner."""

from abc import ABC, abstractmethod
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, Union
from uuid import UUID


from zenml.client import Client
from zenml.deployers.server.service import (
    BasePipelineDeploymentService,
    DefaultPipelineDeploymentService,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models.v2.core.deployment import DeploymentResponse
from zenml.utils import source_utils

logger = get_logger(__name__)

if TYPE_CHECKING:
    from uvicorn._types import ASGIApplication


class BaseDeploymentAppRunner(ABC):
    """Base class for deployment app runners.

    This class is responsible for building and running the ASGI compatible web
    application (e.g. FastAPI, Django, Flask, Falcon, Quart, BlackSheep, etc.) and the
    associated deployment service for the pipeline deployment. It also acts as
    a adaptation layer between the REST API interface and deployment service to
    preserve the following separation of concerns between the two components:

    * the ASGI application is responsible for handling the HTTP requests and
    responses to the user
    * the deployment service is responsible for handling the business logic

    The deployment service code should be free of any ASGI application specific
    code and concerns and vice-versa. This allows them to be independently
    extendable and easily swappable.

    Implementations of this class must use the deployment and its settings to
    configure and run the web application (e.g. FastAPI, Flask, Falcon, Quart,
    BlackSheep, etc.) that wraps the deployment service according to the user's
    specifications, particularly concerning the following:

    * exposed endpoints (URL paths, methods, input/output models)
    * middleware (CORS, authentication, logging, etc.)
    * error handling
    * lifecycle management (startup, shutdown)
    * custom hooks (startup, shutdown)
    * app configuration (workers, host, port, thread pool size, etc.)

    The following methods must be provided by implementations of this class:

    * build: Build and return an ASGI compatible web application (i.e. an
    ASGIApplication object that can be run with uvicorn). Most Python ASGI
    frameworks provide an ASGIApplication object.
    """

    def __init__(self, deployment: Union[str, UUID, "DeploymentResponse"]):
        """Initialize the deployment app.

        Args:
            deployment: The deployment to run.

        Raises:
            RuntimeError: If the deployment or its snapshot cannot be loaded.
        """
        self.deployment = self.load_deployment(deployment)
        assert self.deployment.snapshot is not None
        self.snapshot = self.deployment.snapshot

        self.settings = (
            self.snapshot.pipeline_configuration.deployment_settings
        )

        self.service = self.load_deployment_service(deployment)

    @classmethod
    def load_deployment(
        cls, deployment: Union[str, UUID, "DeploymentResponse"]
    ) -> DeploymentResponse:
        """Load the deployment.

        Args:
            deployment: The deployment to load.

        Returns:
            The deployment.

        Raises:
            RuntimeError: If the deployment or its snapshot cannot be loaded.
        """
        if isinstance(deployment, str):
            deployment = UUID(deployment)

        if isinstance(deployment, UUID):
            try:
                deployment = Client().zen_store.get_deployment(
                    deployment_id=deployment
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load deployment {deployment}: {e}"
                ) from e
        else:
            assert isinstance(deployment, DeploymentResponse)

        if deployment.snapshot is None:
            raise RuntimeError(f"Deployment {deployment.id} has no snapshot")

        return deployment

    @classmethod
    def load_app_runner(
        cls, deployment: Union[str, UUID, "DeploymentResponse"]
    ) -> "BaseDeploymentAppRunner":
        """Load the app runner for the deployment.

        Args:
            deployment: The deployment to load the app runner for.

        Returns:
            The app runner for the deployment.
        """
        from zenml.deployers.server.fastapi.app import (
            FastAPIDeploymentAppRunner,
        )

        deployment = cls.load_deployment(deployment)
        assert deployment.snapshot is not None

        settings = (
            deployment.snapshot.pipeline_configuration.deployment_settings
        )

        if settings.deployment_app_runner_source is None:
            app_runner_cls = FastAPIDeploymentAppRunner
        else:
            try:
                app_runner_cls = source_utils.load(
                    settings.deployment_app_runner_source
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load deployment app runner from source "
                    f"{settings.deployment_app_runner_source}: {e}\n"
                    "Please check that the source is valid and that the "
                    "deployment app runner class is importable from the source "
                    "root directory. Hint: run `zenml init` in your local "
                    "source directory to initialize the source root path."
                ) from e

        if not issubclass(app_runner_cls, BaseDeploymentAppRunner):
            raise RuntimeError(
                f"Deployment app runner class '{app_runner_cls}' is not a "
                "subclass of 'BaseDeploymentAppRunner'"
            )

        logger.info(
            f"Instantiating deployment app runner class '{app_runner_cls}' for "
            f"deployment {deployment.id}"
        )

        try:
            return app_runner_cls(deployment)
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate deployment app runner class "
                f"'{app_runner_cls}' for deployment {deployment.id}: {e}"
            ) from e

    @classmethod
    def load_deployment_service(
        cls, deployment: Union[str, UUID, "DeploymentResponse"]
    ) -> BasePipelineDeploymentService:
        """Load the service for the deployment.

        Args:
            deployment: The deployment to load the service for.

        Returns:
            The deployment service for the deployment.

        Raises:
            RuntimeError: If the deployment service cannot be loaded.
        """
        deployment = cls.load_deployment(deployment)
        assert deployment.snapshot is not None

        settings = (
            deployment.snapshot.pipeline_configuration.deployment_settings
        )
        if settings.deployment_service_source is None:
            service_cls = DefaultPipelineDeploymentService
        else:
            try:
                service_cls = source_utils.load(
                    settings.deployment_service_source
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load deployment service from source "
                    f"{settings.deployment_service_source}: {e}\n"
                    "Please check that the source is valid and that the "
                    "deployment service class is importable from the source "
                    "root directory. Hint: run `zenml init` in your local "
                    "source directory to initialize the source root path."
                ) from e

        if not issubclass(service_cls, BasePipelineDeploymentService):
            raise RuntimeError(
                f"Deployment service class '{service_cls}' is not a subclass "
                "of 'BasePipelineDeploymentService'"
            )

        logger.info(
            f"Instantiating deployment service class '{service_cls}' for "
            f"deployment {deployment.id}"
        )

        try:
            return service_cls(deployment)
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate deployment service class "
                f"'{service_cls}' for deployment {deployment.id}: {e}"
            ) from e

    def run(self) -> None:
        """Run the deployment app."""
        import uvicorn

        settings = self.settings

        self.asgi_app = self.build()

        logger.info(f"""
🚀 Starting ZenML pipeline deployment application:
   Deployment ID: {self.deployment.id}
   Deployment Name: {self.deployment.name}
   Snapshot ID: {self.snapshot.id}
   Snapshot Name: {self.snapshot.name or "N/A"}
   Pipeline ID: {self.snapshot.pipeline.id}
   Pipeline Name: {self.snapshot.pipeline.name}
   Host: {settings.uvicorn_host}
   Port: {settings.uvicorn_port}
   Workers: {settings.uvicorn_workers}
   Log Level: {settings.log_level}
""")

        uvicorn_kwargs: Dict[str, Any] = dict(
            host=settings.uvicorn_host,
            port=settings.uvicorn_port,
            workers=settings.uvicorn_workers,
            log_level=settings.log_level.value,
            access_log=True,
        )
        if settings.uvicorn_kwargs:
            uvicorn_kwargs.update(settings.uvicorn_kwargs)

        try:
            # Start the ASGI application
            uvicorn.run(
                self.asgi_app,
                **uvicorn_kwargs,
            )
        except KeyboardInterrupt:
            logger.info("\n🛑 Deployment application shutdown")
        except Exception as e:
            logger.error(
                f"❌ Failed to start deployment application: {str(e)}"
            )
            raise

    @abstractmethod
    def build(self) -> Union["ASGIApplication", Callable[..., Any]]:
        """Build the ASGI compatible web application.

        Args:
            **kwargs: Additional keyword arguments for building the ASGI
                compatible web application.

        Returns:
            The ASGI compatible web application.
        """


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deployment_id",
        default=os.getenv("ZENML_DEPLOYMENT_ID"),
        help="Pipeline snapshot ID",
    )
    args = parser.parse_args()

    logger.info(
        f"Starting deployment application server for deployment "
        f"{args.deployment_id}"
    )

    # Activate integrations to ensure all components are available
    integration_registry.activate_integrations()

    app_runner = BaseDeploymentAppRunner.load_app_runner(args.deployment_id)
    app_runner.run()
