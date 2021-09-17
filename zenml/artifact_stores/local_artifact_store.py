import os.path
from typing import Optional, Text

from pydantic import Field

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import ArtifactStoreTypes
from zenml.utils.path_utils import get_zenml_config_dir


class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    store_type: ArtifactStoreTypes = ArtifactStoreTypes.local
    path: Optional[Text] = Field(
        default=os.path.join(get_zenml_config_dir(), "local_store")
    )
