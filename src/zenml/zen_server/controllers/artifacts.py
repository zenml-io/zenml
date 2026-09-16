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
"""Server-side artifact operations that reach beyond the database."""

from typing import TYPE_CHECKING, List
from uuid import UUID

from zenml.artifacts import pruning
from zenml.artifacts.pruning import ArtifactDataDeleter
from zenml.artifacts.utils import instantiate_artifact_store
from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionFilter,
    ArtifactVersionPruneRequest,
    ArtifactVersionPruneResponse,
    ComponentResponse,
)
from zenml.zen_server.rbac.models import Action, Resource, ResourceType
from zenml.zen_server.rbac.utils import (
    delete_resources,
    verify_permission_for_model,
)
from zenml.zen_server.utils import submit_maintenance_task, zen_store

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore

logger = get_logger(__name__)


def prune_artifact_versions(
    prune_request: ArtifactVersionPruneRequest, in_background: bool = True
) -> ArtifactVersionPruneResponse:
    """Count or prune the artifact versions that nothing references.

    A dry run only counts and returns immediately. Pruning can take a long
    time, so it runs as a maintenance task and returns the task ID unless
    the caller needs the result within the request. Artifact data is
    deleted only from the artifact stores the caller may use, and versions
    whose data cannot be deleted are kept.

    Args:
        prune_request: Which artifact versions to prune and whether to
            delete them or only count them.
        in_background: Whether to prune in a maintenance task.

    Returns:
        The number of unused or pruned artifact versions, or the ID of the
        task pruning them.
    """
    if not prune_request.apply:
        return ArtifactVersionPruneResponse(
            artifact_version_count=zen_store().count_artifact_versions(
                ArtifactVersionFilter(
                    project=prune_request.project, only_unused=True
                )
            )
        )

    def _delete_rbac_resources(artifact_version_ids: List[UUID]) -> None:
        delete_resources(
            [
                Resource(
                    type=ResourceType.ARTIFACT_VERSION,
                    id=artifact_version_id,
                    project_id=prune_request.project,
                )
                for artifact_version_id in artifact_version_ids
            ]
        )

    def _prune() -> ArtifactVersionPruneResponse:
        logger.info(
            "Pruning unused artifact versions of project "
            f"{prune_request.project}."
        )
        return pruning.prune_artifact_versions(
            zen_store(),
            prune_request,
            artifact_data_deleter=ArtifactDataDeleter(
                load_accessible_artifact_store
            ),
            on_deleted=_delete_rbac_resources,
        )

    if not in_background:
        return _prune()
    return ArtifactVersionPruneResponse(
        task_id=submit_maintenance_task(_prune)
    )


def load_accessible_artifact_store(
    artifact_store_id: UUID,
) -> "BaseArtifactStore":
    """Load an artifact store after checking that the caller may use it.

    Args:
        artifact_store_id: The artifact store.

    Returns:
        The artifact store.
    """
    return instantiate_artifact_store(
        verify_artifact_store_access(artifact_store_id)
    )


def verify_artifact_store_access(
    artifact_store_id: UUID,
) -> ComponentResponse:
    """Verify that the caller may use an artifact store and its connector.

    Args:
        artifact_store_id: The artifact store.

    Returns:
        The artifact store component.
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
    return artifact_store_model
