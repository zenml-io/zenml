#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

from typing import Any, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import API, RUN_METADATA, VERSION_1
from zenml.enums import MetadataResourceTypes
from zenml.models import RunMetadataRequest
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    verify_permission_for_model,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + RUN_METADATA,
    tags=["run_metadata"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + RUN_METADATA,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["run_metadata"],
)
@handle_exceptions
def create_run_metadata(
    run_metadata: RunMetadataRequest,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    auth_context: AuthContext = Security(authorize),
) -> None:
    """Creates run metadata.

    Args:
        run_metadata: The run metadata to create.
        project_name_or_id: Optional name or ID of the project.
        auth_context: Authentication context.

    Raises:
        RuntimeError: If the resource type is not supported.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        run_metadata.project = project.id

    run_metadata.user = auth_context.user.id

    verify_models: List[Any] = []
    for resource in run_metadata.resources:
        if resource.type == MetadataResourceTypes.PIPELINE_RUN:
            verify_models.append(zen_store().get_run(resource.id))
        elif resource.type == MetadataResourceTypes.STEP_RUN:
            verify_models.append(zen_store().get_run_step(resource.id))
        elif resource.type == MetadataResourceTypes.ARTIFACT_VERSION:
            verify_models.append(zen_store().get_artifact_version(resource.id))
        elif resource.type == MetadataResourceTypes.MODEL_VERSION:
            verify_models.append(zen_store().get_model_version(resource.id))
        elif resource.type == MetadataResourceTypes.SCHEDULE:
            verify_models.append(zen_store().get_schedule(resource.id))
        else:
            raise RuntimeError(f"Unknown resource type: {resource.type}")

    batch_verify_permissions_for_models(
        models=verify_models,
        action=Action.UPDATE,
    )

    verify_permission_for_model(model=run_metadata, action=Action.CREATE)

    zen_store().create_run_metadata(run_metadata)
