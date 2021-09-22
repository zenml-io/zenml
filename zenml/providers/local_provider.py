from typing import Optional

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.metadata.sqlite_metadata_wrapper import SQLiteMetadataStore
from zenml.providers.base_provider import BaseProvider
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator


class LocalProvider(BaseProvider):
    """Default local provider."""

    provider_type: str = "local"
    metadata_store: Optional[SQLiteMetadataStore] = SQLiteMetadataStore()
    artifact_store: Optional[LocalArtifactStore] = LocalArtifactStore()
    orchestrator: Optional[LocalOrchestrator] = LocalOrchestrator()
