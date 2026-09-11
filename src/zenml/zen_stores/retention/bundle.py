# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Bounded gzip/tar bundles with exact sections and relational validation."""

import gzip
import hashlib
import tarfile
import zlib
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, ClassVar, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.exceptions import ExecutionRetentionIntegrityError
from zenml.zen_stores.retention.manifest import (
    MAX_DECODED_BYTES,
    MAX_OBJECT_BYTES,
    MAX_RECORDS,
    RECORDS_BY_TABLE,
    TABLE_ORDER,
    ConfigurationRecord,
    Manifest,
    Record,
    RunRecord,
    Section,
    SnapshotRecord,
    StepRecord,
    UnsupportedArchiveFormatError,
    parse_record,
    record_bytes,
    sha256_hex,
)


class WrittenObject(BaseModel):
    """Name the local compressed object and its authenticated byte descriptor."""

    model_config = ConfigDict(frozen=True)

    path: Path
    size_bytes: int
    sha256: str


class Bundle(BaseModel):
    """Write and verify one execution archive and its detached manifest."""

    model_config = ConfigDict(frozen=True)

    # Four headers and up to four partial blocks, plus the final tar record.
    MAX_TAR_BYTES: ClassVar[int] = (
        MAX_DECODED_BYTES + len(TABLE_ORDER) * 1024 + tarfile.RECORDSIZE
    )
    manifest: Manifest
    path: Path

    @classmethod
    def fetch_records(
        cls,
        storage: BaseArtifactStore,
        uri: str,
        manifest_hash: str,
        identity_check: Callable[[Manifest], None],
    ) -> List[Record]:
        """Download and verify all records in one private scratch directory.

        Args:
            storage: Registered archive component.
            uri: Catalog object directory.
            manifest_hash: Expected canonical manifest checksum.
            identity_check: Check the caller's ownership contract.

        Returns:
            Fully verified records in manifest section order.
        """
        with TemporaryDirectory(prefix="zenml-archive-read-") as temporary:
            directory = Path(temporary)
            bundle = cls.download(
                storage,
                uri,
                manifest_hash,
                directory,
                identity_check,
            )
            return bundle.records(directory)

    @classmethod
    def download(
        cls,
        storage: BaseArtifactStore,
        uri: str,
        manifest_hash: str,
        directory: Path,
        verify_identity: Callable[[Manifest], None],
    ) -> "Bundle":
        """Download catalog-authenticated bytes with manifest and object bounds.

        Args:
            storage: Registered archive component.
            uri: Catalog object directory.
            manifest_hash: Expected canonical manifest checksum.
            directory: Local scratch directory.
            verify_identity: Check the caller's ownership contract before reading payload.

        Returns:
            Downloaded bundle for caller-specific identity and record validation.

        Raises:
            ExecutionRetentionIntegrityError: Manifest or object exceeds its contract.
        """
        with storage.open(f"{uri}/manifest.json", "rb") as source:
            encoded = source.read(Manifest.MAX_BYTES + 1)
        if (
            len(encoded) > Manifest.MAX_BYTES
            or sha256_hex(encoded) != manifest_hash
        ):
            raise ExecutionRetentionIntegrityError(
                "Manifest checksum or size mismatch."
            )
        try:
            manifest = Manifest.from_bytes(encoded)
        except UnsupportedArchiveFormatError as error:
            raise ExecutionRetentionIntegrityError(str(error)) from error
        verify_identity(manifest)
        path = directory / "rows.tar.gz"
        size = 0
        with (
            storage.open(f"{uri}/rows.tar.gz", "rb") as source,
            path.open("xb") as target,
        ):
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                size += len(chunk)
                if size > min(MAX_OBJECT_BYTES, manifest.object_bytes):
                    raise ExecutionRetentionIntegrityError(
                        "Archive object exceeds size limit."
                    )
                target.write(chunk)
        return cls(manifest=manifest, path=path)

    @classmethod
    def create(
        cls,
        records: List[Record],
        directory: Path,
        *,
        bundle_id: UUID,
        project_id: UUID,
        root_run_id: UUID,
        created_at: datetime,
    ) -> "Bundle":
        """Validate ownership and write canonical sections into a gzip tar.

        Args:
            records: Captured records ordered by table and identity.
            directory: Caller-owned empty scratch directory.
            bundle_id: Claimed archive identity.
            project_id: Authorized project identity.
            root_run_id: Canonical execution root.
            created_at: Archive timestamp.

        Returns:
            The written object with its final manifest.

        Raises:
            ExecutionRetentionIntegrityError: Invalid records or size bounds.
        """
        validate_closure(
            records, project_id=project_id, root_run_id=root_run_id
        )
        sections = cls._write_sections(records, directory)
        written = cls._write_object(directory, sections)
        try:
            manifest = Manifest(
                bundle_id=bundle_id,
                project_id=project_id,
                root_run_id=root_run_id,
                created_at=created_at,
                object_bytes=written.size_bytes,
                object_sha256=written.sha256,
                sections=sections,
            )
        except ValueError as exc:
            raise ExecutionRetentionIntegrityError(
                "Invalid archive manifest."
            ) from exc
        return cls(manifest=manifest, path=written.path)

    @staticmethod
    def _write_sections(
        records: List[Record], directory: Path
    ) -> List[Section]:
        """Write JSONL sections and compute their inventories in one pass.

        Args:
            records: Validated tree records in section identity order.
            directory: Private directory for section files.

        Returns:
            The four ordered section descriptors.

        Raises:
            ExecutionRetentionIntegrityError: Records exceed ordering or caps.
        """
        ids: Dict[str, List[UUID]] = {table: [] for table in TABLE_ORDER}
        hashes = {table: hashlib.sha256() for table in TABLE_ORDER}
        sizes = dict.fromkeys(TABLE_ORDER, 0)
        total_bytes = total_rows = 0
        with ExitStack() as stack:
            streams = {
                table: stack.enter_context(
                    (directory / f"{table}.jsonl").open("xb")
                )
                for table in TABLE_ORDER
            }
            for table in TABLE_ORDER:
                (directory / f"{table}.jsonl").chmod(0o600)
            for record in records:
                section_ids = ids[record.table]
                if section_ids and record.id <= section_ids[-1]:
                    raise ExecutionRetentionIntegrityError(
                        "Section records must have unique sorted IDs."
                    )
                line = record_bytes(record)
                total_bytes += len(line)
                total_rows += 1
                if total_bytes > MAX_DECODED_BYTES or total_rows > MAX_RECORDS:
                    raise ExecutionRetentionIntegrityError(
                        "Tree exceeds archive bounds."
                    )
                section_ids.append(record.id)
                sizes[record.table] += len(line)
                hashes[record.table].update(line)
                streams[record.table].write(line)
        return [
            Section(
                table=table,
                ids=ids[table],
                decoded_bytes=sizes[table],
                sha256=hashes[table].hexdigest(),
            )
            for table in TABLE_ORDER
        ]

    @staticmethod
    def _write_object(
        directory: Path, sections: List[Section]
    ) -> WrittenObject:
        """Compress the section files into a deterministic tar object.

        Args:
            directory: Private directory containing the four section files.
            sections: Ordered inventories with exact section sizes.

        Returns:
            The object path, byte size, and SHA-256 digest.

        Raises:
            ExecutionRetentionIntegrityError: The compressed object is oversized.
        """
        path = directory / "rows.tar.gz"
        with (
            path.open("xb") as raw,
            gzip.GzipFile(
                filename="", fileobj=raw, mode="wb", mtime=0
            ) as compressed,
            tarfile.open(fileobj=compressed, mode="w|") as archive,
        ):
            for section in sections:
                info = tarfile.TarInfo(f"{section.table}.jsonl")
                info.size, info.mode = section.decoded_bytes, 0o600
                with (directory / info.name).open("rb") as stream:
                    archive.addfile(info, stream)
        size_bytes = path.stat().st_size
        if size_bytes > MAX_OBJECT_BYTES:
            raise ExecutionRetentionIntegrityError(
                "Archive object exceeds size limit."
            )
        return WrittenObject(
            path=path,
            size_bytes=size_bytes,
            sha256=sha256_hex(path.read_bytes()),
        )

    def records(self, directory: Path) -> List[Record]:
        """Verify the entire compressed object and its relational closure.

        Args:
            directory: Private scratch directory for bounded decompression.

        Returns:
            Fully verified records in manifest section order.

        Raises:
            ExecutionRetentionIntegrityError: The object or its records are invalid.
        """
        if (
            self.path.stat().st_size != self.manifest.object_bytes
            or self.path.stat().st_size > MAX_OBJECT_BYTES
            or sha256_hex(self.path.read_bytes())
            != self.manifest.object_sha256
        ):
            raise ExecutionRetentionIntegrityError(
                "Archive object checksum or size mismatch."
            )
        unpacked = directory / "verified.tar"
        decoder = zlib.decompressobj(31)
        size = 0
        try:
            with self.path.open("rb") as source, unpacked.open("xb") as target:
                for chunk in iter(lambda: source.read(64 * 1024), b""):
                    decoded = decoder.decompress(
                        chunk, self.MAX_TAR_BYTES - size + 1
                    )
                    size += len(decoded)
                    if (
                        size > self.MAX_TAR_BYTES
                        or decoder.unconsumed_tail
                        or decoder.unused_data
                    ):
                        raise ExecutionRetentionIntegrityError(
                            "Oversized or trailing archive compression data."
                        )
                    target.write(decoded)
            if not decoder.eof:
                raise ExecutionRetentionIntegrityError(
                    "Truncated compressed archive."
                )
            records = self._read_sections(unpacked)
            validate_closure(
                records,
                project_id=self.manifest.project_id,
                root_run_id=self.manifest.root_run_id,
            )
            return records
        except (ValueError, zlib.error, tarfile.TarError, EOFError) as exc:
            raise ExecutionRetentionIntegrityError(
                "Malformed archive object."
            ) from exc
        finally:
            unpacked.unlink(missing_ok=True)

    def _read_sections(self, unpacked: Path) -> List[Record]:
        """Parse bounded sections without extracting archive members to disk.

        Args:
            unpacked: Bounded decompressed tar file.

        Returns:
            Parsed records with verified hashes and exact section identities.

        Raises:
            ExecutionRetentionIntegrityError: Any member or inventory disagrees.
        """
        records: List[Record] = []
        with tarfile.open(unpacked, mode="r:") as archive:
            for section in self.manifest.sections:
                member = archive.next()
                if (
                    member is None
                    or not member.isreg()
                    or member.name != f"{section.table}.jsonl"
                    or member.size != section.decoded_bytes
                    or member.pax_headers
                ):
                    raise ExecutionRetentionIntegrityError(
                        "Unexpected archive section."
                    )
                section_stream = archive.extractfile(member)
                if section_stream is None:
                    raise ExecutionRetentionIntegrityError(
                        "Missing archive section."
                    )
                sha = hashlib.sha256()
                actual_ids: List[UUID] = []
                with section_stream:
                    for line in section_stream:
                        sha.update(line)
                        record = parse_record(
                            line, RECORDS_BY_TABLE[section.table]
                        )
                        actual_ids.append(record.id)
                        records.append(record)
                if (
                    actual_ids != section.ids
                    or sha.hexdigest() != section.sha256
                ):
                    raise ExecutionRetentionIntegrityError(
                        "Section checksum or identity mismatch."
                    )
            if archive.next() is not None:
                raise ExecutionRetentionIntegrityError(
                    "Unexpected additional archive member."
                )
            # tarfile stops at the first zero block; subsequent padding must
            # also be zero, rather than a hidden second archive.
            with unpacked.open("rb") as tail:
                tail.seek(archive.offset)
                if any(tail.read()):
                    raise ExecutionRetentionIntegrityError(
                        "Unexpected trailing tar data."
                    )
        return records


