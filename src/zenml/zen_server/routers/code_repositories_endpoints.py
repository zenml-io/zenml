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
"""Endpoint definitions for code repositories."""
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, CODE_REPOSITORIES, VERSION_1
from zenml.models import (
    CodeRepositoryFilter,
    CodeRepositoryResponse,
    CodeRepositoryUpdate,
    Page,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
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

router = APIRouter(
    prefix=API + VERSION_1 + CODE_REPOSITORIES,
    tags=["code_repositories"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[CodeRepositoryResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_code_repositories(
    filter_model: CodeRepositoryFilter = Depends(
        make_dependable(CodeRepositoryFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[CodeRepositoryResponse]:
    """Gets a page of code repositories.

    Args:
        filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page of code repository objects.
    """
    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.CODE_REPOSITORY,
        list_method=zen_store().list_code_repositories,
        hydrate=hydrate,
    )


@router.get(
    "/{code_repository_id}",
    response_model=CodeRepositoryResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_code_repository(
    code_repository_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> CodeRepositoryResponse:
    """Gets a specific code repository using its unique ID.

    Args:
        code_repository_id: The ID of the code repository to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        A specific code repository object.
    """
    return verify_permissions_and_get_entity(
        id=code_repository_id,
        get_method=zen_store().get_code_repository,
        hydrate=hydrate,
    )


@router.put(
    "/{code_repository_id}",
    response_model=CodeRepositoryResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_code_repository(
    code_repository_id: UUID,
    update: CodeRepositoryUpdate,
    _: AuthContext = Security(authorize),
) -> CodeRepositoryResponse:
    """Updates a code repository.

    Args:
        code_repository_id: The ID of the code repository to update.
        update: The model containing the attributes to update.

    Returns:
        The updated code repository object.
    """
    return verify_permissions_and_update_entity(
        id=code_repository_id,
        update_model=update,
        get_method=zen_store().get_code_repository,
        update_method=zen_store().update_code_repository,
    )


@router.delete(
    "/{code_repository_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_code_repository(
    code_repository_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a specific code repository.

    Args:
        code_repository_id: The ID of the code repository to delete.
    """
    verify_permissions_and_delete_entity(
        id=code_repository_id,
        get_method=zen_store().get_code_repository,
        delete_method=zen_store().delete_code_repository,
    )
