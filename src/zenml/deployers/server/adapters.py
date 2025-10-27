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
"""Framework adapter interfaces."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, cast

from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    Scope,
)

from zenml.config.source import SourceOrObject

if TYPE_CHECKING:
    from zenml.config import (
        EndpointSpec,
        MiddlewareSpec,
    )
    from zenml.deployers.server.app import BaseDeploymentAppRunner


class EndpointAdapter(ABC):
    """Converts framework-agnostic endpoint specs to framework endpoints."""

    def resolve_endpoint_handler(
        self,
        app_runner: "BaseDeploymentAppRunner",
        endpoint_spec: "EndpointSpec",
    ) -> Any:
        """Resolve an endpoint handler from its specification.

        This method handles three types of handlers as defined in EndpointSpec:
        1. Direct endpoint function - returned as-is
        2. Endpoint builder class - instantiated with app_runner, app, and
        init_kwargs
        3. Endpoint builder function - called with app_runner, app, and
        init_kwargs to obtain the actual endpoint

        Args:
            app_runner: Deployment app runner instance.
            endpoint_spec: The endpoint specification to resolve the handler
                from.

        Returns:
            The actual endpoint callable ready to be registered.

        Raises:
            ValueError: If handler is not callable or builder returns
                non-callable.
            RuntimeError: If handler resolution fails.
        """
        import inspect

        assert isinstance(endpoint_spec.handler, SourceOrObject)
        handler = endpoint_spec.handler.load()

        if endpoint_spec.native:
            return handler

        # Type 2: Endpoint builder class
        if isinstance(handler, type):
            if not hasattr(handler, "__call__"):
                raise ValueError(
                    f"Handler class {handler.__name__} must implement "
                    "__call__ method"
                )
            try:
                inner_handler = handler(
                    app_runner=app_runner,
                    **endpoint_spec.init_kwargs,
                )
            except TypeError as e:
                raise RuntimeError(
                    f"Failed to instantiate handler class "
                    f"{handler.__name__}: {e}"
                ) from e

            if not callable(inner_handler):
                raise ValueError(
                    f"The __call__ method of the handler class "
                    f"{handler.__name__} must return a callable"
                )

            return inner_handler

        if not callable(handler):
            raise ValueError(f"Handler {handler} is not callable")

        # Determine if it's Type 3 (builder function) or Type 1 (direct)
        try:
            sig = inspect.signature(handler)
            params = set(sig.parameters.keys())

            # Type 3: Builder function (has app_runner parameter)
            if "app_runner" in params:
                try:
                    inner_handler = handler(
                        app_runner=app_runner,
                        **endpoint_spec.init_kwargs,
                    )
                    if not callable(inner_handler):
                        raise ValueError(
                            f"Builder function {handler.__name__} must "
                            f"return a callable, got {type(inner_handler)}"
                        )
                    return inner_handler
                except TypeError as e:
                    raise RuntimeError(
                        f"Failed to call builder function "
                        f"{handler.__name__}: {e}"
                    ) from e

            # Type 1: Direct endpoint function
            return handler

        except ValueError:
            # inspect.signature failed, assume it's a direct endpoint
            return handler

    @abstractmethod
    def register_endpoint(
        self,
        app_runner: "BaseDeploymentAppRunner",
        spec: "EndpointSpec",
    ) -> None:
        """Register an endpoint on the app.

        Args:
            app_runner: Deployment app runner instance.
            spec: Framework-agnostic endpoint specification.

        Raises:
            RuntimeError: If endpoint registration fails.
        """


class MiddlewareAdapter(ABC):
    """Converts framework-agnostic middleware specs to framework middleware."""

    def resolve_middleware_handler(
        self,
        app_runner: "BaseDeploymentAppRunner",
        middleware_spec: "MiddlewareSpec",
    ) -> Any:
        """Resolve a middleware handler from its specification.

        This method handles three types of middleware as defined in MiddlewareSpec:
        1. Middleware callable class
        2. Middleware callable function
        3. Native middleware object

        Args:
            app_runner: Deployment app runner instance.
            middleware_spec: The middleware specification to resolve the handler
                from.

        Returns:
            The actual middleware callable ready to be registered.

        Raises:
            ValueError: If middleware is not callable or builder returns
                non-callable.
        """
        import inspect

        assert isinstance(middleware_spec.middleware, SourceOrObject)
        middleware = middleware_spec.middleware.load()

        if middleware_spec.native:
            return middleware

        # Type 1: Middleware class
        if isinstance(middleware, type):
            return middleware

        if not callable(middleware):
            raise ValueError(f"Middleware {middleware} is not callable")

        # Wrap the middleware function in a middleware class
        class _MiddlewareAdapter:
            def __init__(self, app: ASGIApplication, **kwargs: Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self,
                scope: Scope,
                receive: ASGIReceiveCallable,
                send: ASGISendCallable,
            ) -> None:
                callable_middleware = cast(Callable[..., Any], middleware)
                if inspect.iscoroutinefunction(callable_middleware):
                    await callable_middleware(
                        app=self.app,
                        scope=scope,
                        receive=receive,
                        send=send,
                        **self.kwargs,
                    )
                else:
                    callable_middleware(
                        app=self.app,
                        scope=scope,
                        receive=receive,
                        send=send,
                        **self.kwargs,
                    )

        return _MiddlewareAdapter

    @abstractmethod
    def register_middleware(
        self,
        app_runner: "BaseDeploymentAppRunner",
        spec: "MiddlewareSpec",
    ) -> None:
        """Register middleware on the app.

        Args:
            app_runner: Deployment app runner instance.
            spec: Framework-agnostic middleware specification.

        Raises:
            ValueError: If middleware scope requires missing parameters.
            RuntimeError: If middleware registration fails.
        """
