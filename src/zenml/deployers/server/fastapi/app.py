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
"""FastAPI application for running ZenML pipeline deployments."""

from abc import ABC, abstractmethod
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Union
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from zenml import __version__ as zenml_version
from zenml.client import Client
from zenml.deployers.server.app import BaseDeploymentAppRunner
from zenml.deployers.server.models import (
    BaseDeploymentInvocationRequest,
    BaseDeploymentInvocationResponse,
    ExecutionMetrics,
    ServiceInfo,
)
from zenml.deployers.server.service import (
    BasePipelineDeploymentService,
    DefaultPipelineDeploymentService,
)
from zenml.logger import get_logger
from zenml.models.v2.core.deployment import DeploymentResponse
from zenml.utils import source_utils

logger = get_logger(__name__)


class FastAPIDeploymentAppRunner(BaseDeploymentAppRunner):
    """Default deployment app runner."""

    def _build_invoke_endpoint(
        self,
    ) -> Callable[
        [BaseDeploymentInvocationRequest], BaseDeploymentInvocationResponse
    ]:
        """Create the invoke endpoint."""
        PipelineInvokeRequest, PipelineInvokeResponse = (
            self.service.get_pipeline_invoke_models()
        )

        security = HTTPBearer(
            scheme_name="Bearer Token",
            description="Enter your API key as a Bearer token",
            auto_error=False,
        )

        def verify_token(
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(
                security
            ),
        ) -> None:
            """Verify the provided Bearer token for authentication.

            This dependency function integrates with FastAPI's security system
            to provide proper OpenAPI documentation and authentication UI.

            Args:
                credentials: HTTP Bearer credentials from the request

            Raises:
                HTTPException: If authentication is required but token is invalid
            """
            auth_key = self.deployment.auth_key
            auth_enabled = auth_key and auth_key != ""

            # If authentication is not enabled, allow all requests
            if not auth_enabled:
                return

            # If authentication is enabled, validate the token
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if credentials.credentials != auth_key:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Token is valid, authentication successful
            return

        def _invoke_endpoint(
            request: PipelineInvokeRequest,  # type: ignore[valid-type]
            _: None = Depends(verify_token),
        ) -> PipelineInvokeResponse:  # type: ignore[valid-type]
            return self.invoke_endpoint(request)

        return _invoke_endpoint

    def invoke_endpoint(
        self, request: BaseDeploymentInvocationRequest
    ) -> BaseDeploymentInvocationResponse:
        """Invoke the pipeline.

        Args:
            request: The request.

        Returns:
            The invocation response.
        """
        return self.service.execute_pipeline(request)

    def health_check_endpoint(self, request: Request) -> str:
        """Health check endpoint.

        Args:
            request: The request.

        Returns:
            "OK" if the service is healthy, otherwise raises an HTTPException.

        Raises:
            HTTPException: If the service is not healthy.
        """
        if not self.service.is_healthy():
            raise HTTPException(503, "Service is unhealthy")
        return "OK"

    def info_endpoint(self, request: Request) -> ServiceInfo:
        """Info endpoint.

        Args:
            request: The request.

        Returns:
            Service info.
        """
        return self.service.get_service_info()

    def execution_metrics_endpoint(self, request: Request) -> ExecutionMetrics:
        """Execution metrics endpoint.

        Args:
            request: The request.

        Returns:
            Execution metrics.
        """
        return self.service.get_execution_metrics()

    def root_endpoint(self, request: Request) -> HTMLResponse:
        """Root endpoint.

        Args:
            request: The request.

        Returns:
            The root content.
        """
        info = self.service.get_service_info()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.settings.app_title or f"ZenML Pipeline Deployment `{self.deployment.name}`"}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ color: #2563eb; }}
                .section {{ margin: 20px 0; }}
                .status {{ padding: 5px 10px; border-radius: 4px; background: #10b981; color: white; }}
            </style>
        </head>
        <body>
            <h1 class="header">🚀 ZenML Pipeline Deployment</h1>
            <div class="section">
                <h2>Service Status</h2>
                <p>Status: <span class="status">Running</span></p>
                <p>Pipeline: <strong>{info.pipeline.name}</strong></p>
            </div>
            <div class="section">
                <h2>Documentation</h2>
                <p><a href="{self.settings.docs_url_path}">📖 Interactive API Documentation</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html_content)

    def error_handler(self, request: Request, exc: ValueError) -> JSONResponse:
        """FastAPI error handler.

        Args:
            request: The request.
            exc: The exception.

        Returns:
            The error response.
        """
        logger.error("Error in request: %s", exc)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    def build(self) -> FastAPI:
        """Build the FastAPI app for the deployment."""
        # Build app with metadata
        title = (
            self.settings.app_title
            or f"ZenML Pipeline Deployment {self.deployment.name}"
        )
        description = (
            self.settings.app_description
            or f"ZenML pipeline deployment server for the "
            f"{self.deployment.name} deployment"
        )
        fastapi_kwargs: Dict[str, Any] = dict(
            title=title,
            description=description,
            version=self.settings.app_version
            if self.settings.app_version is not None
            else zenml_version,
            root_path=self.settings.root_url_path,
            docs_url=self.settings.docs_url_path,
            redoc_url=self.settings.redoc_url_path,
            lifespan=self.lifespan,
        )
        fastapi_kwargs.update(self.settings.fastapi_kwargs)

        fastapi_app = FastAPI(**fastapi_kwargs)

        # Bind the deployment service to the app state
        fastapi_app.state.service = self.service

        fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_allow_origins,
            allow_credentials=self.settings.cors_allow_credentials,
            allow_methods=self.settings.cors_allow_methods,
            allow_headers=self.settings.cors_allow_headers,
        )

        fastapi_app.get("/")(self.root_endpoint)
        fastapi_app.post(self.settings.invoke_url_path)(
            self._build_invoke_endpoint()
        )
        fastapi_app.get(self.settings.health_url_path)(
            self.health_check_endpoint
        )
        fastapi_app.get(self.settings.info_url_path)(self.info_endpoint)
        fastapi_app.get(self.settings.metrics_url_path)(
            self.execution_metrics_endpoint
        )

        # error handlers
        fastapi_app.exception_handler(Exception)(self.error_handler)

        return fastapi_app

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage the deployment application lifespan.

        Args:
            app: The FastAPI application instance being deployed.

        Yields:
            None: Control is handed back to FastAPI once initialization completes.

        Raises:
            ValueError: If no deployment identifier is configured.
            Exception: If initialization or cleanup fails.
        """
        # Check for test mode
        if os.getenv("ZENML_DEPLOYMENT_TEST_MODE", "false").lower() == "true":
            logger.info("🧪 Running in test mode - skipping initialization")
            yield
            return

        logger.info("🚀 Initializing the pipeline deployment service...")

        try:
            self.service.initialize()
            logger.info(
                "✅ Pipeline deployment service initialized successfully"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize the pipeline deployment service: {e}"
            )
            raise

        # TODO: run custom startup app hooks

        yield

        # TODO: run custom shutdown app hooks

        logger.info("🛑 Cleaning up the pipeline deployment service...")
        try:
            self.service.cleanup()
            logger.info(
                "✅ The pipeline deployment service was cleaned up successfully"
            )
        except Exception as e:
            logger.error(
                f"❌ Error during the pipeline deployment service cleanup: {e}"
            )

