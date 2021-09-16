from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import ArtifactStoreTypes


class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    store_type: ArtifactStoreTypes = ArtifactStoreTypes.local
