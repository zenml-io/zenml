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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for the artifact version pruning endpoint."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List
from unittest.mock import MagicMock, call, patch
from uuid import UUID, uuid4

import pytest

from zenml.client import Client
from zenml.enums import ArtifactSaveType, ArtifactType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ArtifactVersionPruneRequest,
    ArtifactVersionPruneResponse,
    ArtifactVersionRequest,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.routers import artifact_version_endpoints as endpoints
from zenml.zen_stores.sql_zen_store import ArtifactVersionLocation


@contextmanager
def _server(store: MagicMock) -> Iterator[MagicMock]:
    """Patch the permission check, store and task submission.

    Args:
        store: The store the endpoint should use.

    Yields:
        The patched permission check.
    """
    with (
        patch.object(endpoints, "verify_permission") as verify,
        patch.object(endpoints, "zen_store", return_value=store),
        patch.object(endpoints, "set_auth_context"),
        patch.object(
            endpoints, "submit_maintenance_task", return_value="task"
        ),
    ):
        yield verify


def _prune(
    prune_request: ArtifactVersionPruneRequest,
) -> ArtifactVersionPruneResponse:
    """Call the prune endpoint without the FastAPI wrapper."""
    return endpoints.prune_artifact_versions.__wrapped__(
        prune_request, auth_context=MagicMock()
    )


def test_prune_dry_run_only_counts() -> None:
    """A dry run counts synchronously and schedules nothing."""
    prune_request = ArtifactVersionPruneRequest(project=uuid4())
    store = MagicMock()
    store.prune_artifact_versions.return_value = ArtifactVersionPruneResponse(
        artifact_version_count=3
    )

    with _server(store) as verify:
        response = _prune(prune_request)
        endpoints.submit_maintenance_task.assert_not_called()

    verify.assert_called_once_with(
        resource_type=ResourceType.ARTIFACT_VERSION,
        action=Action.PRUNE,
        project_id=prune_request.project,
    )
    assert response == ArtifactVersionPruneResponse(artifact_version_count=3)
    store.prune_artifact_versions.assert_called_once_with(prune_request)


def test_prune_apply_runs_in_the_background() -> None:
    """Applying defers the pruning to a maintenance task."""
    prune_request = ArtifactVersionPruneRequest(project=uuid4(), apply=True)
    store = MagicMock()

    with (
        _server(store),
        patch.object(
            endpoints, "_prune_unused_artifact_versions", return_value=2
        ) as prune,
    ):
        response = _prune(prune_request)
        prune.assert_not_called()
        endpoints.submit_maintenance_task.assert_called_once()
        endpoints.submit_maintenance_task.call_args.args[0]()
        endpoints.set_auth_context.assert_called_once()

    assert response == ArtifactVersionPruneResponse(task_id="task")
    prune.assert_called_once_with(prune_request)


def test_legacy_prune_route_prunes_synchronously() -> None:
    """The deprecated delete route prunes metadata for older clients."""
    project_id = uuid4()
    store = MagicMock()
    store.get_project.return_value.id = project_id

    with _server(store) as verify:
        endpoints.prune_artifact_versions_legacy.__wrapped__(
            "my-project", only_versions=False
        )
        endpoints.submit_maintenance_task.assert_not_called()

    verify.assert_called_once_with(
        resource_type=ResourceType.ARTIFACT_VERSION,
        action=Action.PRUNE,
        project_id=project_id,
    )
    store.prune_artifact_versions.assert_called_once_with(
        ArtifactVersionPruneRequest(
            project=project_id, only_versions=False, apply=True
        )
    )


def _location(uri: str, artifact_store_id: UUID) -> ArtifactVersionLocation:
    return ArtifactVersionLocation(
        id=uuid4(), uri=uri, artifact_store_id=artifact_store_id
    )


