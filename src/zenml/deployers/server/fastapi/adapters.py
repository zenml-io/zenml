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
"""FastAPI adapter implementations."""

from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from zenml.config import (
    EndpointMethod,
    EndpointSpec,
    MiddlewareSpec,
)
from zenml.deployers.server.adapters import (
    EndpointAdapter,
    MiddlewareAdapter,
)
from zenml.deployers.server.app import BaseDeploymentAppRunner


class FastAPIEndpointAdapter(EndpointAdapter):
    """FastAPI implementation of endpoint adapter."""

    def _build_auth_dependency(self, api_key: str) -> Callable[..., Any]:
        """Build a FastAPI auth dependency.

        Args:
            api_key: The API key to use for authentication.

        Returns:
            FastAPI auth enforcement callable.
        """
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

            Args:
                credentials: HTTP Bearer credentials from the request.

            Raises:
                HTTPException: If token is invalid.
            """
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if credentials.credentials != api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return verify_token

    def register_endpoint(
        self,
        app_runner: BaseDeploymentAppRunner,
        spec: EndpointSpec,
    ) -> None:
        """Register endpoint with FastAPI.

        Args:
            app_runner: Deployment app runner instance.
            spec: Framework-agnostic endpoint specification.

        Raises:
            RuntimeError: If the adapter is not used with a FastAPI application.
        """
        app = app_runner.asgi_app

        if not isinstance(app, FastAPI):
            raise RuntimeError(
                f"The {self.__class__.__name__} adapter must be used with a "
                "FastAPI application"
            )

        # Ensure handler is loaded
        handler = self.resolve_endpoint_handler(app_runner, spec)

        # Apply auth dependency if required
        dependencies = []
        if spec.auth_required and app_runner.deployment.auth_key:
            auth_dependency = self._build_auth_dependency(
                app_runner.deployment.auth_key
            )
            dependencies.append(Depends(auth_dependency))

        if spec.native:
            if isinstance(handler, APIRouter):
                app.include_router(
                    handler, prefix=spec.path, **spec.extra_kwargs
                )
                return
            # Handle StaticFiles mounting
            if isinstance(handler, StaticFiles):
                app.mount(spec.path, handler, name=spec.path.strip("/"))
                return

        # Register with appropriate HTTP method
        route_kwargs: Dict[str, Any] = {"dependencies": dependencies}
        route_kwargs.update(spec.extra_kwargs)

        if spec.method == EndpointMethod.GET:
            app.get(spec.path, **route_kwargs)(handler)
        elif spec.method == EndpointMethod.POST:
            app.post(spec.path, **route_kwargs)(handler)
        elif spec.method == EndpointMethod.PUT:
            app.put(spec.path, **route_kwargs)(handler)
        elif spec.method == EndpointMethod.PATCH:
            app.patch(spec.path, **route_kwargs)(handler)
        elif spec.method == EndpointMethod.DELETE:
            app.delete(spec.path, **route_kwargs)(handler)


class FastAPIMiddlewareAdapter(MiddlewareAdapter):
    """FastAPI implementation of middleware adapter.

    We support two types of native middleware:

    * A middleware class like that receives the ASGIApp object in the
    constructor and implements the __call__ method to dispatch the middleware,
    e.g.:

    ```python
    from starlette.types import ASGIApp, Receive, Scope, Send

    class MyMiddleware:
        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            ...
            await self.app(scope, receive, send)
    ```

    * A middleware function that takes request and next callable and returns a response,
    e.g.:

    ```python
    from fastapi import Request, Response

    async def my_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        ...
        return await call_next(request)
    ```

    """

    def register_middleware(
        self,
        app_runner: BaseDeploymentAppRunner,
        spec: MiddlewareSpec,
    ) -> None:
        """Register middleware with FastAPI.

        Args:
            app_runner: Deployment app runner instance.
            spec: Framework-agnostic middleware specification.

        Raises:
            RuntimeError: If the adapter is not used with a FastAPI application.
        """
        app = app_runner.asgi_app

        if not isinstance(app, FastAPI):
            raise RuntimeError(
                f"The {self.__class__.__name__} adapter must be used with a "
                "FastAPI application"
            )

        middleware = self.resolve_middleware_handler(app_runner, spec)

        if spec.native:
            if isinstance(middleware, type):
                app.add_middleware(
                    middleware,  # type: ignore[arg-type]
                    **spec.extra_kwargs,
                )
                return

            app.add_middleware(
                BaseHTTPMiddleware,
                dispatch=middleware,
                **spec.extra_kwargs,
            )

        if isinstance(middleware, type):
            app.add_middleware(
                middleware,  # type: ignore[arg-type]
                **spec.extra_kwargs,
            )
            return

        # Convert the unified middleware to a FastAPI middleware class
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=middleware,
            **spec.extra_kwargs,
        )
