from pydantic import BaseSettings

from zenml.artifacts.artifact_store import BaseArtifactStore
from zenml.metadata.metadata_wrapper import BaseMetadataStore


class Settings(BaseSettings):
    """Base Settings for ZenML."""

    metadata_store: BaseMetadataStore
    artifact_store: BaseArtifactStore

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_"
