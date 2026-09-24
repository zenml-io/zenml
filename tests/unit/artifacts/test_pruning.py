#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for the artifact-store prune handler."""

from typing import Optional
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from zenml.artifacts.pruning import (
    ArtifactDataReference,
    ArtifactPruneBatch,
    ArtifactPruneCandidate,
    ArtifactPruneDatabaseChanges,
    ArtifactStorePruneHandler,
)


def _candidate(
    uri: str = "uri", storage_id: Optional[UUID] = None
) -> ArtifactPruneCandidate:
    return ArtifactPruneCandidate(
        artifact_version_id=uuid4(),
        data_reference=ArtifactDataReference(uri=uri, storage_id=storage_id),
    )


def test_handler_prepares_everything_without_data_deletion() -> None:
    """A metadata-only prune never touches an artifact store."""
    loader = MagicMock()
    batch = ArtifactPruneBatch(candidates=(_candidate(), _candidate()))

    prepared = ArtifactStorePruneHandler(
        delete_external_data=False, artifact_store_loader=loader
    ).prepare_batch(batch)

    assert prepared.prepared_artifact_version_ids == batch.artifact_version_ids
    loader.assert_not_called()


def test_handler_keeps_versions_whose_data_stays(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unloadable stores and failed deletions keep only their versions."""
    good_store_id, broken_store_id = uuid4(), uuid4()
    artifact_store = MagicMock()
    artifact_store.exists.side_effect = lambda uri: uri != "missing"

    def _rmtree(uri: str) -> None:
        if uri == "locked":
            raise OSError("denied")

    artifact_store.rmtree.side_effect = _rmtree

    def _load(storage_id: UUID) -> MagicMock:
        if storage_id == broken_store_id:
            raise RuntimeError("no credentials")
        return artifact_store

    loader = MagicMock(side_effect=_load)
    fine, missing, locked, unloadable, unloadable_again = (
        _candidate("fine", good_store_id),
        _candidate("missing", good_store_id),
        _candidate("locked", good_store_id),
        _candidate("elsewhere", broken_store_id),
        _candidate("elsewhere-again", broken_store_id),
    )
    batch = ArtifactPruneBatch(
        candidates=(fine, missing, locked, unloadable, unloadable_again)
    )

    prepared = ArtifactStorePruneHandler(
        delete_external_data=True, artifact_store_loader=loader
    ).prepare_batch(batch)

    assert prepared.prepared_artifact_version_ids == {
        fine.artifact_version_id,
        missing.artifact_version_id,
    }
    assert loader.call_count == 2
    assert "Deleting the data of 5 artifact version(s) took" in caplog.text
    assert "median" in caplog.text


@pytest.mark.parametrize("delete_external_data", [True, False])
def test_handler_reports_retained_versions_only_after_deleting_data(
    delete_external_data: bool, caplog: pytest.LogCaptureFixture
) -> None:
    """A kept version is only inconsistent if its data was deleted."""
    retained_id = uuid4()

    ArtifactStorePruneHandler(
        delete_external_data=delete_external_data,
        artifact_store_loader=MagicMock(),
    ).database_changes_committed(
        ArtifactPruneDatabaseChanges(
            retained_artifact_version_ids=frozenset({retained_id})
        )
    )

    assert (str(retained_id) in caplog.text) is delete_external_data
