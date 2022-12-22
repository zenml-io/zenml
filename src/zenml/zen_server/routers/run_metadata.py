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
"""Endpoint definitions for run metadata."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, RUN_METADATA, VERSION_1
from zenml.enums import PermissionType
from zenml.models import RunMetadataResponseModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + RUN_METADATA,
    tags=["run_metadata"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[RunMetadataResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_run_metadata(
    project_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    pipeline_run_id: Optional[UUID] = None,
    step_run_id: Optional[UUID] = None,
    artifact_id: Optional[UUID] = None,
    stack_component_id: Optional[UUID] = None,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> List[RunMetadataResponseModel]:
    """Get run metadata according to query filters.

    Args:
        project_id: ID of the project to filter by.
        user_id: ID of the user to filter by.
        pipeline_run_id: ID of the pipeline run to filter by.
        step_run_id: ID of the step run to filter by.
        artifact_id: ID of the artifact to filter by.
        stack_component_id: ID of the stack component to filter by.

    Returns:
        The pipeline runs according to query filters.
    """
    return zen_store().list_run_metadata(
        project_id=project_id,
        user_id=user_id,
        pipeline_run_id=pipeline_run_id,
        step_run_id=step_run_id,
        artifact_id=artifact_id,
        stack_component_id=stack_component_id,
    )
