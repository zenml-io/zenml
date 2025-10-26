"""Simple ZenML Pipeline - The minimal example to get started."""

from typing import Annotated, Optional

from steps.simple_step import simple_step

from zenml import pipeline
from zenml.config import CORSConfig, DeploymentSettings, DockerSettings

docker_settings = DockerSettings(
    requirements="requirements.txt",
)

deployment_settings = DeploymentSettings(
    app_title="Simple Pipeline",
    cors=CORSConfig(allow_origins=["*"]),
)


@pipeline(
    settings={
        "docker": docker_settings,
        "deployment": deployment_settings,
    },
    enable_cache=False,
)
def simple_pipeline(name: Optional[str] = None) -> Annotated[str, "greeting"]:
    """A simple pipeline that demonstrates ZenML basics.

    This pipeline:
    1. Takes an optional name parameter
    2. Calls a single step that returns a personalized greeting
    3. Returns the result as a tracked artifact

    Supports both batch and deployment modes:
    - Batch: python run.py
    - Deploy: zenml pipeline deploy pipelines.simple_pipeline.simple_pipeline
    - Invoke: zenml deployment invoke simple_pipeline --name="Alice"

    Args:
        name: Optional name to personalize the greeting

    Returns:
        A greeting message as an artifact
    """
    greeting = simple_step(name=name)
    return greeting
