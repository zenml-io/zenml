"""Weather Agent Pipeline."""

import os

from pipelines.hooks import (
    InitConfig,
    cleanup_hook,
    init_hook,
)
from steps import analyze_weather_with_llm, get_weather

from zenml import pipeline
from zenml.config import DockerSettings

# Import enums for type-safe capture mode configuration
from zenml.config.docker_settings import PythonPackageInstaller
from zenml.config.resource_settings import ResourceSettings

docker_settings = DockerSettings(
    requirements=["openai"],
    prevent_build_reuse=True,
    python_package_installer=PythonPackageInstaller.UV,
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
    """Weather agent pipeline optimized for run-only serving.

    Automatically uses run-only architecture for millisecond-class latency:
    - Zero database writes
    - Zero filesystem operations
    - In-memory step output handoff
    - Perfect for real-time inference

    Args:
        city: City name to analyze weather for

    Returns:
        LLM-powered weather analysis and recommendations
    """
    weather_data = get_weather(city=city)
    result = analyze_weather_with_llm(weather_data=weather_data, city=city)
    return result
