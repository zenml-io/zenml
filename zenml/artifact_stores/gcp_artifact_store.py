from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import ArtifactStoreTypes


class GCPArtifactStore(BaseArtifactStore):
    """Artifact Store for Google Cloud Storage based artifacts."""

    store_type: ArtifactStoreTypes = ArtifactStoreTypes.gcp
