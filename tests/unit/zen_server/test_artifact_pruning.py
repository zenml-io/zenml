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
"""Tests for server-side artifact version pruning."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from zenml.artifacts.pruning import (
    ArtifactDataReference,
    ArtifactPruneBatch,
    ArtifactPruneCandidate,
    ArtifactPruneDatabaseChanges,
)
from zenml.client import Client
from zenml.enums import ArtifactSaveType, ArtifactType
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ArtifactVersionPruneRequest,
    ArtifactVersionPruneResponse,
    ArtifactVersionRequest,
)
from zenml.zen_server import artifact_pruning
from zenml.zen_server.artifact_pruning import ServerArtifactPruneHandler
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.routers import artifact_version_endpoints as endpoints


@contextmanager
def _server(store: MagicMock) -> Iterator[MagicMock]:
    """Patch the permission check, store and task submission.

    Args:
        store: The store the routes should use.

    Yields:
        The patched permission check.
    """
    with (
        patch.object(endpoints, "verify_permission") as verify,
        patch.object(endpoints, "zen_store", return_value=store),
        patch.object(
            endpoints, "submit_maintenance_task", return_value="task"
        ),
    ):
        yield verify


def _assert_store_called_with(
    store: MagicMock, prune_request: ArtifactVersionPruneRequest
) -> None:
    kwargs = store.prune_artifact_versions.call_args.kwargs
    assert kwargs["prune_request"] == prune_request
    assert isinstance(kwargs["handler"], ServerArtifactPruneHandler)


def test_prune_dry_run_only_counts() -> None:
    """A dry run counts synchronously and schedules nothing."""
    prune_request = ArtifactVersionPruneRequest(project=uuid4())
    store = MagicMock()
    store.prune_artifact_versions.return_value = ArtifactVersionPruneResponse(
        artifact_version_count=3
    )

    with _server(store) as verify:
        response = endpoints.prune_artifact_versions.__wrapped__(prune_request)
        endpoints.submit_maintenance_task.assert_not_called()

    verify.assert_called_once_with(
        resource_type=ResourceType.ARTIFACT_VERSION,
        action=Action.PRUNE,
        project_id=prune_request.project,
    )
    assert response == ArtifactVersionPruneResponse(artifact_version_count=3)
    _assert_store_called_with(store, prune_request)


def test_prune_apply_runs_in_the_background() -> None:
    """Applying defers the store call to a maintenance task."""
    prune_request = ArtifactVersionPruneRequest(project=uuid4(), apply=True)
    store = MagicMock()

    with _server(store):
        response = endpoints.prune_artifact_versions.__wrapped__(prune_request)
        store.prune_artifact_versions.assert_not_called()
        endpoints.submit_maintenance_task.assert_called_once()
        endpoints.submit_maintenance_task.call_args.args[0]()

    assert response == ArtifactVersionPruneResponse(task_id="task")
    _assert_store_called_with(store, prune_request)


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
    _assert_store_called_with(
        store,
        ArtifactVersionPruneRequest(
            project=project_id, only_versions=False, apply=True
        ),
    )


def test_handler_only_deletes_data_from_accessible_artifact_stores() -> None:
    """The caller's store and connector permissions decide what is deleted."""
    allowed_store, forbidden_store = uuid4(), uuid4()
    artifact_store = MagicMock()
    artifact_store.exists.return_value = True

    def _get_stack_component(component_id: UUID, hydrate: bool) -> MagicMock:
        component = MagicMock(id=component_id)
        component.connector.id = component_id
        return component

    def _verify_permission(model: Any, action: Action) -> None:
        if model.id == forbidden_store:
            raise IllegalOperationError("no")

    store = MagicMock()
    store.get_stack_component.side_effect = _get_stack_component
    candidates = [
        ArtifactPruneCandidate(
            artifact_version_id=uuid4(),
            data_reference=ArtifactDataReference(uri=uri, storage_id=store_id),
        )
        for uri, store_id in [
            ("forbidden", forbidden_store),
            ("allowed", allowed_store),
        ]
    ]

    with (
        patch.object(artifact_pruning, "zen_store", return_value=store),
        patch.object(
            artifact_pruning,
            "verify_permission_for_model",
            side_effect=_verify_permission,
        ) as verify,
        patch.object(
            artifact_pruning,
            "instantiate_artifact_store",
            return_value=artifact_store,
        ) as instantiate,
    ):
        prepared = ServerArtifactPruneHandler(
            ArtifactVersionPruneRequest(
                project=uuid4(), delete_from_artifact_store=True, apply=True
            )
        ).prepare_batch(ArtifactPruneBatch(candidates=tuple(candidates)))

    assert prepared.prepared_artifact_version_ids == {
        candidates[1].artifact_version_id
    }
    artifact_store.rmtree.assert_called_once_with("allowed")
    instantiate.assert_called_once()
    assert [c.kwargs["action"] for c in verify.call_args_list] == [
        Action.READ,
        Action.READ,
        Action.READ,
        Action.CLIENT,
    ]


def test_handler_deletes_rbac_resources_in_chunks() -> None:
    """Deleted versions and artifacts leave RBAC in small requests."""
    project_id = uuid4()
    version_ids = frozenset(uuid4() for _ in range(150))
    artifact_id = uuid4()
    handler = ServerArtifactPruneHandler(
        ArtifactVersionPruneRequest(project=project_id, apply=True)
    )

    with patch.object(artifact_pruning, "delete_resources") as delete:
        handler.database_changes_committed(
            ArtifactPruneDatabaseChanges(
                deleted_artifact_version_ids=version_ids,
                retained_artifact_version_ids=frozenset({uuid4()}),
                deleted_artifact_ids=frozenset({artifact_id}),
            )
        )

    requests = [c.args[0] for c in delete.call_args_list]
    assert [len(resources) for resources in requests] == [100, 51]
    resources = [resource for request in requests for resource in request]
    assert {r.project_id for r in resources} == {project_id}
    assert {r.id for r in resources if r.type == ResourceType.ARTIFACT} == {
        artifact_id
    }
    assert {
        r.id for r in resources if r.type == ResourceType.ARTIFACT_VERSION
    } == version_ids


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
def test_prune_deletes_data_and_metadata_batch_by_batch(
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
            patch.object(artifact_pruning, "verify_permission_for_model"),
            patch.object(artifact_pruning, "delete_resources"),
            patch.object(
                artifact_pruning,
                "zen_store",
                return_value=clean_client.zen_store,
            ),
        ):
            pruned = clean_client.zen_store.prune_artifact_versions(
                prune_request=prune_request,
                handler=ServerArtifactPruneHandler(prune_request),
                batch_size=2,
            ).artifact_version_count
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
