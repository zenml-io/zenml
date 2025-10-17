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
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, cast

from anyio import to_thread
from fastapi import (
    FastAPI,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from zenml import __version__ as zenml_version
from zenml.config.deployment_settings import (
    AppExtensionSpec,
    EndpointMethod,
    EndpointSpec,
    MiddlewareSpec,
)
from zenml.config.source import SourceOrObject
from zenml.deployers.server.adapters import (
    EndpointAdapter,
    MiddlewareAdapter,
)
from zenml.deployers.server.app import BaseDeploymentAppRunner
from zenml.deployers.server.fastapi.adapters import (
    FastAPIEndpointAdapter,
    FastAPIMiddlewareAdapter,
)

if TYPE_CHECKING:
    from asgiref.typing import (
        ASGIApplication,
    )


from zenml.logger import get_logger

logger = get_logger(__name__)


class FastAPIDeploymentAppRunner(BaseDeploymentAppRunner):
    """FastAPI deployment app runner."""

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

    def _get_cors_middleware(self) -> MiddlewareSpec:
        """Get the CORS middleware.

        Returns:
            The CORS middleware.
        """
        return MiddlewareSpec(
            middleware=SourceOrObject(CORSMiddleware),
            init_kwargs=dict(
                allow_origins=self.settings.cors.allow_origins,
                allow_credentials=self.settings.cors.allow_credentials,
                allow_methods=self.settings.cors.allow_methods,
                allow_headers=self.settings.cors.allow_headers,
            ),
            native=True,
        )

    def root_endpoint(self) -> HTMLResponse:
        """Root endpoint.

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

    def _get_dashboard_endpoints(self) -> List[EndpointSpec]:
        """Get the dashboard endpoints specs.

        This is called if the dashboard files path is set to construct the
        endpoints specs for the dashboard.

        Returns:
            The dashboard endpoints specs.
        """
        # @app.get(
        #     API + "/{invalid_api_path:path}", status_code=404, include_in_schema=False
        # )
        # async def invalid_api(invalid_api_path: str) -> None:
        #     """Invalid API endpoint.

        #     All API endpoints that are not defined in the API routers will be
        #     redirected to this endpoint and will return a 404 error.

        #     Args:
        #         invalid_api_path: Invalid API path.

        #     Raises:
        #         HTTPException: 404 error.
        #     """
        #     logger.debug(f"Invalid API path requested: {invalid_api_path}")
        #     raise HTTPException(status_code=404)
        dashboard_files_path = self.dashboard_files_path()
        if not dashboard_files_path:
            return []

        root_static_files = self.get_root_static_files()
        assets_static_files_endpoint = StaticFiles(
            directory=os.path.join(dashboard_files_path, "assets"),
            check_dir=False,
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
            if file_path and file_path in root_static_files:
                logger.debug(f"Returning static file: {file_path}")
                full_path = os.path.join(dashboard_files_path, file_path)
                return FileResponse(full_path)

            # everything else is directed to the index.html file that hosts the
            # single-page application
            return templates.TemplateResponse(
                "index.html", {"request": request}
            )

        return [
            EndpointSpec(
                path="/assets",
                method=EndpointMethod.GET,
                handler=SourceOrObject(assets_static_files_endpoint),
                native=True,
                auth_required=False,
            ),
            EndpointSpec(
                path="/{file_path:path}",
                method=EndpointMethod.GET,
                handler=SourceOrObject(catch_all_endpoint),
                native=True,
                auth_required=False,
                extra_kwargs=dict(
                    include_in_schema=False,
                ),
            ),
        ]

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
    ) -> "ASGIApplication":
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
        fastapi_kwargs.update(self.settings.app_kwargs)

        asgi_app = FastAPI(**fastapi_kwargs)

        # Save this so it's available for the middleware, endpoint adapters and
        # extensions
        self._asgi_app = cast("ASGIApplication", asgi_app)

        # Bind the app runner to the app state
        asgi_app.state.app_runner = self

        if (
            self.settings.include_default_endpoints
            and not self.settings.dashboard_files_path
        ):
            asgi_app.get("/")(self.root_endpoint)
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
