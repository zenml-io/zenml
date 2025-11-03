"""Weather Agent Pipeline."""

import os
import time
import uuid
from typing import Any, Awaitable, Callable, Dict

from asgiref.compatibility import guarantee_single_callable
from asgiref.typing import (
    ASGIApplication,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    Scope,
)
from pipelines.hooks import (
    InitConfig,
    cleanup_hook,
    init_hook,
)
from starlette.middleware.gzip import GZipMiddleware
from steps import analyze_weather_with_llm, get_weather

from zenml import pipeline
from zenml.config import (
    DeploymentSettings,
    DockerSettings,
    EndpointMethod,
    EndpointSpec,
    MiddlewareSpec,
    ResourceSettings,
    SecureHeadersConfig,
)
from zenml.config.deployment_settings import DeploymentDefaultMiddleware
from zenml.deployers.server.app import BaseDeploymentAppRunner
from zenml.enums import LoggingLevels
from zenml.models import DeploymentResponse

docker_settings = DockerSettings(
    requirements=["openai"],
    prevent_build_reuse=True,
)


async def health_detailed() -> Dict[str, Any]:
    """Detailed health check with system metrics."""
    import psutil

    from zenml.client import Client

    client = Client()

    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "zenml": client.zen_store.get_store_info().model_dump(),
    }


class RequestTimingMiddleware:
    """ASGI middleware to measure request processing time.

    Uses the standard ASGI interface (scope, receive, send) which works
    across all ASGI frameworks: FastAPI, Django, Starlette, Quart, etc.
    """

    def __init__(self, app: ASGIApplication):
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
        """
        self.app = guarantee_single_callable(app)

    async def __call__(
        self,
        scope: Scope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        """Process ASGI request with timing measurement.

        Args:
            scope: ASGI connection scope (contains request info).
            receive: Async callable to receive ASGI events.
            send: Async callable to send ASGI events.
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()

        async def send_wrapper(message: ASGISendEvent) -> None:
            """Intercept response to add timing header."""
            if message["type"] == "http.response.start":
                process_time = (time.time() - start_time) * 1000
                headers = list(message.get("headers", []))
                headers.append(
                    (
                        b"x-process-time-ms",
                        str(process_time).encode(),
                    )
                )
                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_wrapper)


def build_deployment_info(
    app_runner: BaseDeploymentAppRunner,
) -> Callable[[], Awaitable[DeploymentResponse]]:
    """Build the deployment info endpoint.

    Args:
        app_runner: The deployment app runner.

    Returns:
        The deployment info endpoint.
    """

    async def endpoint() -> DeploymentResponse:
        return app_runner.deployment

    return endpoint


async def request_id_middleware(
    app: ASGIApplication,
    scope: Scope,
    receive: ASGIReceiveCallable,
    send: ASGISendCallable,
    header_name: str = "x-request-id",
) -> None:
    """ASGI function middleware that ensures a correlation ID header exists."""

    app = guarantee_single_callable(app)

    if scope["type"] != "http":
        await app(scope, receive, send)
        return

    # Reuse existing request ID if present; otherwise generate one
    request_id = None
    for k, v in scope.get("headers", []):
        if k.decode().lower() == header_name:
            request_id = v.decode()
            break

    if not request_id:
        request_id = str(uuid.uuid4())

    async def send_wrapper(message: ASGISendEvent) -> None:
        if message["type"] == "http.response.start":
            headers = list(message.get("headers", []))
            headers.append((header_name.encode(), request_id.encode()))
            message = {**message, "headers": headers}

        await send(message)

    await app(scope, receive, send_wrapper)


def on_startup(
    app_runner: BaseDeploymentAppRunner, warm: bool = False
) -> None:
    """Startup hook.

    Args:
        app_runner: The deployment app runner.
        warm: Whether to warm the app.
    """
    print(f"Startup hook called with warm={warm}")


def on_shutdown(
    app_runner: BaseDeploymentAppRunner, drain_timeout_s: int = 2
) -> None:
    """Shutdown hook.

    Args:
        app_runner: The deployment app runner.
        drain_timeout_s: The drain timeout in seconds.
    """
    print(f"Shutdown hook called with drain_timeout_s={drain_timeout_s}")


deployment_settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/health",
            method=EndpointMethod.GET,
            handler=health_detailed,
            auth_required=False,
        ),
        EndpointSpec(
            path="/deployment",
            method=EndpointMethod.GET,
            handler=build_deployment_info,
            auth_required=True,
        ),
    ],
    custom_middlewares=[
        MiddlewareSpec(
            middleware=RequestTimingMiddleware,
            order=10,
        ),
        MiddlewareSpec(
            middleware=request_id_middleware,
            order=5,
            init_kwargs={"header_name": "x-request-id"},
        ),
        MiddlewareSpec(
            middleware=GZipMiddleware,
            native=True,
            order=20,
            extra_kwargs={"minimum_size": 1024},
        ),
    ],
    dashboard_files_path="ui",
    secure_headers=SecureHeadersConfig(
        csp=(
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'"
        ),
    ),
    startup_hook=on_startup,
    shutdown_hook=on_shutdown,
    startup_hook_kwargs={"warm": True},
    shutdown_hook_kwargs={"drain_timeout_s": 2},
    include_default_middleware=DeploymentDefaultMiddleware.CORS
    | DeploymentDefaultMiddleware.SECURE_HEADERS,
    log_level=LoggingLevels.DEBUG,
)

environment = {}
if os.getenv("OPENAI_API_KEY"):
    environment["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


@pipeline(
    enable_cache=False,
    on_init=init_hook,
    on_init_kwargs={"config": InitConfig(organization=None, project=None)},
    on_cleanup=cleanup_hook,
    settings={
        "docker": docker_settings,
        "deployment": deployment_settings,
        "deployer": {
            "generate_auth_key": False,
        },
        "resources": ResourceSettings(
            memory="1GB",
            cpu_count=1,
            min_replicas=1,
            max_replicas=5,
            max_concurrency=10,
        ),
    },
    environment=environment,
)
def weather_agent(
    city: str = "London",
) -> tuple[Dict[str, float], str]:
    """Weather agent pipeline.

    Args:
        city: City name to analyze weather for

    Returns:
        LLM-powered weather analysis and recommendations
    """
    weather_data = get_weather(city=city)
    result = analyze_weather_with_llm(weather_data=weather_data, city=city)
    return weather_data, result
