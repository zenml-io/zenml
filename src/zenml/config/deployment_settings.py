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

from enum import Enum
from typing import (
    TYPE_CHECKING,
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
from zenml.enums import LoggingLevels
from zenml.logger import get_logger
from zenml.utils.source_utils import SourceOrObjectField

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

DEFAULT_DEPLOYMENT_APP_THREAD_POOL_SIZE = 20

DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_HSTS = (
    "max-age=63072000; includeSubdomains"
)
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XFO = "SAMEORIGIN"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XXP = "0"
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CONTENT = "nosniff"
_csp_script_src_urls: List[str] = []
_csp_connect_src_urls: List[str] = []
_csp_img_src_urls: List[str] = []
_csp_frame_src_urls: List[str] = []
DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_CSP = (
    "default-src 'none'; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "img-src 'self'; "
    "style-src 'self'; "
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

    1. The function that represents the actual middleware implementation. This
    will be registered as is. The function itself may be framework-specific.

    ```python
    async def my_middleware(request: Request, call_next) -> Response:
        # Process request
        response = await call_next(request)
        # Process response
        return response
    ```

    2. A middleware class - this is a class that implements the middleware
    logic. When this is used, the class constructor must accept an argument
    `app_runner` of type `BaseDeploymentAppRunner` which will be passed by the
    adapter at application build time.

    The adapter will also pass the `init_kwargs` to the class constructor if
    configured. The following is an example of a middleware class:

    ```python
    class MyMiddleware:
        def __init__(
            self,
            app_runner: "BaseDeploymentAppRunner",
            **kwargs: Any,
        ) -> None:
            self.app_runner = app_runner
            self.kwargs = kwargs

        async def __call__(
            self, request: Request, call_next
        ) -> Response:
            # Middleware logic
            ...
    ```

    3. A middleware builder function - this is a function that is used to
    build and return the middleware. When this is used, the adapter will call
    the provided function first and is expected to return the actual middleware
    function. The builder function must accept an argument `app_runner` of type
    `BaseDeploymentAppRunner` which will be passed by the adapter at
    application build time.

    The adapter will also pass the `init_kwargs` to the builder function if
    configured. The following is an example of a middleware builder function:

    ```python
    def my_middleware_builder(
        app_runner: "BaseDeploymentAppRunner",
        **kwargs: Any,
    ) -> Callable:
        ...

        async def middleware(request: Request, call_next) -> Response:
            # Middleware logic
            ...

        return middleware
    ```

    4. Alternatively, the middleware can be set to any framework-specific
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
    class MyExtension(BaseAppExtension):

        def __init__(self, **kwargs):
            ...
            self.router = APIRouter()
            ...

        def install(self, app_runner: BaseDeploymentAppRunner, **kwargs) -> None:

            app_runner.asgi_app.include_router(self.router)
    ```

    Attributes:
        extension: Extension callable/class or source.
        extension_kwargs: Configuration passed during initialization.
    """

    extension: SourceOrObjectField
    extension_kwargs: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def load_sources(self) -> None:
        """Load source string into callable."""
        if not self.extension.is_loaded:
            self.extension.load()

    def resolve_extension_handler(
        self,
    ) -> Callable[..., Any]:
        """Resolve the extension handler from the spec."""
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
    allow_methods: List[str] = ["GET", "OPTIONS"]
    allow_headers: List[str] = ["*"]
    allow_credentials: bool = True


class SecureHeadersConfig(BaseModel):
    """Configuration for secure headers."""

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
    xxp: Union[bool, str] = Field(
        default=DEFAULT_DEPLOYMENT_APP_SECURE_HEADERS_XXP,
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


class DeploymentSettings(BaseSettings):
    """Settings for the pipeline deployment."""

    # This settings is only available at the pipeline level
    LEVEL: ClassVar[ConfigurationLevel] = ConfigurationLevel.PIPELINE

    app_title: Optional[str] = None
    app_description: Optional[str] = None
    app_version: Optional[str] = None
    app_kwargs: Dict[str, Any] = {}

    root_url_path: str = ""
    docs_url_path: str = "/docs"
    redoc_url_path: str = "/redoc"
    invoke_url_path: str = "/invoke"
    health_url_path: str = "/health"
    info_url_path: str = "/info"
    metrics_url_path: str = "/metrics"

    dashboard_files_path: str = ""

    cors: CORSConfig = CORSConfig()
    secure_headers: SecureHeadersConfig = SecureHeadersConfig()

    thread_pool_size: int = DEFAULT_DEPLOYMENT_APP_THREAD_POOL_SIZE

    startup_hook_source: Optional[SourceOrObjectField] = None
    shutdown_hook_source: Optional[SourceOrObjectField] = None
    startup_hook_kwargs: Dict[str, Any] = {}
    shutdown_hook_kwargs: Dict[str, Any] = {}

    # Framework-agnostic endpoint/middleware configuration
    custom_endpoints: Optional[List[EndpointSpec]] = None
    custom_middlewares: Optional[List[MiddlewareSpec]] = None

    # Pluggable app extensions for advanced features
    app_extensions: Optional[List[AppExtensionSpec]] = None

    # Include default endpoints in the deployment application
    include_default_endpoints: bool = True

    # Include default middleware in the deployment application
    include_default_middleware: bool = True

    uvicorn_host: str = "0.0.0.0"
    uvicorn_port: int = 8000
    uvicorn_workers: int = 1
    log_level: LoggingLevels = LoggingLevels.INFO

    uvicorn_kwargs: Dict[str, Any] = {}

    deployment_app_runner_source: Optional[SourceOrObjectField] = None
    deployment_app_runner_kwargs: Dict[str, Any] = {}
    deployment_service_source: Optional[SourceOrObjectField] = None
    deployment_service_kwargs: Dict[str, Any] = {}

    def load_sources(self) -> None:
        """Load source string into callable."""
        if self.startup_hook_source is not None:
            self.startup_hook_source.load()
        if self.shutdown_hook_source is not None:
            self.shutdown_hook_source.load()
        if self.deployment_app_runner_source is not None:
            self.deployment_app_runner_source.load()
        if self.deployment_service_source is not None:
            self.deployment_service_source.load()

    model_config = ConfigDict(
        # public attributes are mutable
        frozen=False,
        # prevent extra attributes during model initialization
        extra="ignore",
    )
