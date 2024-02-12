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
from zenml.models import BasePluginFlavorResponse
from zenml.models.v2.base.page import Page
from zenml.plugins.plugin_flavor_registry import plugin_flavor_registry
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
)

plugin_router = APIRouter(
    prefix=API + VERSION_1 + PLUGIN_FLAVORS,
    tags=["plugins"],
    responses={401: error_response, 403: error_response},
)


# -------------------- Plugin Flavors --------------------


@plugin_router.get(
    "",
    response_model=Page[BasePluginFlavorResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_flavors(
    _type: PluginType,
    sub_type: PluginSubType,
    page: int = PAGINATION_STARTING_PAGE,
    size: int = PAGE_SIZE_DEFAULT,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[BasePluginFlavorResponse]:
    """Returns all event flavors.

    Args:
        _type: The type of Plugin
        sub_type: The subtype of the plugin
        page: Page for pagination (offset +1)
        size: Page size for pagination
        hydrate: Whether to hydrate the response bodies

    Returns:
        A page of flavors.
    """
    flavors = plugin_flavor_registry.list_available_flavor_responses_for_type_and_subtype(
        _type=_type, sub_type=sub_type, page=page, size=size, hydrate=hydrate
    )
    return flavors


# -------------------- Flavors --------------------


@plugin_router.get(
    "/{flavor_name}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(
    flavor_name: str,
    plugin_type: PluginType = Query(..., alias="type"),
    plugin_subtype: PluginSubType = Query(..., alias="subtype"),
    _: AuthContext = Security(authorize),
) -> BasePluginFlavorResponse:
    """Returns the requested flavor.

    Args:
        flavor_name: Name of the flavor.
        plugin_type: Type of Plugin
        plugin_subtype: Subtype of Plugin

    Returns:
        The requested flavor response.
    """
    plugin_flavor = plugin_flavor_registry.get_flavor_class(
        flavor_name=flavor_name, _type=plugin_type, subtype=plugin_subtype
    )
    return plugin_flavor.get_flavor_response_model(hydrate=True)
