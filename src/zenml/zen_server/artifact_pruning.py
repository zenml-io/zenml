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
"""Server side effects of artifact pruning outside the database."""

from typing import TYPE_CHECKING
from uuid import UUID

from zenml.artifacts.pruning import (
    ArtifactPruneDatabaseChanges,
    ArtifactStorePruneHandler,
)
from zenml.artifacts.utils import instantiate_artifact_store
from zenml.models import ArtifactVersionPruneRequest
from zenml.zen_server.rbac.models import Action, Resource, ResourceType
from zenml.zen_server.rbac.utils import (
    delete_resources,
    verify_permission_for_model,
)
from zenml.zen_server.utils import zen_store

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore

# Keeps every request to the RBAC service small, whatever the prune batch
# size.
RBAC_RESOURCE_BATCH_SIZE = 100


def load_accessible_artifact_store(
    artifact_store_id: UUID,
) -> "BaseArtifactStore":
    """Load an artifact store after checking that the caller may use it.

    Args:
        artifact_store_id: The artifact store.

    Returns:
        The artifact store.
    """
    artifact_store_model = zen_store().get_stack_component(
        artifact_store_id, hydrate=True
    )
    verify_permission_for_model(artifact_store_model, action=Action.READ)
    if artifact_store_model.connector:
        verify_permission_for_model(
            artifact_store_model.connector, action=Action.READ
        )
        verify_permission_for_model(
            artifact_store_model.connector, action=Action.CLIENT
        )
    return instantiate_artifact_store(artifact_store_model)


class ServerArtifactPruneHandler(ArtifactStorePruneHandler):
    """Prunes artifact data and RBAC resources on behalf of the caller.

    Artifact data is only deleted from the artifact stores the caller may
    use, so this must run with the caller's authentication context.
    """

    def __init__(self, prune_request: ArtifactVersionPruneRequest) -> None:
        """Initialize the handler.

        Args:
            prune_request: The prune request being handled.
        """
        super().__init__(
            delete_external_data=prune_request.delete_from_artifact_store,
            artifact_store_loader=load_accessible_artifact_store,
        )
        self._project_id = prune_request.project

    def database_changes_committed(
        self, changes: ArtifactPruneDatabaseChanges
    ) -> None:
        """Delete the RBAC resources of the deleted artifacts and versions.

        Args:
            changes: The committed database changes.
        """
        super().database_changes_committed(changes)
        resources = [
            Resource(
                type=ResourceType.ARTIFACT_VERSION,
                id=artifact_version_id,
                project_id=self._project_id,
            )
            for artifact_version_id in changes.deleted_artifact_version_ids
        ] + [
            Resource(
                type=ResourceType.ARTIFACT,
                id=artifact_id,
                project_id=self._project_id,
            )
            for artifact_id in changes.deleted_artifact_ids
        ]
        for start in range(0, len(resources), RBAC_RESOURCE_BATCH_SIZE):
            delete_resources(
                resources[start : start + RBAC_RESOURCE_BATCH_SIZE]
            )