def validate_closure(
    records: List[Record], *, project_id: UUID, root_run_id: UUID
) -> None:
    """Reject rows whose owners fall outside the authenticated execution unit.

    Args:
        records: Captured or fully verified records.
        project_id: Authorized project identity.
        root_run_id: Canonical execution root identity.
    """
    runs = {run.id: run for run in records if isinstance(run, RunRecord)}
    steps = {step.id for step in records if isinstance(step, StepRecord)}
    snapshots = {
        snapshot.id
        for snapshot in records
        if isinstance(snapshot, SnapshotRecord)
    }
    _validate_snapshot_references(records, snapshots)
    _validate_canonical_root(runs, root_run_id)
    for record in records:
        if isinstance(record, ConfigurationRecord):
            _validate_configuration_owner(record, snapshots, steps)
            continue
        _validate_project_owner(record, project_id)
        if isinstance(record, RunRecord):
            _validate_run_parent(record, runs, root_run_id)
        if isinstance(record, StepRecord):
            _validate_execution_parent(record, runs)


def _validate_snapshot_references(
    records: List[Record], snapshots: set[UUID]
) -> None:
    """Reject snapshot payloads unreferenced by the captured execution.

    Args:
        records: Verified record identities and ownership fields.
        snapshots: Snapshot identities stored in this bundle.

    Raises:
        ExecutionRetentionIntegrityError: A snapshot has no captured run or step owner.
    """
    referenced = {
        record.snapshot_id
        for record in records
        if isinstance(record, (RunRecord, StepRecord))
        and record.snapshot_id is not None
    }
    if not snapshots.issubset(referenced):
        raise ExecutionRetentionIntegrityError(
            "Snapshot is not referenced by the captured execution tree."
        )


