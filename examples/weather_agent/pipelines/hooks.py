"""Pipeline state and init/cleanup hooks for the weather agent pipeline."""

from typing import Optional

from pydantic import BaseModel

from zenml.config import DockerSettings
from zenml.config.docker_settings import PythonPackageInstaller

docker_settings = DockerSettings(
    requirements=["openai"],
    prevent_build_reuse=True,
    python_package_installer=PythonPackageInstaller.UV,
)


class PipelineState:
    """Pipeline state."""

    def __init__(
        self, organization: Optional[str] = None, project: Optional[str] = None
    ) -> None:
        """Initialize the pipeline state."""
        self.openai_client = None

        try:
            # Try to use OpenAI API if available
            import os

            try:
                import openai
            except ImportError:
                raise ImportError("OpenAI package not available")

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ImportError("OpenAI API key not found")

            self.openai_client = openai.OpenAI(
                api_key=api_key,
                organization=organization,
                project=project,
            )
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")


class InitConfig(BaseModel):
    """Init config."""

    organization: Optional[str] = None
    project: Optional[str] = None


def init_hook(
    config: InitConfig,
) -> PipelineState:
    """Initialize the pipeline."""
    print("Initializing the pipeline...")

    return PipelineState(
        organization=config.organization, project=config.project
    )


def cleanup_hook() -> None:
    """Cleanup the pipeline."""
    print("Cleaning up the pipeline...")
