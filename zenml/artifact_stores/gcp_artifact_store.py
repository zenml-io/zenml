from typing import Text

from pydantic import validator

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.core.component_factory import artifact_store_factory
from zenml.enums import ArtifactStoreTypes


@artifact_store_factory.register(ArtifactStoreTypes.gcp)
class GCPArtifactStore(BaseArtifactStore):
    """Artifact Store for Google Cloud Storage based artifacts."""

    @validator("path")
    def must_be_gcs_path(cls, v: Text):
        """Validates that the path is a valid gcs path."""
        if not v.startswith("gs://"):
            raise ValueError(
                "Must be a valid gcs path, i.e., starting with `gs://`"
            )
        return v
