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
"""Endpoint definitions for roles and role assignment."""
from typing import List

from fastapi import APIRouter, Security

from zenml.constants import API, VERSION_1, PERMISSIONS
from zenml.models import RoleModel
from zenml.models.user_management_models import PermissionModel
from zenml.zen_server.auth import authorize

from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + PERMISSIONS,
    tags=["permissions"],
    dependencies=[Security(authorize, scopes=["read"])],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[PermissionModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_permissions() -> List[RoleModel]:
    """Returns a list of all roles.

    Returns:
        List of all roles.
    """
    return zen_store().list_permissions()
