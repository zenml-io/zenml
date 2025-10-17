"""Weather Agent Pipeline."""

import os
import time
from typing import Any, Dict

from pipelines.hooks import (
    InitConfig,
    cleanup_hook,
    init_hook,
)
from steps import analyze_weather_with_llm, get_weather

from zenml import pipeline
from zenml.config import DeploymentSettings, DockerSettings

# Import enums for type-safe capture mode configuration
from zenml.config.deployment_settings import (
    EndpointMethod,
    EndpointSpec,
    MiddlewareSpec,
)
from zenml.config.resource_settings import ResourceSettings
from zenml.config.source import SourceOrObject

docker_settings = DockerSettings(
    requirements=["openai"],
    prevent_build_reuse=True,
)


async def health_detailed() -> Dict[str, Any]:
    """Detailed health check with system metrics."""
    import psutil

    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }


class RequestTimingMiddleware:
    """ASGI middleware to measure request processing time.

    Uses the standard ASGI interface (scope, receive, send) which works
    across all ASGI frameworks: FastAPI, Django, Starlette, Quart, etc.
    """

    def __init__(self, app):
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
        """
        self.app = app

    async def __call__(self, scope, receive, send):
        """Process ASGI request with timing measurement.

        Args:
            scope: ASGI connection scope (contains request info).
            receive: Async callable to receive ASGI events.
            send: Async callable to send ASGI events.
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.time()

        async def send_wrapper(message):
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


deployment_settings = DeploymentSettings(
    custom_endpoints=[
        EndpointSpec(
            path="/health/detailed",
            method=EndpointMethod.GET,
            handler=SourceOrObject(health_detailed),
            auth_required=False,
        ),
    ],
    custom_middlewares=[
        MiddlewareSpec(
            middleware=SourceOrObject(RequestTimingMiddleware),
            order=10,
        ),
    ],
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
            "generate_auth_key": True,
        },
        "deployer.gcp": {
            "allow_unauthenticated": True,
            # "location": "us-central1",
            "generate_auth_key": True,
        },
        "deployer.aws": {
            "generate_auth_key": True,
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
) -> str:
    """Weather agent pipeline.

    Args:
        city: City name to analyze weather for

    Returns:
        LLM-powered weather analysis and recommendations
    """
    weather_data = get_weather(city=city)
    result = analyze_weather_with_llm(weather_data=weather_data, city=city)
    return result
