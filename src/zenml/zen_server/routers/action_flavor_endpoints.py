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
"""Endpoint definitions for action plans."""
from typing import List

from fastapi import APIRouter, Security

from zenml.actions.base_action_flavor import ActionFlavorResponse
from zenml.constants import ACTIONS, API, VERSION_1
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
)
from zenml.zen_server.utils import zen_store

router = APIRouter(
    prefix=API + VERSION_1 + ACTIONS,
    tags=["actions"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=List[ActionFlavorResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_action_flavors(
    _: AuthContext = Security(authorize),
) -> List[ActionFlavorResponse]:
    """Returns all action flavors.

    Returns:
        All flavors.
    """
    return zen_store().list_action_flavors()


@router.get(
    "/{flavor_name}",
    response_model=ActionFlavorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(
    flavor_name: str,
    _: AuthContext = Security(authorize),
) -> ActionFlavorResponse:
    """Returns the requested flavor.

    Args:
        flavor_name: Name of the flavor.

    Returns:
        The requested stack.
    """
    return zen_store().get_action_flavor(flavor_name=flavor_name)
