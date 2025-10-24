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
"""Deployment settings."""

from enum import Enum, IntFlag, auto
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from zenml.config.base_settings import BaseSettings, ConfigurationLevel
from zenml.config.source import SourceOrObject, SourceOrObjectField
from zenml.enums import LoggingLevels
from zenml.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DEPLOYMENT_APP_THREAD_POOL_SIZE = 40

DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_HSTS = (
    "max-age=63072000; includeSubdomains"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XFO = "SAMEORIGIN"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CONTENT = "nosniff"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "img-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "font-src 'self';"
    "frame-src 'self'"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_REFERRER = "no-referrer-when-downgrade"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CACHE = (
    "no-store, no-cache, must-revalidate"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_PERMISSIONS = (
    "accelerometer=(), autoplay=(), camera=(), encrypted-media=(), "
    "geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), "
    "payment=(), sync-xhr=(), usb=()"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_REPORT_TO = "default"
DEFAULT_DEPLOYMENT_APP_MAX_REQUEST_BODY_SIZE_IN_BYTES = 256 * 1024 * 1024


class EndpointMethod(str, Enum):
    """HTTP methods for endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class EndpointSpec(BaseModel):
    """Endpoint specification.

    Use this class to configure a custom endpoint that must be registered on the
    deployment application in a framework-agnostic way.

    The handler field can be set to one of the following:

    1. The function or method that represents the actual endpoint
    implementation. This will be registered as is. The function itself may be
    framework-specific - i.e. it may use framework-specific arguments, return
    values or implementation details, e.g.:

    ```python
    async def my_handler(request: Request, my_param: InputModel) -> OutputModel:
        ...
    ```

    2. An endpoint builder class - this is a callable class (i.e. a class that
    implements the __call__ method, which is the actual endpoint implementation)
    that is used to build the endpoint. When this is used, the class constructor
    must accept an argument `app_runner` of type `BaseDeploymentAppRunner`
    which will be passed by the adapter at application build time.

    The adapter will also pass the `init_kwargs` to the class constructor if
    configured. The following is an example of an endpoint builder class

    ```python
    from zenml.deployers.server import BaseDeploymentAppRunner

    class MyHandler:
        def __init__(
            self,
            app_runner: "BaseDeploymentAppRunner",
            **kwargs: Any,
        ) -> Any:
            self.app_runner = app_runner
            self.kwargs = kwargs
            ...

        async def __call__(self, request: Request, my_param: InputModel) -> OutputModel:
            ...
    ```

    3. An endpoint builder function - this is a function that is used to build
    and return the endpoint. When this is used, the adapter will call the
    the provided function first and is expected to return the actual endpoint
    function. The builder function must accept an argument `app_runner` of type
    `BaseDeploymentAppRunner` which will be passed by the adapter at
    application build time.

    The adapter will also pass the `init_kwargs` to the builder function if
    configured. The following is an example of an endpoint builder function:

    ```python
    from zenml.deployers.server import BaseDeploymentAppRunner

    def my_builder(
        app_runner: "BaseDeploymentAppRunner",
        **kwargs: Any,
    ) -> Callable:
        ...

        async def endpoint(request: Request, my_param: InputModel) -> OutputModel:
            ...

        return endpoint
    ```

    4. Alternatively, the middleware can be set to any framework-specific
    source-loadable object that can be used directly, by setting `native` to
    `True`. In this case, the framework-specific endpoint adapter will decide
    what to do with the object and how to use the init_kwargs.

    Attributes:
        path: URL path (e.g., "/custom/metrics").
        method: HTTP method.
        handler: Handler callable or source. If this is an endpoint builder
            instead of the actual endpoint implementation, the adapter will call
            the provided callable first and is expected to return the actual
            endpoint callable.
        native: Whether the endpoint is a framework-specific source-loadable
            object that can be used directly.
        auth_required: Whether authentication is required. This is an
            indication for the adapter to apply any configured auth dependencies
            or middlewares to the endpoint.
        init_kwargs: Arguments to be passed to the endpoint builder function or
            class constructor, if provided.
        extra_kwargs: Arbitrary framework-specific arguments to be used when
            registering the endpoint.
    """

    path: str
    method: EndpointMethod
    handler: SourceOrObjectField
    native: bool = False
    auth_required: bool = True
    init_kwargs: Dict[str, Any] = Field(default_factory=dict)
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict)

    def load_sources(self) -> None:
        """Load all source strings into callables."""
        assert isinstance(self.handler, SourceOrObject)
        if not self.handler.is_loaded:
            self.handler.load()

    model_config = ConfigDict(
        # public attributes are mutable
        frozen=False,
        # prevent extra attributes during model initialization
        extra="ignore",
    )


class MiddlewareSpec(BaseModel):
    """Middleware specification.

    Use this class to configure custom middleware that must be registered on
    the deployment application in a framework-agnostic way.

    The middleware field can be set to one of the following:

    1. A middleware class - this class follows the standard ASGI middleware
    interface, i.e. it implements the __call__ method and takes the scope,
    receive and send arguments.

    The adapter will also pass the `init_kwargs` to the class constructor if
    configured. The following is an example of a middleware class:

    ```python
    from asgiref.typing import (
        ASGIApplication,
        ASGIReceiveCallable,
        ASGISendCallable,
        Scope,
    )

    class MyMiddleware:
        def __init__(
            self,
            app: ASGIApplication,
            **kwargs: Any,
        ) -> None:
            self.app = app
            self.kwargs = kwargs

        async def __call__(
            self,
            scope: Scope,
            receive: ASGIReceiveCallable,
            send: ASGISendCallable,
        ) -> None:
            # Middleware logic
            ...
            await self.app(scope, receive, send)
    ```

    2. A middleware function - this function follows the standard ASGI middleware
    interface, i.e. it takes the ASGIApp object, scope, receive and send arguments.
    The adapter will pass the `init_kwargs` to the middleware function if
    configured. The following is an example of a middleware function:

    ```python
    from asgiref.typing import (
        ASGIApplication,
        ASGIReceiveCallable,
        ASGISendCallable,
        Scope,
    )

    async def my_middleware(
        app: ASGIApplication,
        scope: Scope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
        **kwargs: Any,
    ) -> None:
        ...
        await app(scope, receive, send)
    ```

    3. Alternatively, the middleware can be set to any framework-specific
    source-loadable object that can be used directly, by setting `native` to
    `True`. In this case, the framework-specific middleware adapter will decide
    what to do with the object and how to use the init_kwargs.

    Attributes:
        middleware: Middleware callable or source. If this is a middleware
            builder instead of the actual middleware implementation, the
            adapter will call the provided callable first and is expected to
            return the actual middleware callable.
        native: Whether the middleware is a framework-specific source-loadable
            object that can be used directly.
        order: Registration order (lower = earlier in chain).
        init_kwargs: Arguments to be passed to the middleware builder function
            or class constructor, if provided.
        extra_kwargs: Arbitrary framework-specific arguments to be passed to
            the middleware constructor by the adapter.
    """

    middleware: SourceOrObjectField
    native: bool = False
    order: int = 0
    init_kwargs: Dict[str, Any] = Field(default_factory=dict)
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict)

    def load_sources(self) -> None:
        """Load source string into callable."""
        assert isinstance(self.middleware, SourceOrObject)
        if not self.middleware.is_loaded:
            self.middleware.load()

    model_config = ConfigDict(
        # public attributes are mutable
        frozen=False,
        # prevent extra attributes during model initialization
        extra="ignore",
    )


class AppExtensionSpec(BaseModel):
    """Configuration for a pluggable app extension.

    Extensions can be:
    1. Simple callable - this is a function that is used to apply the extension
    to the app. The function must accept an argument `app_runner` of type
    `BaseDeploymentAppRunner` which will be passed by the adapter at
    application build time. If configured, the function will also be passed the
    `extension_kwargs` as keyword arguments. This is an example:

    ```python
    from zenml.deployers.server import BaseDeploymentAppRunner

    def extension(app_runner: BaseDeploymentAppRunner, **kwargs)

        @app_runner.asgi_app.get("/my-extension")
        def my_extension(request: Request) -> Response:
            ...

    ```

    2. BaseAppExtension subclass. If any kwargs are provided, they will be
    passed to the class constructor. The class must also implement the `install`
    method, which will be called by the adapter at application build time. This
    is an example:

    ```python
    from zenml.deployers.server import BaseAppExtension
    from zenml.deployers.server import BaseDeploymentAppRunner

    class MyExtension(BaseAppExtension):

        def __init__(self, **kwargs):
            ...
            self.router = APIRouter()
            ...

        def install(self, app_runner: BaseDeploymentAppRunner) -> None:

            app_runner.asgi_app.include_router(self.router)
    ```

    Attributes:
        extension: Extension callable/class or source.
        extension_kwargs: Configuration passed during initialization.
    """

    extension: SourceOrObjectField
    extension_kwargs: Dict[str, Any] = Field(default_factory=dict)

    def load_sources(self) -> None:
        """Load source string into callable."""
        assert isinstance(self.extension, SourceOrObject)
        if not self.extension.is_loaded:
            self.extension.load()

    def resolve_extension_handler(
        self,
    ) -> Callable[..., Any]:
        """Resolve the extension handler from the spec.

        Returns:
            The extension handler.

        Raises:
            ValueError: If the extension object is not callable.
        """
        assert isinstance(self.extension, SourceOrObject)

        extension = self.extension.load()
        if not callable(extension):
            raise ValueError(
                f"The extension object {extension} must be callable"
            )
        return extension

    model_config = ConfigDict(
        # public attributes are mutable
        frozen=False,
        # prevent extra attributes during model initialization
        extra="ignore",
    )


class CORSConfig(BaseModel):
    """Configuration for CORS."""

    allow_origins: List[str] = ["*"]
    allow_methods: List[str] = ["GET", "POST", "OPTIONS"]
    allow_headers: List[str] = ["*"]
    allow_credentials: bool = False


class SecureHeadersConfig(BaseModel):
    """Configuration for secure headers.

    Attributes:
        server: Custom value to be set in the `Server` HTTP header to identify
            the server. If not specified, or if set to one of the reserved values
            `enabled`, `yes`, `true`, `on`, the `Server` header will be set to the
            default value (ZenML server ID). If set to one of the reserved values
            `disabled`, `no`, `none`, `false`, `off` or to an empty string, the
            `Server` header will not be included in responses.
        hsts: The server header value to be set in the HTTP header
            `Strict-Transport-Security`. If not specified, or if set to one of
            the reserved values `enabled`, `yes`, `true`, `on`, the
            `Strict-Transport-Security` header will be set to the default value
            (`max-age=63072000; includeSubdomains`). If set to one of the reserved
            values `disabled`, `no`, `none`, `false`, `off` or to an empty string,
            the `Strict-Transport-Security` header will not be included in responses.
        xfo: The server header value to be set in the HTTP header
            `X-Frame-Options`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `X-Frame-Options`
            header will be set to the default value (`SAMEORIGIN`). If set to
            one of the reserved values `disabled`, `no`, `none`, `false`, `off`
            or to an empty string, the `X-Frame-Options` header will not be
            included in responses.
        content: The server header value to be set in the HTTP header
            `X-Content-Type-Options`. If not specified, or if set to one
            of the reserved values `enabled`, `yes`, `true`, `on`, the
            `X-Content-Type-Options` header will be set to the default value
            (`nosniff`). If set to one of the reserved values `disabled`, `no`,
            `none`, `false`, `off` or to an empty string, the
            `X-Content-Type-Options` header will not be included in responses.
        csp: The server header value to be set in the HTTP header
            `Content-Security-Policy`. If not specified, or if set to one
            of the reserved values `enabled`, `yes`, `true`, `on`, the
            `Content-Security-Policy` header will be set to the default value
            DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CSP. If set to one of the
            reserved values `disabled`, `no`, `none`, `false`, `off` or to an
            empty string, the `Content-Security-Policy` header will not be
            included in responses.
        referrer: The server header value to be set in the HTTP header
            `Referrer-Policy`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `Referrer-Policy`
            header will be set to the default value
            (`no-referrer-when-downgrade`). If set to one of the reserved values
            `disabled`, `no`, `none`, `false`, `off` or to an empty string, the
            `Referrer-Policy` header will not be included in responses.
        cache: The server header value to be set in the HTTP header
            `Cache-Control`. If not specified, or if set to one of the
            reserved values `enabled`, `yes`, `true`, `on`, the `Cache-Control`
            header will be set to the default value
            (`no-store, no-cache, must-revalidate`). If set to one of the
            reserved values `disabled`, `no`, `none`, `false`, `off` or to an
            empty string, the `Cache-Control` header will not be included in
            responses.
        permissions: The server header value to be set in the HTTP header
            `Permissions-Policy`. If not specified, or if set to one
            of the reserved values `enabled`, `yes`, `true`, `on`, the
            `Permissions-Policy` header will be set to the default value
            DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_PERMISSIONS. If set to
            one of the reserved values `disabled`, `no`, `none`, `false`, `off`
            or to an empty string, the `Permissions-Policy` header will not be
            included in responses.
    """

    server: Union[bool, str] = Field(
        default=True,
        union_mode="left_to_right",
    )
    hsts: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_HSTS,
        union_mode="left_to_right",
    )
    xfo: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XFO,
        union_mode="left_to_right",
    )
    content: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CONTENT,
        union_mode="left_to_right",
    )
    csp: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CSP,
        union_mode="left_to_right",
    )
    referrer: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_REFERRER,
        union_mode="left_to_right",
    )
    cache: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CACHE,
        union_mode="left_to_right",
    )
    permissions: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_PERMISSIONS,
        union_mode="left_to_right",
    )


DEFAULT_DEPLOYMENT_APP_ROOT_URL_PATH = ""
DEFAULT_DEPLOYMENT_APP_API_URL_PATH = ""
DEFAULT_DEPLOYMENT_APP_DOCS_URL_PATH = "/docs"
DEFAULT_DEPLOYMENT_APP_REDOC_URL_PATH = "/redoc"
DEFAULT_DEPLOYMENT_APP_INVOKE_URL_PATH = "/invoke"
DEFAULT_DEPLOYMENT_APP_HEALTH_URL_PATH = "/health"
DEFAULT_DEPLOYMENT_APP_INFO_URL_PATH = "/info"
DEFAULT_DEPLOYMENT_APP_METRICS_URL_PATH = "/metrics"


class DeploymentDefaultEndpoints(IntFlag):
    """Default endpoints for the deployment application."""

    NONE = 0
    DOCS = auto()
    REDOC = auto()
    INVOKE = auto()
    HEALTH = auto()
    INFO = auto()
    METRICS = auto()
    DASHBOARD = auto()

    DOC = DOCS | REDOC
    API = INVOKE | HEALTH | INFO | METRICS
    ALL = DOCS | REDOC | INVOKE | HEALTH | INFO | METRICS | DASHBOARD


class DeploymentDefaultMiddleware(IntFlag):
    """Default middleware for the deployment application."""

    NONE = 0
    CORS = auto()
    SECURE_HEADERS = auto()

    ALL = CORS | SECURE_HEADERS


class DeploymentSettings(BaseSettings):
    """Settings for the pipeline deployment.

    Use these settings to fully customize all aspects of the uvicorn web server
    and ASGI web application that constitute the pipeline deployment.

    Note that these settings are only available at the pipeline level.

    The following customizations can be used to configure aspects that are
    framework-agnostic (i.e. not specific to a particular ASGI framework like
    FastAPI, Django, Flask, etc.):

    * the ASGI application details: `app_title`, `app_description`,
    `app_version` and `app_kwargs`
    * the URL paths for the various built-in endpoints: `root_url_path`,
    `api_url_path`, `docs_url_path`, `redoc_url_path`, `invoke_url_path`,
    `health_url_path`, `info_url_path` and `metrics_url_path`
    * the location of dashboard static files can be provided to replace the
    default UI that is included with the deployment ASGI application:
    `dashboard_files_path`
    * which default endpoints and middleware to include:
    `include_default_endpoints` and `include_default_middleware`
    * the CORS configuration: `cors`
    * the secure headers configuration: `secure_headers`
    * the thread pool size: `thread_pool_size`
    * custom application startup and shutdown hooks: `startup_hook_source`,
    `shutdown_hook_source`, `startup_hook_kwargs` and `shutdown_hook_kwargs`
    * uvicorn server configuration: `uvicorn_host`, `uvicorn_port`,
    `uvicorn_workers` and `uvicorn_kwargs`

    In addition to the above, the following advanced features can be used to
    customize the implementation-specific details of the deployment application:

    * custom endpoints (e.g. custom metrics, custom health, etc.): `custom_endpoints`
    * custom middlewares (e.g. authentication, logging, etc.): `custom_middlewares`
    * application building extensions - these are pluggable components that can
    be used to add advanced framework-specific features like custom authentication,
    logging, metrics, etc.: `app_extensions`

    Ultimately, if neither of the above are sufficient, the user can provide a
    custom implementations for the two core components that are used to build
    and run the deployment application itself:

    * the deployment app runner - this is the component that is responsible for
    building and running the ASGI application. It is represented by the
    `zenml.deployers.server.BaseDeploymentAppRunner` class.
    See: `deployment_app_runner_flavor` and `deployment_app_runner_kwargs`
    * the deployment service - this is the component that is responsible for
    handling the business logic of the pipeline deployment. It is represented by
    the `zenml.deployers.server.BaseDeploymentService` class. See:
    `deployment_service_class` and `deployment_service_kwargs`

    Both of these base classes or their existing implementations can be extended
    and provided as sources in the deployment settings to be loaded at runtime.

    Attributes:
        app_title: Title of the deployment application.
        app_description: Description of the deployment application.
        app_version: Version of the deployment application.
        app_kwargs: Arbitrary framework-specific keyword arguments to be passed
            to the deployment ASGI application constructor.

        include_default_endpoints: Whether to include the default endpoints in
            the ASGI application. Can be a boolean or a list of default endpoints
            to include. See the `DeploymentDefaultEndpoints` enum for the available
            default endpoints.
        include_default_middleware: Whether to include the default middleware
            in the ASGI application. Can be a boolean or a list of default middleware
            to include. See the `DeploymentDefaultMiddleware` enum for the available
            default middleware.

        root_url_path: Root URL path.
        docs_url_path: URL path for the OpenAPI documentation endpoint.
        redoc_url_path: URL path for the Redoc documentation endpoint.
        api_url_path: URL path for the API endpoints.
        invoke_url_path: URL path for the API invoke endpoint.
        health_url_path: URL path for the API health check endpoint.
        info_url_path: URL path for the API info endpoint.
        metrics_url_path: URL path for the API metrics endpoint.
        dashboard_files_path: Path where the dashboard static files (e.g. for an
            single-page application) are located. This can be used to replace the
            default UI that is included with the deployment ASGI application.
            The referenced directory must contain at a minimum an `index.html`
            file. One or more subdirectories can be included to serve static
            files (e.g. /assets, /css, /js, etc.). The path must be relative to
            the source root (e.g. relative to the directory where `zenml init`
            was run or where the main running Python script is located).

        cors: Configuration for CORS.
        secure_headers: Configuration for secure headers.
        thread_pool_size: Size of the thread pool for the ASGI application.

        startup_hook: Custom startup hook for the ASGI application.
        shutdown_hook: Custom shutdown hook for the ASGI application.
        startup_hook_kwargs: Keyword arguments for the startup hook.
        shutdown_hook_kwargs: Keyword arguments for the shutdown hook.

        custom_endpoints: Custom endpoints for the ASGI application. See the
            `EndpointSpec` class for more details.
        custom_middlewares: Custom middlewares for the ASGI application. See the
            `MiddlewareSpec` class for more details.
        app_extensions: App extensions used to build the ASGI application. See
            the `AppExtensionSpec` class for more details.

        uvicorn_host: Host of the uvicorn server.
        uvicorn_port: Port of the uvicorn server.
        uvicorn_workers: Number of workers for the uvicorn server.
        uvicorn_reload: Whether to automatically reload the deployment when the
            code changes.
        log_level: Log level for the deployment application.
        uvicorn_kwargs: Keyword arguments for the uvicorn server.

        deployment_app_runner_flavor: Flavor of the deployment app runner. Must
            point to a class that extends the
            `zenml.deployers.server.BaseDeploymentAppRunnerFlavor` class.
        deployment_app_runner_kwargs: Keyword arguments for the deployment app
            runner. These will be passed to the constructor of the deployment app
            runner class.
        deployment_service_class: Class of the deployment service. Must point
            to a class that extends the
            `zenml.deployers.server.BaseDeploymentService` class.
        deployment_service_kwargs: Keyword arguments for the deployment service.
            These will be passed to the constructor of the deployment service class.
    """

    # These settings are only available at the pipeline level
    LEVEL: ClassVar[ConfigurationLevel] = ConfigurationLevel.PIPELINE

    app_title: Optional[str] = None
    app_description: Optional[str] = None
    app_version: Optional[str] = None
    app_kwargs: Dict[str, Any] = {}

    include_default_endpoints: DeploymentDefaultEndpoints = (
        DeploymentDefaultEndpoints.ALL
    )
    include_default_middleware: DeploymentDefaultMiddleware = (
        DeploymentDefaultMiddleware.ALL
    )

    root_url_path: str = DEFAULT_DEPLOYMENT_APP_ROOT_URL_PATH
    api_url_path: str = DEFAULT_DEPLOYMENT_APP_API_URL_PATH
    docs_url_path: str = DEFAULT_DEPLOYMENT_APP_DOCS_URL_PATH
    redoc_url_path: str = DEFAULT_DEPLOYMENT_APP_REDOC_URL_PATH
    invoke_url_path: str = DEFAULT_DEPLOYMENT_APP_INVOKE_URL_PATH
    health_url_path: str = DEFAULT_DEPLOYMENT_APP_HEALTH_URL_PATH
    info_url_path: str = DEFAULT_DEPLOYMENT_APP_INFO_URL_PATH
    metrics_url_path: str = DEFAULT_DEPLOYMENT_APP_METRICS_URL_PATH

    dashboard_files_path: Optional[str] = None
    cors: CORSConfig = CORSConfig()
    secure_headers: SecureHeadersConfig = SecureHeadersConfig()

    thread_pool_size: int = DEFAULT_DEPLOYMENT_APP_THREAD_POOL_SIZE

    startup_hook: Optional[SourceOrObjectField] = None
    shutdown_hook: Optional[SourceOrObjectField] = None
    startup_hook_kwargs: Dict[str, Any] = {}
    shutdown_hook_kwargs: Dict[str, Any] = {}

    # Framework-agnostic endpoint/middleware configuration
    custom_endpoints: Optional[List[EndpointSpec]] = None
    custom_middlewares: Optional[List[MiddlewareSpec]] = None

    # Pluggable app extensions for advanced features
    app_extensions: Optional[List[AppExtensionSpec]] = None

    uvicorn_host: str = "0.0.0.0"  # nosec
    uvicorn_port: int = 8000
    uvicorn_workers: int = 1
    uvicorn_reload: bool = False
    log_level: LoggingLevels = LoggingLevels.INFO

    uvicorn_kwargs: Dict[str, Any] = {}

    deployment_app_runner_flavor: Optional[SourceOrObjectField] = None
    deployment_app_runner_kwargs: Dict[str, Any] = {}
    deployment_service_class: Optional[SourceOrObjectField] = None
    deployment_service_kwargs: Dict[str, Any] = {}

    def load_sources(self) -> None:
        """Load source string into callable."""
        if self.startup_hook is not None:
            assert isinstance(self.startup_hook, SourceOrObject)
            self.startup_hook.load()
        if self.shutdown_hook is not None:
            assert isinstance(self.shutdown_hook, SourceOrObject)
            self.shutdown_hook.load()
        if self.deployment_app_runner_flavor is not None:
            assert isinstance(
                self.deployment_app_runner_flavor, SourceOrObject
            )
            self.deployment_app_runner_flavor.load()
        if self.deployment_service_class is not None:
            assert isinstance(self.deployment_service_class, SourceOrObject)
            self.deployment_service_class.load()

    def endpoint_enabled(self, endpoint: DeploymentDefaultEndpoints) -> bool:
        """Check if an endpoint is enabled.

        Args:
            endpoint: The endpoint to check.

        Returns:
            True if the endpoint is enabled, False otherwise.
        """
        return endpoint in self.include_default_endpoints

    def middleware_enabled(
        self, middleware: DeploymentDefaultMiddleware
    ) -> bool:
        """Check if a middleware is enabled.

        Args:
            middleware: The middleware to check.

        Returns:
            True if the middleware is enabled, False otherwise.
        """
        return middleware in self.include_default_middleware

    model_config = ConfigDict(
        # public attributes are mutable
        frozen=False,
        # prevent extra attributes during model initialization
        extra="ignore",
    )
