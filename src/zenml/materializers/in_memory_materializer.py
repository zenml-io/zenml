"""In-memory materializer for serving runtime.

Stores and loads Python objects directly from a process-local registry keyed
by the artifact URI. This avoids any filesystem or remote store IO and is
intended only for ephemeral runtime scenarios.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Tuple, Type

from zenml.deployers.serving import _in_memory_registry as reg
from zenml.enums import ArtifactType, VisualizationType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.metadata_types import MetadataType


class InMemoryMaterializer(BaseMaterializer):
    """Materializer that keeps artifact data in memory during runtime."""

    # Support any Python object
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (object,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.BASE
    SKIP_REGISTRATION: ClassVar[bool] = False

    def load(self, data_type: Type[Any]) -> Any:
        """Load an object from the in-memory registry.

        Args:
            data_type: The type of the object to load.

        Returns:
            The object.
        """
        if not reg.has_object(self.uri):
            # Nothing in memory; return None to signal absence
            return None

        obj = reg.get_object(self.uri)
        # Best-effort: if requested type is not compatible, still return object
        return obj

    def save(self, data: Any) -> None:
        """Save an object to the in-memory registry.

        Args:
            data: The object to save.
        """
        reg.put_object(self.uri, data)
        # Track URI for request-scoped cleanup when serving runtime is active
        try:
            from zenml.deployers.serving import runtime

            if runtime.is_active():
                runtime.note_in_memory_uri(self.uri)
        except Exception:
            # If runtime is not available, skip tracking
            pass

    # No visualizations when in-memory
    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Save visualizations for an object.

        Args:
            data: The object to save visualizations for.

        Returns:
            The visualizations.
        """
        return {}

    # Minimal metadata to avoid IO
    def extract_metadata(self, data: Any) -> Dict[str, MetadataType]:
        """Extract metadata for an object.

        Args:
            data: The object to extract metadata for.

        Returns:
            The metadata.
        """
        return {}

    def compute_content_hash(self, data: Any) -> str | None:
        # Avoid expensive hashing; return None to keep request optional
        """Compute the content hash for an object.

        Args:
            data: The object to compute the content hash for.

        Returns:
            The content hash.
        """
        return None
