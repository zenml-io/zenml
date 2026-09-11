# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Canonical archives, frozen compatibility, and hostile tar boundaries."""

import gzip
import io
import json
import tarfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import DateTime, Uuid
from sqlmodel import SQLModel

from tests.unit.zen_stores.retention.fixture_graph import (
    insert_rows,
    read_tables,
)
from zenml.enums import (
    ArchiveBundleStatus,
    RetentionOutcome,
)
from zenml.exceptions import ExecutionRetentionIntegrityError
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores.retention.bundle import Bundle
from zenml.zen_stores.retention.manifest import (
    TABLE_ORDER,
    Manifest,
    canonical_json,
    sha256_hex,
)
from zenml.zen_stores.schemas import ArchiveBundleSchema


@pytest.fixture
def bundle(tmp_path):
    """Copy frozen bytes before hostile mutations; never regenerate during tests."""
    fixtures = Path(__file__).parent / "fixtures"
    payload = tmp_path / "rows.tar.gz"
    payload.write_bytes((fixtures / "v1-rows.tar.gz").read_bytes())
    return Bundle(
        manifest=Manifest.from_bytes(
            (fixtures / "v1-manifest.json").read_bytes()
        ),
        path=payload,
    )


@pytest.mark.parametrize(
    "hostile",
    [
        "traversal",
        "absolute",
        "symlink",
        "hardlink",
        "pax_headers",
        "duplicate",
        "trailing",
    ],
)
def test_hostile_tar_members_never_write_outside_scratch(
    bundle, tmp_path, hostile
):
    """Authenticated hostile tar shapes fail without extracting any member."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    sentinel = tmp_path / "outside.jsonl"
    sentinel.write_bytes(b"untouched")
    output = io.BytesIO()
    with (
        tarfile.open(bundle.path, "r:gz") as original,
        tarfile.open(
            fileobj=output, mode="w", format=tarfile.PAX_FORMAT
        ) as crafted,
    ):
        members = original.getmembers()
        if hostile == "duplicate":
            members.append(members[-1])
        for index, member in enumerate(members):
            content = original.extractfile(member).read()
            if index == 0:
                if hostile == "traversal":
                    member.name = "../outside.jsonl"
                elif hostile == "absolute":
                    member.name = str(sentinel)
                elif hostile in ("symlink", "hardlink"):
                    member.type = (
                        tarfile.SYMTYPE
                        if hostile == "symlink"
                        else tarfile.LNKTYPE
                    )
                    member.linkname = str(sentinel)
                    member.size = 0
                elif hostile == "pax_headers":
                    member.pax_headers = {"comment": "untrusted extension"}
            crafted.addfile(member, io.BytesIO(content))
    raw = output.getvalue()
    if hostile == "trailing":
        raw += b"hidden nonzero tail"
    payload = gzip.compress(raw, mtime=0)
    bundle.path.write_bytes(payload)
    manifest = bundle.manifest.model_copy(
        update=dict(
            object_bytes=len(payload), object_sha256=sha256_hex(payload)
        )
    )
    before = set(tmp_path.rglob("*"))
    with pytest.raises(ExecutionRetentionIntegrityError, match="archive|tar"):
        Bundle(manifest=manifest, path=bundle.path).records(scratch)
    assert set(tmp_path.rglob("*")) == before
    assert sentinel.read_bytes() == b"untouched"


def test_future_format_preserves_compatibility_message(
    bundle, tmp_path, storage
):
    """A downloaded newer format explains the compatible-server requirement."""
    fields = bundle.manifest.model_dump(mode="json")
    fields["format_version"] = 2
    payload = canonical_json(fields)
    uri = f"{storage.path}/future"
    storage.makedirs(uri)
    with storage.open(f"{uri}/manifest.json", "wb") as target:
        target.write(payload)
    with pytest.raises(
        ExecutionRetentionIntegrityError,
        match="Archive format 2 requires a compatible server; supported: 1",
    ):
        Bundle.download(
            storage, uri, sha256_hex(payload), tmp_path, lambda manifest: None
        )


def test_frozen_v1_restores_current_schema(retention_store, storage):
    """Restore the checked-in metadata-free V1 bytes into today's SQL schema."""
    fixtures = Path(__file__).parent / "fixtures"
    manifest_bytes = (fixtures / "v1-manifest.json").read_bytes()
    manifest = Manifest.from_bytes(manifest_bytes)
    fixture = json.loads((fixtures / "v1-sql.json").read_text())
    uri = f"{storage.path}/{manifest.bundle_id}"
    storage.makedirs(uri)
    for source, destination in (
        ("v1-manifest.json", "manifest.json"),
        ("v1-rows.tar.gz", "rows.tar.gz"),
    ):
        with storage.open(f"{uri}/{destination}", "wb") as target:
            target.write((fixtures / source).read_bytes())
    cold = deepcopy(fixture["before"])
    # Keep the frozen V1 clearing contract independent of today's writer metadata.
    cleared = {
        "pipeline_run": "orchestrator_environment exception_info pipeline_configuration client_environment",
        "pipeline_snapshot": "pipeline_configuration client_environment pipeline_spec source_code description",
        "step_run": "exception_info step_configuration",
    }
    cold["step_configuration"] = []
    for name, columns in cleared.items():
        for row in cold[name]:
            row.update({column: None for column in columns.split()})
            if name == "pipeline_snapshot":
                row.update(
                    pipeline_configuration="{}", client_environment="{}"
                )
            if "archive_bundle_id" in row:
                row["archive_bundle_id"] = str(manifest.bundle_id)
    cold["archive_bundle"] = [
        ArchiveBundleSchema(
            id=manifest.bundle_id,
            project_id=manifest.project_id,
            root_run_id=manifest.root_run_id,
            active_root_id=manifest.root_run_id,
            created=manifest.created_at,
            updated=manifest.created_at,
            uri=uri,
            size_bytes=manifest.object_bytes,
            manifest_hash=sha256_hex(
                canonical_json(manifest.model_dump(mode="json"))
            ),
            format_version=manifest.format_version,
            status=ArchiveBundleStatus.COMPLETE,
            claim_token=2,
        ).model_dump(mode="json")
    ]
    for name, rows in cold.items():
        for row in rows:
            for column, value in row.items():
                sql_type = SQLModel.metadata.tables[name].c[column].type
                if value is not None and isinstance(
                    sql_type, (Uuid, DateTime)
                ):
                    row[column] = (
                        UUID(value)
                        if isinstance(sql_type, Uuid)
                        else datetime.fromisoformat(value)
                    )
    insert_rows(retention_store, cold)
    restored = retention_store.restore_pipeline_run(manifest.root_run_id)
    assert restored.outcome == RetentionOutcome.SUCCEEDED
    actual = json.loads(
        json.dumps(read_tables(retention_store), default=pydantic_encoder)
    )
    for name in TABLE_ORDER:
        assert actual[name] == fixture["before"][name], name
