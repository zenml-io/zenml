#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Endpoint definitions for artifact versions."""

import os
from typing import TYPE_CHECKING, List, Optional, Sequence, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from zenml.artifacts.utils import (
    ArtifactDataDeleter,
    instantiate_artifact_store,
    load_artifact_visualization,
)
from zenml.constants import (
    API,
    ARTIFACT_VERSIONS,
    BATCH,
    DATA,
    DOWNLOAD_TOKEN,
    PRUNE,
    VERSION_1,
    VISUALIZE,
)
from zenml.enums import DownloadType
from zenml.exceptions import IllegalOperationError
from zenml.logger import get_logger
from zenml.models import (
    ArtifactVersionFilter,
    ArtifactVersionPruneRequest,
    ArtifactVersionPruneResponse,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionUpdate,
    ComponentResponse,
    LoadedVisualization,
    Page,
)
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
    generate_download_token,
    verify_download_token,
)
from zenml.zen_server.download_utils import (
    create_artifact_archive,
    verify_artifact_is_downloadable,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_batch_create_entity,
    verify_permissions_and_create_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, Resource, ResourceType
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    dehydrate_page,
    delete_model_resource,
    delete_resources,
    get_allowed_resource_ids,
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    set_auth_context,
    set_filter_project_scope,
    submit_maintenance_task,
    zen_store,
)

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore

logger = get_logger(__name__)

artifact_version_router = APIRouter(
    prefix=API + VERSION_1 + ARTIFACT_VERSIONS,
    tags=["artifact_versions"],
    responses={401: error_response, 403: error_response},
)


