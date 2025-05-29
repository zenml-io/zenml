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
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from zenml.artifacts.utils import (
    load_artifact_visualization,
)
from zenml.constants import (
    API,
    ARTIFACT_VERSIONS,
    BATCH,
    DATA,
    DOWNLOAD_TOKEN,
    VERSION_1,
    VISUALIZE,
)
from zenml.models import (
    ArtifactVersionFilter,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionUpdate,
    LoadedVisualization,
    Page,
)
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
    generate_artifact_download_token,
    verify_artifact_download_token,
)
from zenml.zen_server.download_utils import (
    create_artifact_archive,
    verify_artifact_is_downloadable,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_batch_create_entity,
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
    async_fastapi_endpoint_wrapper,
    make_dependable,
    set_filter_project_scope,
    zen_store,
)

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
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def prune_artifact_versions(
    project_name_or_id: Union[str, UUID],
    only_versions: bool = True,
    _: AuthContext = Security(authorize),
) -> None:
    """Prunes unused artifact versions and their artifacts.

    Args:
        project_name_or_id: The project name or ID to prune artifact
            versions for.
        only_versions: Only delete artifact versions, keeping artifacts
    """
    project_id = zen_store().get_project(project_name_or_id).id

    verify_permissions_and_prune_entities(
        resource_type=ResourceType.ARTIFACT_VERSION,
        prune_method=zen_store().prune_artifact_versions,
        only_versions=only_versions,
        project_id=project_id,
    )


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
    """
    store = zen_store()
    artifact = verify_permissions_and_get_entity(
        id=artifact_version_id, get_method=store.get_artifact_version
    )
    return load_artifact_visualization(
        artifact=artifact, index=index, zen_store=store, encode_image=True
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
    """
    artifact = verify_permissions_and_get_entity(
        id=artifact_version_id, get_method=zen_store().get_artifact_version
    )
    verify_artifact_is_downloadable(artifact)

    # The artifact download is handled in a separate tab by the browser. In this
    # tab, we do not have the ability to set any headers and therefore cannot
    # include the CSRF token in the request. To handle this, we instead generate
    # a JWT token in this endpoint (which includes CSRF and RBAC checks) and
    # then use that token to download the artifact data in a separate endpoint
    # which only verifies this short-lived token.
    return generate_artifact_download_token(artifact_version_id)


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
    verify_artifact_download_token(token, artifact_version_id)

    artifact = zen_store().get_artifact_version(artifact_version_id)
    archive_path = create_artifact_archive(artifact)

    return FileResponse(
        archive_path,
        media_type="application/gzip",
        filename=f"{artifact.name}-{artifact.version}.tar.gz",
        background=BackgroundTask(os.remove, archive_path),
    )
