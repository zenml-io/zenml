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
"""Endpoint definitions for steps (and artifacts) of pipeline runs."""

from asyncio.log import logger
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, ARTIFACTS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import ArtifactRequestModel, ArtifactResponseModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + ARTIFACTS,
    tags=["artifacts"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[ArtifactResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_artifacts(
    project_name_or_id: Optional[Union[str, UUID]] = None,
    artifact_uri: Optional[str] = None,
    artifact_store_id: Optional[UUID] = None,
    only_unused: bool = False,
    parent_step_id: Optional[UUID] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[ArtifactResponseModel]:
    """Get artifacts according to query filters.

    Args:
        project_name_or_id: If specified, only artifacts from the given
            project will be returned.
        artifact_uri: If specified, only artifacts with the given URI will
            be returned.
        artifact_store_id: If specified, only artifacts from the given
            artifact store will be returned.
        only_unused: If True, only return artifacts that are not used in
            any runs.
        parent_step_id: Deprecated filter, will be ignored.

    Returns:
        The artifacts according to query filters.
    """
    if parent_step_id:
        logger.warning(
            "The ZenML server received a request to list artifacts with an "
            "outdated filter argument. If you see this message, please "
            "update your ZenML client to match the server version."
        )
    return zen_store().list_artifacts(
        project_name_or_id=project_name_or_id,
        artifact_uri=artifact_uri,
        artifact_store_id=artifact_store_id,
        only_unused=only_unused,
    )


@router.post(
    "",
    response_model=ArtifactResponseModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_artifact(
    artifact: ArtifactRequestModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ArtifactResponseModel:
    """Create a new artifact.

    Args:
        artifact: The artifact to create.

    Returns:
        The created artifact.
    """
    return zen_store().create_artifact(artifact)


@router.get(
    "/{artifact_id}",
    response_model=ArtifactResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_artifact(
    artifact_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ArtifactResponseModel:
    """Get an artifact by ID.

    Args:
        artifact_id: The ID of the artifact to get.

    Returns:
        The artifact with the given ID.
    """
    return zen_store().get_artifact(artifact_id)


@router.delete(
    "/{artifact_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_artifact(
    artifact_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Delete an artifact by ID.

    Args:
        artifact_id: The ID of the artifact to delete.
    """
    zen_store().delete_artifact(artifact_id)
