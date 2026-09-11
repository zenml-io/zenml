# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Verified archived detail loaded independently for every request."""

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.exceptions import (
    ExecutionRetentionIntegrityError,
    ExecutionRetentionUnavailableError,
)
from zenml.zen_stores.retention.bundle import Bundle
from zenml.zen_stores.retention.manifest import (
    Manifest,
    Record,
    RunRecord,
    SnapshotRecord,
    StepRecord,
)
from zenml.zen_stores.schemas import ArchiveBundleSchema
from zenml.zen_stores.schemas.archive_detail import BundleDetail


def index_records(records: Sequence[Record]) -> BundleDetail:
    """Index verified records by their concrete archive record type.

    Dispatching on the manifest classes lets the type checker confirm that
    each record model satisfies the payload protocol conversion reads.

    Args:
        records: Records whose integrity and closure were verified.

    Returns:
        A typed request-local index.
    """
    detail = BundleDetail()
    for record in records:
        if isinstance(record, RunRecord):
            detail.runs[record.id] = record
        elif isinstance(record, StepRecord):
            detail.steps[record.id] = record
        elif isinstance(record, SnapshotRecord):
            detail.snapshots[record.id] = record
        else:
            detail.add_configuration(record)
    return detail


class BundleReference(BaseModel):
    """Retain the authorized catalog descriptor after the SQL session closes."""

    model_config = ConfigDict(frozen=True)

    project_id: UUID
    bundle_id: UUID
    uri: str
    manifest_hash: str

    @classmethod
    def from_bundle(cls, bundle: ArchiveBundleSchema) -> "BundleReference":
        """Return an authorized catalog descriptor detached from its session.

        Args:
            bundle: Complete catalog record with its immutable descriptor.

        Returns:
            Hashable descriptor used for read authorization and revalidation.

        Raises:
            ExecutionRetentionIntegrityError: The object descriptor is incomplete.
        """
        if bundle.uri is None or bundle.manifest_hash is None:
            raise ExecutionRetentionIntegrityError(
                "Archive catalog descriptor is incomplete."
            )
        return cls(
            project_id=bundle.project_id,
            bundle_id=bundle.id,
            uri=bundle.uri,
            manifest_hash=bundle.manifest_hash,
        )


class ArchiveReader:
    """Download and verify the bundles needed by one request."""

    def __init__(self, storage: BaseArtifactStore) -> None:
        """Bind the registered archive destination.

        Args:
            storage: Loaded artifact store component.
        """
        self._storage = storage

    def detail_for(
        self, references: Sequence[BundleReference]
    ) -> BundleDetail:
        """Fetch required bundles and assemble one request-local index.

        Args:
            references: SQL-authorized descriptors needed by this request.

        Returns:
            A merged index of independently verified records.

        """
        distinct = {reference.bundle_id: reference for reference in references}
        merged = BundleDetail()
        for reference in distinct.values():
            merged.merge(self._fetch(reference))
        return merged

    def _fetch(self, reference: BundleReference) -> BundleDetail:
        """Download bounded bytes and verify the complete archived execution.

        Args:
            reference: Trusted catalog identity, path, and manifest checksum.

        Returns:
            Indexed records after object and relational verification.

        Raises:
            ExecutionRetentionIntegrityError: Bytes, identity, or structure differ.
            ExecutionRetentionUnavailableError: Storage could not be read.
        """
        try:
            return index_records(
                Bundle.fetch_records(
                    self._storage,
                    reference.uri,
                    reference.manifest_hash,
                    lambda manifest: self._require_identity(
                        reference, manifest
                    ),
                )
            )
        except ExecutionRetentionIntegrityError:
            raise
        except ValueError as error:
            raise ExecutionRetentionIntegrityError(
                "Archived execution detail failed archive verification."
            ) from error
        except Exception as error:
            raise ExecutionRetentionUnavailableError(
                "Archived execution detail storage is unavailable. Retry "
                "shortly."
            ) from error

    @staticmethod
    def _require_identity(
        reference: BundleReference, manifest: Manifest
    ) -> None:
        """Reject a manifest for another catalog record or project.

        Args:
            reference: Authorized catalog descriptor.
            manifest: Downloaded manifest whose checksum was verified.

        Raises:
            ExecutionRetentionIntegrityError: The manifest has another identity.
        """
        if (
            manifest.project_id != reference.project_id
            or manifest.bundle_id != reference.bundle_id
        ):
            raise ExecutionRetentionIntegrityError(
                "Manifest identity mismatch."
            )
