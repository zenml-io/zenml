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
"""Endpoint definitions for builds."""
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, PIPELINE_BUILDS, VERSION_1
from zenml.enums import PermissionType
from zenml.models import PipelineBuildFilterModel, PipelineBuildResponseModel
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + PIPELINE_BUILDS,
    tags=["builds"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[PipelineBuildResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_builds(
    build_filter_model: PipelineBuildFilterModel = Depends(
        make_dependable(PipelineBuildFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[PipelineBuildResponseModel]:
    """Gets a list of builds.

    Args:
        build_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        List of build objects.
    """
    return zen_store().list_builds(build_filter_model=build_filter_model)


@router.get(
    "/{build_id}",
    response_model=PipelineBuildResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_build(
    build_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> PipelineBuildResponseModel:
    """Gets a specific build using its unique id.

    Args:
        build_id: ID of the build to get.

    Returns:
        A specific build object.
    """
    return zen_store().get_build(build_id=build_id)


@router.delete(
    "/{build_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_build(
    build_id: UUID,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a specific build.

    Args:
        build_id: ID of the build to delete.
    """
    zen_store().delete_build(build_id=build_id)
