# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archived detail fetched and verified independently for every request.

A detailed read of archived rows happens in two phases around storage I/O.
The first SQL phase resolves each row's bundle. The compressed objects are
then downloaded outside any transaction, capped in count and total size. The
second SQL phase checks that the rows still point at the same bundles and
decodes them one at a time, so only one decoded document is alive at once.
"""

from typing import Dict, Iterable, Optional, Protocol, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlmodel import Session, col

from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.retention.format import (
    MAX_OBJECT_BYTES,
    ArchiveDocument,
    decode,
)
from zenml.zen_stores.retention.storage import ArchiveStorage
from zenml.zen_stores.retention.transactions import batches
from zenml.zen_stores.schemas import ArchiveBundleSchema
from zenml.zen_stores.schemas.archive_detail import BundleDetail

MAX_BUNDLES_PER_READ = 20
MAX_COMPRESSED_BYTES_PER_READ = MAX_OBJECT_BYTES

NARROW_THE_READ = (
    "This read needs more archived detail than one request may load. List "
    "without details (`hydrate=False`), use a smaller page, or narrow the "
    "filter."
)


class ArchiveMarked(Protocol):
    """A row that may carry an archive marker."""

    @property
    def id(self) -> UUID:
        """Row identity.

        Returns:
            The row ID.
        """
        ...

    @property
    def project_id(self) -> UUID:
        """Owning project.

        Returns:
            The project ID.
        """
        ...

    @property
    def archive_bundle_id(self) -> Optional[UUID]:
        """Bundle holding the row's detail.

        Returns:
            The bundle ID, or None while the detail is in SQL.
        """
        ...


class BundleReference(BaseModel):
    """A bundle row detached from the SQL session that read it."""

    model_config = ConfigDict(frozen=True)

    bundle_id: UUID
    project_id: UUID
    run_id: Optional[UUID]
    uri: str
    size_bytes: int
    content_hash: str


def resolve_references(
    session: Session, rows: Iterable[ArchiveMarked]
) -> Dict[UUID, BundleReference]:
    """Resolve the bundle rows that marked rows point to.

    Args:
        session: Current read transaction.
        rows: Loaded rows, archived or not.

    Returns:
        References keyed by bundle ID; empty when every row is in SQL.

    Raises:
        ExecutionRetentionIntegrityError: A marker has no bundle row, or a
            bundle spans projects.
    """
    projects: Dict[UUID, UUID] = {}
    for row in rows:
        bundle_id = row.archive_bundle_id
        if bundle_id is None:
            continue
        if projects.setdefault(bundle_id, row.project_id) != row.project_id:
            raise ExecutionRetentionIntegrityError(
                "Archive bundle is referenced across project boundaries."
            )
    references: Dict[UUID, BundleReference] = {}
    for group in batches(projects):
        for bundle in session.execute(
            select(ArchiveBundleSchema).where(
                col(ArchiveBundleSchema.id).in_(group)
            )
        ).scalars():
            if bundle.project_id != projects[bundle.id]:
                raise ExecutionRetentionIntegrityError(
                    "Archive bundle belongs to another project."
                )
            references[bundle.id] = BundleReference(
                bundle_id=bundle.id,
                project_id=bundle.project_id,
                run_id=bundle.run_id,
                uri=bundle.uri,
                size_bytes=bundle.size_bytes,
                content_hash=bundle.content_hash,
            )
    if len(references) != len(projects):
        raise ExecutionRetentionIntegrityError(
            "Archive marker has no bundle record."
        )
    return references


def index_document(document: ArchiveDocument) -> BundleDetail:
    """Index a verified document by record type and identity.

    Args:
        document: Decoded and validated archive document.

    Returns:
        A request-local index for response conversion.
    """
    detail = BundleDetail()
    detail.runs[document.run.id] = document.run
    for step in document.steps:
        detail.steps[step.id] = step
    for snapshot in document.snapshots:
        detail.snapshots[snapshot.id] = snapshot
    for configuration in document.configurations:
        detail.add_configuration(configuration)
    return detail


class FetchedBundles:
    """Compressed objects for one request, decoded on demand one at a time."""

    def __init__(
        self,
        references: Dict[UUID, BundleReference],
        objects: Dict[UUID, bytes],
    ) -> None:
        """Hold downloaded objects until the second SQL phase converts rows.

        Args:
            references: Bundle rows resolved in the first SQL phase.
            objects: Compressed object bytes keyed by bundle ID.
        """
        self.references = references
        self._objects = objects
        self._current: Optional[tuple[UUID, BundleDetail]] = None

    def detail(self, bundle_id: UUID) -> BundleDetail:
        """Decode one bundle, releasing the previously decoded one.

        Args:
            bundle_id: Bundle to decode.

        Returns:
            The verified detail index.

        Raises:
            ExecutionRetentionIntegrityError: The object is corrupt or holds
                another run's detail.
        """
        if self._current is not None and self._current[0] == bundle_id:
            return self._current[1]
        self._current = None
        reference = self.references[bundle_id]
        document = decode(self._objects[bundle_id], reference.content_hash)
        if document.project_id != reference.project_id or (
            reference.run_id is not None
            and document.run_id != reference.run_id
        ):
            raise ExecutionRetentionIntegrityError(
                "Archive content belongs to another run."
            )
        self._current = (bundle_id, index_document(document))
        return self._current[1]

    def for_rows(
        self, rows: Sequence[ArchiveMarked]
    ) -> Optional[BundleDetail]:
        """Return the detail of the single bundle a set of rows uses.

        One run's rows always share a bundle: a snapshot is only archived
        with a run when nothing outside that run uses it.

        Args:
            rows: Rows converted into one response.

        Returns:
            The detail index, or None when every row is in SQL.

        Raises:
            ExecutionRetentionIntegrityError: The rows span several bundles.
        """
        bundle_ids = {
            row.archive_bundle_id
            for row in rows
            if row.archive_bundle_id is not None
        }
        if not bundle_ids:
            return None
        if len(bundle_ids) > 1:
            raise ExecutionRetentionIntegrityError(
                "One execution's archived detail spans several bundles."
            )
        return self.detail(bundle_ids.pop())


class ArchiveReader:
    """Download the bundles one request needs."""

    def __init__(self, storage: ArchiveStorage) -> None:
        """Bind the archive storage.

        Args:
            storage: Storage rooted at the server's archive URI.
        """
        self._storage = storage

    def fetch(self, references: Dict[UUID, BundleReference]) -> FetchedBundles:
        """Download compressed objects within the per-request limits.

        Args:
            references: Bundle rows resolved in the first SQL phase.

        Returns:
            The downloaded objects, not yet decoded.

        Raises:
            ExecutionArchivedError: The read needs more bundles or bytes than
                one request may load.
            ExecutionRetentionIntegrityError: An object's size differs from
                its bundle row.
        """
        if (
            len(references) > MAX_BUNDLES_PER_READ
            or sum(reference.size_bytes for reference in references.values())
            > MAX_COMPRESSED_BYTES_PER_READ
        ):
            raise ExecutionArchivedError(NARROW_THE_READ)
        objects: Dict[UUID, bytes] = {}
        for bundle_id, reference in references.items():
            data = self._storage.read(reference.uri, reference.size_bytes)
            if len(data) != reference.size_bytes:
                raise ExecutionRetentionIntegrityError(
                    "Archive object size differs from its bundle record."
                )
            objects[bundle_id] = data
        return FetchedBundles(references, objects)


def no_bundles() -> FetchedBundles:
    """Return the empty fetch used when every requested row is in SQL.

    Returns:
        A fetch that holds no objects.
    """
    return FetchedBundles({}, {})