def _validate_canonical_root(
    runs: Dict[UUID, RunRecord], root_id: UUID
) -> None:
    """Require the declared root to be a canonical captured run.

    Args:
        runs: Captured runs indexed by identity.
        root_id: Authenticated execution root identity.

    Raises:
        ExecutionRetentionIntegrityError: The root is missing or has a parent.
    """
    root = runs.get(root_id)
    if (
        root is None
        or root.parent_run_id is not None
        or root.root_run_id not in (None, root.id)
    ):
        raise ExecutionRetentionIntegrityError("Missing canonical root.")


def _validate_configuration_owner(
    record: ConfigurationRecord, snapshots: set[UUID], steps: set[UUID]
) -> None:
    """Require a configuration's owner to belong to this bundle.

    Args:
        record: Configuration with its validated single owner.
        snapshots: Captured snapshot identities.
        steps: Captured step identities.

    Raises:
        ExecutionRetentionIntegrityError: The owner is outside the bundle.
    """
    if (
        record.snapshot_id is not None
        and record.snapshot_id not in snapshots
        or record.step_run_id is not None
        and record.step_run_id not in steps
    ):
        raise ExecutionRetentionIntegrityError(
            "Configuration owner is outside the bundle."
        )


def _validate_run_parent(
    record: RunRecord, runs: Dict[UUID, RunRecord], root_id: UUID
) -> None:
    """Require each non-root run to name the root and a captured parent.

    Args:
        record: Run whose tree membership is being checked.
        runs: Captured runs indexed by identity.
        root_id: Validated canonical execution root.

    Raises:
        ExecutionRetentionIntegrityError: A non-root run belongs to another tree.
    """
    if record.id != root_id and (
        record.root_run_id != root_id or record.parent_run_id not in runs
    ):
        raise ExecutionRetentionIntegrityError(
            "Run is outside the execution tree."
        )


def _validate_execution_parent(
    record: StepRecord, runs: Dict[UUID, RunRecord]
) -> None:
    """Require a step to reference a captured pipeline run.

    Args:
        record: Step with a pipeline run owner.
        runs: Captured runs indexed by identity.

    Raises:
        ExecutionRetentionIntegrityError: The pipeline run owner is absent.
    """
    if record.pipeline_run_id not in runs:
        raise ExecutionRetentionIntegrityError("Missing parent run.")


def _validate_project_owner(
    record: RunRecord | StepRecord | SnapshotRecord,
    project_id: UUID,
) -> None:
    """Require each project-scoped record to match the authenticated project.

    Args:
        record: Execution record carrying its own project identity.
        project_id: Authorized project identity from the descriptor.

    Raises:
        ExecutionRetentionIntegrityError: The record belongs to another project.
    """
    if record.project_id != project_id:
        raise ExecutionRetentionIntegrityError("Cross-project record.")
