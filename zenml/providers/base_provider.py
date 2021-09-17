from typing import Optional, Text

from pydantic import BaseModel

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.metadata.metadata_wrapper import BaseMetadataStore


class BaseProvider(BaseModel):
    """Base provider for ZenML.

    A ZenML provider brings together an Metadata Store, an Artifact Store, and
    an Orchestrator, the trifecta of the environment required to run a ZenML
    pipeline. A ZenML provider also happens to be a pydantic `BaseSettings`
    class, which means that there are multiple ways to use it.
    """

    provider_type: Text = "base"
    metadata_store: Optional[BaseMetadataStore]
    artifact_store: Optional[BaseArtifactStore]
    orchestrator: Optional[str]
