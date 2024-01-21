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
"""Endpoint definitions for event flavors."""


from fastapi import APIRouter, Security

from zenml.constants import API, EVENTS, VERSION_1
from zenml.events import event_flavor_registry
from zenml.events.base_event_flavor import EventFlavorResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
)

router = APIRouter(
    prefix=API + VERSION_1 + EVENTS,
    tags=["events"],
    responses={401: error_response, 403: error_response},
)


# @router.get(
#     "",
#     response_model=Page[FlavorResponse],
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# @handle_exceptions
# def list_action_flavors(
#     flavor_filter_model: FlavorFilter = Depends(make_dependable(FlavorFilter)),
#     hydrate: bool = False,
#     _: AuthContext = Security(authorize),
# ) -> Page[FlavorResponse]:
#     """Returns all flavors.
#
#     Args:
#         flavor_filter_model: Filter model used for pagination, sorting,
#                              filtering
#         hydrate: Flag deciding whether to hydrate the output model(s)
#             by including metadata fields in the response.
#
#     Returns:
#         All flavors.
#     """
#     return verify_permissions_and_list_entities(
#         filter_model=flavor_filter_model,
#         resource_type=ResourceType.FLAVOR,
#         list_method=zen_store().list_flavors,
#         hydrate=hydrate,
#     )

# TODO: Change response to a pydantic Model
@router.get(
    "/{flavor_name}",
    response_model=EventFlavorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(
    flavor_name: str,
    _: AuthContext = Security(authorize),
) -> EventFlavorResponse:
    """Returns the requested flavor.

    Args:
        flavor_name: Name of the flavor.

    Returns:
        The requested stack.
    """
    try:
        return event_flavor_registry.get_event_flavor(flavor_name)().to_model()
    except KeyError:
        raise KeyError("No event flavor by that name exists.")
        # TODO: Implement this properly
