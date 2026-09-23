# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""The port through which execution retention reaches archive objects.

The SQL store owns every retention algorithm, but archive objects live
outside the database. This interface is all the store knows about them: it
never learns which backend holds the bytes, which credentials reach it, or how
object names map to paths. The server supplies the implementation.

The store never calls these methods while it holds an open SQL transaction,
so slow or remote object I/O cannot extend a row lock.
"""

from abc import ABC, abstractmethod
from uuid import UUID


class ArchiveStorage(ABC):
    """Reads and writes the objects that hold archived run detail."""

    @abstractmethod
    def object_uri(
        self, project_id: UUID, run_id: UUID, bundle_id: UUID
    ) -> str:
        """Name the object that will hold one run's archived detail.

        The store records the returned value on the bundle row and passes it
        back unchanged to `read` and `remove`; it never interprets it.

        Args:
            project_id: Owning project.
            run_id: Archived run.
            bundle_id: Bundle row identity, unique per archive attempt.

        Returns:
            An object location unique to this attempt.
        """

    @abstractmethod
    def write(self, uri: str, data: bytes) -> None:
        """Write one uniquely named archive object.

        Args:
            uri: Location returned by `object_uri`.
            data: Object bytes.

        Raises:
            ExecutionRetentionUnavailableError: The write failed.
        """  # noqa: DOC502

    @abstractmethod
    def read(self, uri: str, max_bytes: int) -> bytes:
        """Read one object, stopping one byte past the expected size.

        Args:
            uri: Location recorded on a bundle row, possibly written under a
                previously configured archive root.
            max_bytes: Largest size the caller accepts.

        Returns:
            At most `max_bytes + 1` bytes, so callers detect oversized data.

        Raises:
            ExecutionRetentionUnavailableError: The object could not be read.
        """  # noqa: DOC502

    @abstractmethod
    def remove(self, uri: str) -> bool:
        """Remove an object after its detail is no longer needed.

        Implementations must not raise. A failed cleanup retains its catalog
        entry so a later deletion request can retry it.

        Args:
            uri: Recorded object location, possibly at a former archive root.

        Returns:
            True when absent; False if deletion failed.
        """

    @abstractmethod
    def probe(self) -> bool:
        """Check that new objects can be written and read back.

        Returns:
            Whether a unique probe object round-tripped.
        """
