"""Implementation of the ZenML Artifact Store."""

from zenml.integrations.s3.artifact_stores.s3_artifact_store import (  # noqa
    S3ArtifactStore,
)


class ZenMLArtifactStore(S3ArtifactStore):
    """ZenML specialized Artifact Store that inherits from S3 Artifact Store.
    
    This class extends the S3ArtifactStore to provide ZenML-specific 
    functionality and customizations for artifact storage.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the ZenML Artifact Store.
        
        Args:
            *args: Arguments to pass to the parent class.
            **kwargs: Keyword arguments to pass to the parent class.
        """
        super().__init__(*args, **kwargs) 