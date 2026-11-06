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
"""Tests for the server's artifact prune handler."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from zenml.artifacts.pruning import (
    ArtifactDataReference,
    ArtifactPruneBatch,
    ArtifactPruneCandidate,
    ArtifactPruneDatabaseChanges,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import ArtifactVersionPruneRequest
from zenml.zen_server import artifact_pruning
from zenml.zen_server.artifact_pruning import ServerArtifactPruneHandler
from zenml.zen_server.rbac.models import Action, ResourceType


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


def test_handler_deletes_rbac_resources_of_committed_deletions_in_chunks() -> (
    None
):
    """Deleted versions and artifacts lose their RBAC records, 100 per call."""
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
                deleted_artifact_ids=frozenset({artifact_id}),
            )
        )

    sent = [r for call in delete.call_args_list for r in call.args[0]]
    assert [len(call.args[0]) for call in delete.call_args_list] == [100, 51]
    assert {(r.type, r.id) for r in sent} == {
        (ResourceType.ARTIFACT_VERSION, v) for v in version_ids
    } | {(ResourceType.ARTIFACT, artifact_id)}
    assert {r.project_id for r in sent} == {project_id}
