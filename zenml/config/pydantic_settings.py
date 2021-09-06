from pydantic import BaseModel, BaseSettings

from zenml.artifacts.artifact_store import BaseArtifactStore
from zenml.metadata.metadata_wrapper import BaseMetadataStore


class SubModel(BaseModel):
    """Test"""

    foo = "bar"
    apple = 1


class Settings(BaseSettings):
    """Base Settings for ZenML."""

    metadata_store: BaseMetadataStore
    artifact_store: BaseArtifactStore

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_"


print(Settings().dict())