@artifact_version_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_artifact_versions(
    artifact_version_filter_model: ArtifactVersionFilter = Depends(
        make_dependable(ArtifactVersionFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[ArtifactVersionResponse]:
    """Get artifact versions according to query filters.

    Args:
        artifact_version_filter_model: Filter model used for pagination,
            sorting, filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: The authentication context.

    Returns:
        The artifact versions according to query filters.
    """
    # A project scoped request must always be scoped to a specific
    # project. This is required for the RBAC check to work.
    set_filter_project_scope(artifact_version_filter_model)
    assert isinstance(artifact_version_filter_model.project, UUID)

    allowed_artifact_ids = get_allowed_resource_ids(
        resource_type=ResourceType.ARTIFACT,
        project_id=artifact_version_filter_model.project,
    )
    artifact_version_filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id,
        artifact_id=allowed_artifact_ids,
    )
    artifact_versions = zen_store().list_artifact_versions(
        artifact_version_filter_model=artifact_version_filter_model,
        hydrate=hydrate,
    )
    return dehydrate_page(artifact_versions)


@artifact_version_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_artifact_version(
    artifact_version: ArtifactVersionRequest,
    _: AuthContext = Security(authorize),
) -> ArtifactVersionResponse:
    """Create a new artifact version.

    Args:
        artifact_version: The artifact version to create.

    Returns:
        The created artifact version.
    """
    return verify_permissions_and_create_entity(
        request_model=artifact_version,
        create_method=zen_store().create_artifact_version,
    )


@artifact_version_router.post(
    BATCH,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def batch_create_artifact_version(
    artifact_versions: List[ArtifactVersionRequest],
    _: AuthContext = Security(authorize),
) -> List[ArtifactVersionResponse]:
    """Create a batch of artifact versions.

    Args:
        artifact_versions: The artifact versions to create.

    Returns:
        The created artifact versions.
    """
    return verify_permissions_and_batch_create_entity(
        batch=artifact_versions,
        create_method=zen_store().batch_create_artifact_versions,
    )


@artifact_version_router.get(
    "/{artifact_version_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_artifact_version(
    artifact_version_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ArtifactVersionResponse:
    """Get an artifact version by ID.

    Args:
        artifact_version_id: The ID of the artifact version to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The artifact version with the given ID.
    """
    return verify_permissions_and_get_entity(
        id=artifact_version_id,
        get_method=zen_store().get_artifact_version,
        hydrate=hydrate,
    )


@artifact_version_router.put(
    "/{artifact_version_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def update_artifact_version(
    artifact_version_id: UUID,
    artifact_version_update: ArtifactVersionUpdate,
    _: AuthContext = Security(authorize),
) -> ArtifactVersionResponse:
    """Update an artifact by ID.

    Args:
        artifact_version_id: The ID of the artifact version to update.
        artifact_version_update: The update to apply to the artifact version.

    Returns:
        The updated artifact.
    """
    return verify_permissions_and_update_entity(
        id=artifact_version_id,
        update_model=artifact_version_update,
        get_method=zen_store().get_artifact_version,
        update_method=zen_store().update_artifact_version,
    )


@artifact_version_router.delete(
    "/{artifact_version_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_artifact_version(
    artifact_version_id: UUID,
    delete_metadata: bool = True,
    delete_from_artifact_store: bool = False,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete an artifact version by ID.

    Args:
        artifact_version_id: The ID of the artifact version to delete.
        delete_metadata: Whether to delete the artifact version metadata.
        delete_from_artifact_store: Whether to also delete the artifact data.

    Raises:
        RuntimeError: If the artifact data cannot be deleted from the artifact
            store.
        ValueError: On metadata deletion of used versions, on data deletion of versions without artifact store.
    """
    artifact_version = zen_store().get_artifact_version(
        artifact_version_id, hydrate=True
    )

    verify_permission_for_model(artifact_version, action=Action.DELETE)

    if delete_metadata:
        unused_versions = zen_store().list_artifact_versions(
            ArtifactVersionFilter(
                id=artifact_version.id,
                project=artifact_version.project_id,
                only_unused=True,
                size=1,
            )
        )
        if not unused_versions.items:
            raise ValueError(
                "The metadata of artifact versions that are still referenced "
                "by runs or model versions cannot be deleted. Please remove "
                "all references to this artifact version first."
            )

    if delete_from_artifact_store:
        if not artifact_version.artifact_store_id:
            raise ValueError(
                "Artifact version has no artifact store, cannot delete data."
            )

        artifact_store = instantiate_artifact_store(
            _verify_artifact_store_access(artifact_version.artifact_store_id)
        )
        try:
            if artifact_store.exists(artifact_version.uri):
                artifact_store.rmtree(artifact_version.uri)
        except Exception as e:
            raise RuntimeError(
                f"Artifact data at '{artifact_version.uri}' could not be "
                f"deleted. Delete the data manually from the artifact store. "
                f"Full error: {e}"
            ) from e

    if delete_metadata:
        zen_store().delete_artifact_version(artifact_version.id)
        delete_model_resource(artifact_version)


@artifact_version_router.post(
    PRUNE,
    responses={401: error_response, 422: error_response, 429: error_response},
)
@async_fastapi_endpoint_wrapper
def prune_artifact_versions(
    prune_request: ArtifactVersionPruneRequest,
    auth_context: AuthContext = Security(authorize),
) -> ArtifactVersionPruneResponse:
    """Counts or deletes artifact versions that nothing references.

    Pruning can take a long time, so it runs as a maintenance task and the
    request only returns the task ID. Artifact data is deleted only from the
    artifact stores the caller may use, and versions whose data cannot be
    deleted are kept.

    Args:
        prune_request: Which artifact versions to prune and whether to
            delete them or only count them.
        auth_context: Authentication context.

    Returns:
        The number of unused artifact versions for a dry run, or the ID of
        the task pruning them.
    """
    verify_permission(
        resource_type=ResourceType.ARTIFACT_VERSION,
        action=Action.PRUNE,
        project_id=prune_request.project,
    )

    if not prune_request.apply:
        return zen_store().prune_artifact_versions(prune_request)

    def _delete_artifact_version_resources(
        artifact_version_ids: List[UUID],
    ) -> None:
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

    def _prune() -> None:
        # The task thread serves no request, so the caller's context is
        # restored for the artifact store permission checks.
        set_auth_context(auth_context)
        logger.info(
            f"Pruning unused artifact versions of project "
            f"{prune_request.project} on behalf of user "
            f"{auth_context.user.id}."
        )
        result = zen_store().prune_artifact_versions(
            prune_request,
            delete_artifact_data=ArtifactDataDeleter(
                _load_usable_artifact_store
            ),
            on_deleted=_delete_artifact_version_resources,
        )
        logger.info(
            f"Pruned {result.artifact_version_count} artifact version(s)."
        )

    return ArtifactVersionPruneResponse(
        task_id=submit_maintenance_task(_prune)
    )


@artifact_version_router.delete(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
    deprecated=True,
)
@async_fastapi_endpoint_wrapper
def prune_artifact_versions_legacy(
    project_name_or_id: Union[str, UUID],
    only_versions: bool = True,
    _: AuthContext = Security(authorize),
) -> None:
    """Prunes unused artifact versions synchronously.

    Kept for clients older than the `prune` route, which delete artifact
    data themselves before calling it.

    Args:
        project_name_or_id: The project name or ID to prune artifact
            versions for.
        only_versions: Only delete artifact versions, keeping artifacts.
    """
    project_id = zen_store().get_project(project_name_or_id).id
    verify_permission(
        resource_type=ResourceType.ARTIFACT_VERSION,
        action=Action.PRUNE,
        project_id=project_id,
    )
    zen_store().prune_artifact_versions(
        ArtifactVersionPruneRequest(
            project=project_id, only_versions=only_versions, apply=True
        )
    )


def _load_usable_artifact_store(
    artifact_store_id: UUID,
) -> Optional["BaseArtifactStore"]:
    """Load an artifact store if it exists and the caller may use it.

    Args:
        artifact_store_id: The artifact store.

    Returns:
        The artifact store, or None if the caller cannot use it.
    """
    try:
        return instantiate_artifact_store(
            _verify_artifact_store_access(artifact_store_id)
        )
    except (KeyError, IllegalOperationError) as e:
        logger.warning(
            f"Keeping the artifact versions stored in artifact store "
            f"{artifact_store_id}: {e}"
        )
        return None


def _verify_artifact_store_access(
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


@artifact_version_router.get(
    "/{artifact_version_id}" + VISUALIZE,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_artifact_visualization(
    artifact_version_id: UUID,
    index: int = 0,
    _: AuthContext = Security(authorize),
) -> LoadedVisualization:
    """Get the visualization of an artifact.

    Args:
        artifact_version_id: ID of the artifact version for which to get the visualization.
        index: Index of the visualization to get (if there are multiple).

    Returns:
        The visualization of the artifact version.

    Raises:
        KeyError: If the artifact version has no artifact store.
    """
    store = zen_store()
    artifact_version = store.get_artifact_version(artifact_version_id)

    if artifact_version.artifact_store_id:
        artifact_store = store.get_stack_component(
            artifact_version.artifact_store_id
        )
    else:
        raise KeyError(
            f"Artifact version {artifact_version_id} has no artifact store"
        )
    models: Sequence[BaseModel] = [artifact_version, artifact_store]
    batch_verify_permissions_for_models(models=models, action=Action.READ)

    return load_artifact_visualization(
        artifact=artifact_version,
        index=index,
        zen_store=store,
        encode_image=True,
    )


@artifact_version_router.get(
    "/{artifact_version_id}" + DOWNLOAD_TOKEN,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def get_artifact_download_token(
    artifact_version_id: UUID,
    _: AuthContext = Security(authorize),
) -> str:
    """Get a download token for the artifact data.

    Args:
        artifact_version_id: ID of the artifact version for which to get the data.

    Returns:
        The download token for the artifact data.

    Raises:
        KeyError: If the artifact version has no artifact store.
    """
    store = zen_store()
    artifact_version = store.get_artifact_version(artifact_version_id)

    if artifact_version.artifact_store_id:
        artifact_store = store.get_stack_component(
            artifact_version.artifact_store_id
        )
    else:
        raise KeyError(
            f"Artifact version {artifact_version_id} has no artifact store"
        )

    models: Sequence[BaseModel] = [artifact_version, artifact_store]
    batch_verify_permissions_for_models(models=models, action=Action.READ)

    verify_artifact_is_downloadable(artifact_version)

    # The artifact download is handled in a separate tab by the browser. In this
    # tab, we do not have the ability to set any headers and therefore cannot
    # include the CSRF token in the request. To handle this, we instead generate
    # a JWT token in this endpoint (which includes CSRF and RBAC checks) and
    # then use that token to download the artifact data in a separate endpoint
    # which only verifies this short-lived token.
    return generate_download_token(
        download_type=DownloadType.ARTIFACT_VERSION,
        resource_id=artifact_version_id,
    )


@artifact_version_router.get(
    "/{artifact_version_id}" + DATA,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def download_artifact_data(
    artifact_version_id: UUID, token: str
) -> FileResponse:
    """Download the artifact data.

    Args:
        artifact_version_id: ID of the artifact version for which to get the data.
        token: The token to authenticate the artifact download.

    Returns:
        The artifact data.
    """
    verify_download_token(
        token=token,
        download_type=DownloadType.ARTIFACT_VERSION,
        resource_id=artifact_version_id,
    )

    artifact_version = zen_store().get_artifact_version(artifact_version_id)

    archive_path = create_artifact_archive(artifact_version)
    return FileResponse(
        archive_path,
        media_type="application/gzip",
        filename=f"{artifact_version.name}-{artifact_version.version}.tar.gz",
        background=BackgroundTask(os.remove, archive_path),
    )