def test_prune_loop_keeps_versions_it_cannot_delete_data_for(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Versions in forbidden stores or with undeletable data are kept."""
    prune_request = ArtifactVersionPruneRequest(
        project=uuid4(),
        only_versions=False,
        delete_from_artifact_store=True,
        apply=True,
    )
    allowed_store, forbidden_store = uuid4(), uuid4()
    forbidden = _location("forbidden", forbidden_store)
    broken = _location("broken", allowed_store)
    fine = _location("fine", allowed_store)
    raced = _location("raced", allowed_store)
    store = MagicMock()
    store.list_unused_artifact_version_locations.side_effect = [
        [forbidden, broken],
        [fine, raced],
        [],
    ]
    # The raced version was referenced after its data went; the store keeps
    # it.
    store.delete_unused_artifact_versions.return_value = [fine.id]

    def _verify_access(artifact_store_id: UUID) -> None:
        if artifact_store_id == forbidden_store:
            raise IllegalOperationError("no")

    artifact_store = MagicMock()
    artifact_store.exists.return_value = True

    def _rmtree(uri: str) -> None:
        if uri == "broken":
            raise RuntimeError("denied")

    artifact_store.rmtree.side_effect = _rmtree

    with (
        patch.object(endpoints, "zen_store", return_value=store),
        patch.object(
            endpoints, "_verify_artifact_store_access", _verify_access
        ),
        patch.object(
            endpoints, "load_artifact_store", return_value=artifact_store
        ),
        patch.object(endpoints, "delete_resources") as delete_resources,
    ):
        pruned = endpoints._prune_unused_artifact_versions(prune_request)

    assert pruned == 1
    assert artifact_store.rmtree.call_args_list == [
        call("broken"),
        call("fine"),
        call("raced"),
    ]
    store.delete_unused_artifact_versions.assert_called_once_with(
        [fine.id, raced.id]
    )
    assert [r.id for r in delete_resources.call_args.args[0]] == [fine.id]
    assert str(raced.id) in caplog.text and "data is gone" in caplog.text
    store.prune_artifacts_without_versions.assert_called_once_with(
        prune_request.project
    )
    # Each batch resumes after the last listed version, so a kept version
    # is never attempted again.
    assert [
        c.kwargs["after"]
        for c in store.list_unused_artifact_version_locations.call_args_list
    ] == [None, broken.id, raced.id]


def _create_artifact_version(client: Client, uri: str) -> UUID:
    return client.zen_store.create_artifact_version(
        ArtifactVersionRequest(
            artifact_name=f"artifact-{uuid4().hex[:8]}",
            project=client.active_project.id,
            version="1",
            type=ArtifactType.DATA,
            uri=uri,
            materializer="zenml.materializers.BuiltInMaterializer",
            data_type="builtins.str",
            save_type=ArtifactSaveType.MANUAL,
            artifact_store_id=client.active_stack.artifact_store.id,
        )
    ).id


@pytest.mark.parametrize("delete_metadata", [True, False])
def test_prune_loop_deletes_data_and_metadata_batch_by_batch(
    clean_client: Client, delete_metadata: bool
) -> None:
    """Against a real store: data goes, metadata follows unless kept."""
    root = Path(clean_client.active_stack.artifact_store.path) / "prune"
    version_ids: List[UUID] = []
    for index in range(5):
        path = root / str(index)
        path.mkdir(parents=True)
        (path / "data").write_text("payload")
        version_ids.append(_create_artifact_version(clean_client, str(path)))
    locked = root / "0"
    os.chmod(locked, stat.S_IRUSR | stat.S_IXUSR)
    prune_request = ArtifactVersionPruneRequest(
        project=clean_client.active_project.id,
        only_versions=False,
        delete_metadata=delete_metadata,
        delete_from_artifact_store=True,
        apply=True,
    )

    try:
        with (
            patch.object(
                endpoints, "zen_store", return_value=clean_client.zen_store
            ),
            patch.object(endpoints, "PRUNE_BATCH_SIZE", 2),
        ):
            pruned = endpoints._prune_unused_artifact_versions(prune_request)
    finally:
        os.chmod(locked, stat.S_IRWXU)

    assert pruned == 4
    assert sorted(os.listdir(root)) == ["0"]
    remaining = clean_client.list_artifact_versions(
        only_unused=True, size=10
    ).items
    if delete_metadata:
        assert [v.id for v in remaining] == [version_ids[0]]
        assert clean_client.list_artifacts(size=10).total == 1
    else:
        assert {v.id for v in remaining} == set(version_ids)
