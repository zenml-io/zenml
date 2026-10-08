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
"""Tests for the pipeline snapshot endpoints."""

from contextlib import contextmanager
from datetime import timedelta
from typing import Iterator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.models import (
    PipelineSnapshotPruneRequest,
    PipelineSnapshotPruneResponse,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.routers import pipeline_snapshot_endpoints


@pytest.mark.parametrize("renaming_itself", [False, True])
def test_replace_requires_delete_on_displaced_snapshot(
    renaming_itself: bool,
) -> None:
    """Replacing a name needs DELETE on the snapshot that currently holds it."""
    existing = MagicMock(id=uuid4())
    store = MagicMock()
    store.list_snapshots.return_value.items = [existing]

    with (
        patch.object(
            pipeline_snapshot_endpoints,
            "server_config",
            return_value=MagicMock(rbac_enabled=True),
        ),
        patch.object(
            pipeline_snapshot_endpoints, "zen_store", return_value=store
        ),
        patch.object(
            pipeline_snapshot_endpoints, "verify_permission_for_model"
        ) as verify,
    ):
        pipeline_snapshot_endpoints.verify_replace_permission(
            project_id=uuid4(),
            pipeline_id=uuid4(),
            name="shared",
            exclude_snapshot_id=existing.id if renaming_itself else None,
        )

    if renaming_itself:
        verify.assert_not_called()
    else:
        verify.assert_called_once_with(existing, action=Action.DELETE)


@pytest.fixture
def prune_request() -> PipelineSnapshotPruneRequest:
    """A prune request for a random project."""
    return PipelineSnapshotPruneRequest(
        project=uuid4(), older_than=utc_now() - timedelta(days=30)
    )


@contextmanager
def _prune_server(store: MagicMock) -> Iterator[MagicMock]:
    """Patch the permission check, store and task submission of the endpoint.

    Args:
        store: The store the endpoint should use.

    Yields:
        The patched permission check.
    """
    with (
        patch.object(
            pipeline_snapshot_endpoints, "verify_permission"
        ) as verify,
        patch.object(
            pipeline_snapshot_endpoints, "zen_store", return_value=store
        ),
        patch.object(
            pipeline_snapshot_endpoints,
            "submit_maintenance_task",
            return_value="task",
        ),
    ):
        yield verify


def _prune(
    prune_request: PipelineSnapshotPruneRequest,
) -> PipelineSnapshotPruneResponse:
    """Call the prune endpoint without the FastAPI wrapper."""
    return pipeline_snapshot_endpoints.prune_pipeline_snapshots.__wrapped__(
        prune_request, auth_context=MagicMock()
    )


def test_prune_dry_run_only_counts(
    prune_request: PipelineSnapshotPruneRequest,
) -> None:
    """A dry run counts synchronously and schedules nothing."""
    store = MagicMock()
    store.prune_snapshots.return_value = PipelineSnapshotPruneResponse(
        snapshot_count=3
    )

    with _prune_server(store) as verify:
        response = _prune(prune_request)

    verify.assert_called_once_with(
        resource_type=ResourceType.PIPELINE_SNAPSHOT,
        action=Action.PRUNE,
        project_id=prune_request.project,
    )
    assert response == PipelineSnapshotPruneResponse(snapshot_count=3)
    store.prune_snapshots.assert_called_once_with(prune_request)


def test_prune_apply_runs_deletion_in_the_background(
    prune_request: PipelineSnapshotPruneRequest,
) -> None:
    """Applying defers the deletion to a maintenance task."""
    prune_request = prune_request.model_copy(update={"apply": True})
    store = MagicMock()
    store.prune_snapshots.return_value = PipelineSnapshotPruneResponse(
        snapshot_count=3
    )

    with _prune_server(store):
        response = _prune(prune_request)
        store.prune_snapshots.assert_not_called()

        submit = pipeline_snapshot_endpoints.submit_maintenance_task
        assert isinstance(submit, MagicMock)
        submit.assert_called_once()
        submit.call_args.args[0]()

    assert response == PipelineSnapshotPruneResponse(task_id="task")
    store.prune_snapshots.assert_called_once_with(prune_request)
