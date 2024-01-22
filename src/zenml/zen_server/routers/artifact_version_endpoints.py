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

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.artifacts.utils import load_artifact_visualization
from zenml.constants import API, ARTIFACT_VERSIONS, VERSION_1, VISUALIZE
from zenml.models import (
    ArtifactVersionFilter,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionUpdate,
    LoadedVisualization,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_prune_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_page,
    get_allowed_resource_ids,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

artifact_version_router = APIRouter(
    prefix=API + VERSION_1 + ARTIFACT_VERSIONS,
    tags=["artifact_versions"],
    responses={401: error_response, 403: error_response},
)


@artifact_version_router.get(
    "",
    response_model=Page[ArtifactVersionResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
    allowed_artifact_ids = get_allowed_resource_ids(
        resource_type=ResourceType.ARTIFACT
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
    response_model=ArtifactVersionResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
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
        resource_type=ResourceType.ARTIFACT_VERSION,
        create_method=zen_store().create_artifact_version,
    )


@artifact_version_router.get(
    "/{artifact_version_id}",
    response_model=ArtifactVersionResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
    response_model=ArtifactVersionResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
@handle_exceptions
def delete_artifact_version(
    artifact_version_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete an artifact version by ID.

    Args:
        artifact_version_id: The ID of the artifact version to delete.
    """
    verify_permissions_and_delete_entity(
        id=artifact_version_id,
        get_method=zen_store().get_artifact_version,
        delete_method=zen_store().delete_artifact_version,
    )


@artifact_version_router.delete(
    "/",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def prune_artifact_versions(
    only_versions: bool = True,
    _: AuthContext = Security(authorize),
) -> None:
    """Prunes unused artifact versions and their artifacts.

    Args:
        only_versions: Only delete artifact versions, keeping artifacts
    """
    verify_permissions_and_prune_entities(
        resource_type=ResourceType.ARTIFACT_VERSION,
        prune_method=zen_store().prune_artifact_versions,
        only_versions=only_versions,
    )


@artifact_version_router.get(
    "/{artifact_version_id}" + VISUALIZE,
    response_model=LoadedVisualization,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
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
    """
    store = zen_store()
    artifact = verify_permissions_and_get_entity(
        id=artifact_version_id, get_method=store.get_artifact_version
    )
    return load_artifact_visualization(
        artifact=artifact, index=index, zen_store=store, encode_image=True
    )
