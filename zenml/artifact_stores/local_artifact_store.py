from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.core.component_factory import artifact_store_factory
from zenml.enums import ArtifactStoreTypes


@artifact_store_factory.register(ArtifactStoreTypes.local)
class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""
