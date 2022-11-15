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

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, ARTIFACTS, VERSION_1
from zenml.enums import PermissionType
from zenml.models.pipeline_models import ArtifactModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + ARTIFACTS,
    tags=["artifacts"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[ArtifactModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_artifacts(
    artifact_uri: Optional[str] = None,
    parent_step_id: Optional[UUID] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[ArtifactModel]:
    """Get artifacts according to query filters.

    Args:
        artifact_uri: If specified, only artifacts with the given URI will
            be returned.
        parent_step_id: If specified, only artifacts for the given step run
            will be returned.

    Returns:
        The artifacts according to query filters.
    """
    return zen_store().list_artifacts(
        artifact_uri=artifact_uri,
        parent_step_id=parent_step_id,
    )


@router.post(
    "",
    response_model=ArtifactModel,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_artifact(
    artifact: ArtifactModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ArtifactModel:
    """Create a new artifact.

    Args:
        artifact: The artifact to create.

    Returns:
        The created artifact.
    """
    return zen_store().create_artifact(artifact)
