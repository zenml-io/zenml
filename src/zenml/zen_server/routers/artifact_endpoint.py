#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Endpoint definitions for artifacts."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, ARTIFACTS, VERSION_1
from zenml.models import (
    ArtifactFilter,
    ArtifactRequest,
    ArtifactResponse,
    ArtifactUpdate,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

artifact_router = APIRouter(
    prefix=API + VERSION_1 + ARTIFACTS,
    tags=["artifacts"],
    responses={401: error_response, 403: error_response},
)


@artifact_router.get(
    "",
    response_model=Page[ArtifactResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_artifacts(
    artifact_filter_model: ArtifactFilter = Depends(
        make_dependable(ArtifactFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ArtifactResponse]:
    """Get artifacts according to query filters.

    Args:
        artifact_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The artifacts according to query filters.
    """
    return verify_permissions_and_list_entities(
        filter_model=artifact_filter_model,
        resource_type=ResourceType.ARTIFACT,
        list_method=zen_store().list_artifacts,
        hydrate=hydrate,
    )


@artifact_router.post(
    "",
    response_model=ArtifactResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_artifact(
    artifact: ArtifactRequest,
    _: AuthContext = Security(authorize),
) -> ArtifactResponse:
    """Create a new artifact.

    Args:
        artifact: The artifact to create.

    Returns:
        The created artifact.
    """
    return verify_permissions_and_create_entity(
        request_model=artifact,
        resource_type=ResourceType.ARTIFACT,
        create_method=zen_store().create_artifact,
    )


@artifact_router.get(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_artifact(
    artifact_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ArtifactResponse:
    """Get an artifact by ID.

    Args:
        artifact_id: The ID of the artifact to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The artifact with the given ID.
    """
    return verify_permissions_and_get_entity(
        id=artifact_id,
        get_method=zen_store().get_artifact,
        hydrate=hydrate,
    )


@artifact_router.put(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_artifact(
    artifact_id: UUID,
    artifact_update: ArtifactUpdate,
    _: AuthContext = Security(authorize),
) -> ArtifactResponse:
    """Update an artifact by ID.

    Args:
        artifact_id: The ID of the artifact to update.
        artifact_update: The update to apply to the artifact.

    Returns:
        The updated artifact.
    """
    return verify_permissions_and_update_entity(
        id=artifact_id,
        update_model=artifact_update,
        get_method=zen_store().get_artifact,
        update_method=zen_store().update_artifact,
    )


@artifact_router.delete(
    "/{artifact_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_artifact(
    artifact_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete an artifact by ID.

    Args:
        artifact_id: The ID of the artifact to delete.
    """
    verify_permissions_and_delete_entity(
        id=artifact_id,
        get_method=zen_store().get_artifact,
        delete_method=zen_store().delete_artifact,
    )
