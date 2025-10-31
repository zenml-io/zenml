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

import os
from contextlib import asynccontextmanager
from genericpath import isdir, isfile
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from anyio import to_thread
from asgiref.typing import (
    ASGIApplication,
)
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from zenml import __version__ as zenml_version
from zenml.config import (
    AppExtensionSpec,
    DeploymentDefaultEndpoints,
    EndpointMethod,
    EndpointSpec,
    MiddlewareSpec,
)
from zenml.deployers.server.adapters import (
    EndpointAdapter,
    MiddlewareAdapter,
)
from zenml.deployers.server.app import (
    BaseDeploymentAppRunner,
    BaseDeploymentAppRunnerFlavor,
)
from zenml.deployers.server.fastapi import FastAPIDeploymentAppRunnerFlavor
from zenml.deployers.server.fastapi.adapters import (
    FastAPIEndpointAdapter,
    FastAPIMiddlewareAdapter,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class FastAPIDeploymentAppRunner(BaseDeploymentAppRunner):
    """FastAPI deployment app runner."""

    @property
    def flavor(cls) -> "BaseDeploymentAppRunnerFlavor":
        """Return the flavor associated with this deployment application runner.

        Returns:
            The flavor associated with this deployment application runner.
        """
        return FastAPIDeploymentAppRunnerFlavor()

    def _create_endpoint_adapter(self) -> EndpointAdapter:
        """Create FastAPI endpoint adapter.

        Returns:
            FastAPI endpoint adapter instance.
        """
        return FastAPIEndpointAdapter()

    def _create_middleware_adapter(self) -> MiddlewareAdapter:
        """Create FastAPI middleware adapter.

        Returns:
            FastAPI middleware adapter instance.
        """
        return FastAPIMiddlewareAdapter()

    def _build_cors_middleware(self) -> MiddlewareSpec:
        """Get the CORS middleware.

        Returns:
            The CORS middleware.
        """
        return MiddlewareSpec(
            middleware=CORSMiddleware,
            extra_kwargs=dict(
                allow_origins=self.settings.cors.allow_origins,
                allow_credentials=self.settings.cors.allow_credentials,
                allow_methods=self.settings.cors.allow_methods,
                allow_headers=self.settings.cors.allow_headers,
            ),
            native=True,
        )

    def _get_dashboard_endpoints(self) -> List[EndpointSpec]:
        """Get the dashboard endpoints specs.

        This is called if the dashboard files path is set to construct the
        endpoints specs for the dashboard.

        Returns:
            The dashboard endpoints specs.

        Raises:
            ValueError: If the index HTML file is not found in the dashboard
                files path.
        """
        dashboard_files_path = self.dashboard_files_path()
        if not dashboard_files_path or not os.path.isdir(dashboard_files_path):
            return []

        endpoints: List[EndpointSpec] = []

        async def catch_invalid_api(invalid_api_path: str) -> None:
            """Invalid API endpoint.

            All API endpoints that are not defined in the API routers will be
            caught by this endpoint and will return a 404 error.

            Args:
                invalid_api_path: Invalid API path.

            Raises:
                HTTPException: 404 error.
            """
            logger.debug(f"Invalid API path requested: {invalid_api_path}")
            raise HTTPException(status_code=404)

        if self.settings.api_url_path:
            endpoints.append(
                EndpointSpec(
                    path=f"{self.settings.api_url_path}"
                    + "/{invalid_api_path:path}",
                    method=EndpointMethod.GET,
                    handler=catch_invalid_api,
                    native=True,
                    extra_kwargs=dict(
                        include_in_schema=False,
                    ),
                )
            )

        static_files = []
        static_directories = []
        index_html_path = None
        for file in os.listdir(dashboard_files_path):
            if file.startswith("__"):
                logger.debug(f"Skipping private file: {file}")
                continue
            if file in ["index.html", "index.htm"]:
                # this is served separately
                index_html_path = os.path.join(dashboard_files_path, file)
                continue
            if isfile(os.path.join(dashboard_files_path, file)):
                static_files.append(file)
            elif isdir(os.path.join(dashboard_files_path, file)):
                static_directories.append(file)

        if index_html_path is None:
            raise ValueError(
                f"Index HTML file not found in the dashboard files path: "
                f"{dashboard_files_path}"
            )

        for static_dir in static_directories:
            static_files_endpoint = StaticFiles(
                directory=os.path.join(dashboard_files_path, static_dir),
                check_dir=False,
            )
            endpoints.append(
                EndpointSpec(
                    path=f"/{static_dir}",
                    method=EndpointMethod.GET,
                    handler=static_files_endpoint,
                    native=True,
                    auth_required=False,
                )
            )

        templates = Jinja2Templates(directory=dashboard_files_path)

        async def catch_all_endpoint(request: Request, file_path: str) -> Any:
            """Dashboard catch-all endpoint.

            Args:
                request: Request object.
                file_path: Path to a file in the dashboard root folder.

            Returns:
                The files in the dashboard root directory.
            """
            # some static files need to be served directly from the root dashboard
            # directory
            if file_path and file_path in static_files:
                logger.debug(f"Returning static file: {file_path}")
                full_path = os.path.join(dashboard_files_path, file_path)
                return FileResponse(full_path)

            # everything else is directed to the index.html file that hosts the
            # single-page application - this is to support client-side routing
            return templates.TemplateResponse(
                "index.html",
                dict(
                    request=request,
                    service_info=self.service.get_service_info().model_dump(
                        mode="json"
                    ),
                ),
            )

        endpoints.append(
            EndpointSpec(
                path="/{file_path:path}",
                method=EndpointMethod.GET,
                handler=catch_all_endpoint,
                native=True,
                auth_required=False,
                extra_kwargs=dict(
                    include_in_schema=False,
                ),
            ),
        )

        return endpoints

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

    def build(
        self,
        middlewares: List[MiddlewareSpec],
        endpoints: List[EndpointSpec],
        extensions: List[AppExtensionSpec],
    ) -> ASGIApplication:
        """Build the FastAPI app for the deployment.

        Args:
            middlewares: The middleware to register.
            endpoints: The endpoints to register.
            extensions: The extensions to install.

        Returns:
            The configured FastAPI application instance.
        """
        title = (
            self.settings.app_title
            or f"ZenML Pipeline Deployment {self.deployment.name}"
        )
        description = (
            self.settings.app_description
            or f"ZenML pipeline deployment server for the "
            f"{self.deployment.name} deployment"
        )
        docs_url_path: Optional[str] = None
        redoc_url_path: Optional[str] = None
        if self.settings.endpoint_enabled(DeploymentDefaultEndpoints.DOCS):
            docs_url_path = self.settings.docs_url_path
        if self.settings.endpoint_enabled(DeploymentDefaultEndpoints.REDOC):
            redoc_url_path = self.settings.redoc_url_path

        fastapi_kwargs: Dict[str, Any] = dict(
            title=title,
            description=description,
            version=self.settings.app_version
            if self.settings.app_version is not None
            else zenml_version,
            root_path=self.settings.root_url_path,
            docs_url=docs_url_path,
            redoc_url=redoc_url_path,
            lifespan=self.lifespan,
        )
        fastapi_kwargs.update(self.settings.app_kwargs)

        asgi_app = FastAPI(**fastapi_kwargs)

        # Save this so it's available for the middleware, endpoint adapters and
        # extensions
        self._asgi_app = cast(ASGIApplication, asgi_app)

        # Bind the app runner to the app state
        asgi_app.state.app_runner = self
        asgi_app.exception_handler(Exception)(self.error_handler)

        self.register_middlewares(*middlewares)
        self.register_endpoints(*endpoints)
        self.install_extensions(*extensions)

        return self._asgi_app

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage the deployment application lifespan.

        Args:
            app: The FastAPI application instance being deployed.

        Yields:
            None: Control is handed back to FastAPI once initialization completes.
        """
        # Set the maximum number of worker threads
        to_thread.current_default_thread_limiter().total_tokens = (
            self.settings.thread_pool_size
        )

        self.startup()

        yield

        self.shutdown()
