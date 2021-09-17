from typing import Optional

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.metadata.sqlite_metadata_wrapper import SQLiteMetadataStore
from zenml.providers.base_provider import BaseProvider


class LocalProvider(BaseProvider):
    """Default local provider."""

    provider_type: str = "local"
    metadata_store: Optional[SQLiteMetadataStore]
    artifact_store: Optional[LocalArtifactStore]
    orchestrator: Optional[str] = "local"
