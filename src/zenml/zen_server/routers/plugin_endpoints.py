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
"""Endpoint definitions for plugin flavors."""

from fastapi import APIRouter, Query, Security

from zenml.constants import (
    API,
    PAGE_SIZE_DEFAULT,
    PAGINATION_STARTING_PAGE,
    PLUGIN_FLAVORS,
    VERSION_1,
)
from zenml.enums import PluginSubType, PluginType
from zenml.models.v2.base.base_plugin_flavor import (
    BasePluginFlavorResponse,
)
from zenml.models.v2.base.page import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    plugin_flavor_registry,
)

plugin_router = APIRouter(
    prefix=API + VERSION_1 + PLUGIN_FLAVORS,
    tags=["plugins"],
    responses={401: error_response, 403: error_response},
)


# -------------------- Plugin Flavors --------------------


@plugin_router.get(
    "",
    response_model=Page[BasePluginFlavorResponse],  # type: ignore[type-arg]
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_flavors(
    type: PluginType,
    subtype: PluginSubType,
    page: int = PAGINATION_STARTING_PAGE,
    size: int = PAGE_SIZE_DEFAULT,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[BasePluginFlavorResponse]:  # type: ignore[type-arg]
    """Returns all event flavors.

    Args:
        type: The type of Plugin
        subtype: The subtype of the plugin
        page: Page for pagination (offset +1)
        size: Page size for pagination
        hydrate: Whether to hydrate the response bodies

    Returns:
        A page of flavors.
    """
    flavors = plugin_flavor_registry().list_available_flavor_responses_for_type_and_subtype(
        _type=type, subtype=subtype, page=page, size=size, hydrate=hydrate
    )
    return flavors


# -------------------- Flavors --------------------


@plugin_router.get(
    "/{name}",
    response_model=BasePluginFlavorResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(
    name: str,
    type: PluginType = Query(..., alias="type"),
    subtype: PluginSubType = Query(..., alias="subtype"),
    _: AuthContext = Security(authorize),
) -> BasePluginFlavorResponse:  # type: ignore[type-arg]
    """Returns the requested flavor.

    Args:
        name: Name of the flavor.
        type: Type of Plugin
        subtype: Subtype of Plugin

    Returns:
        The requested flavor response.
    """
    plugin_flavor = plugin_flavor_registry().get_flavor_class(
        name=name, _type=type, subtype=subtype
    )
    return plugin_flavor.get_flavor_response_model(hydrate=True)
