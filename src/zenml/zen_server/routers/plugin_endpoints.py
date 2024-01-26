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
from typing import List

from fastapi import APIRouter, Security

from zenml.constants import API, PLUGINS, VERSION_1
from zenml.enums import PluginType
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    plugin_flavor_registry,
)

plugin_router = APIRouter(
    prefix=API + VERSION_1 + PLUGINS,
    tags=["plugins"],
    responses={401: error_response, 403: error_response},
)


# -------------------- Plugin Flavors --------------------


@plugin_router.get(
    "",
    response_model=List[str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_plugin_flavors(
    _: AuthContext = Security(authorize),
) -> List[str]:
    """Returns all event flavors.

    Returns:
        All flavors.
    """
    return plugin_flavor_registry().available_flavors


# -------------------- Plugin Types --------------------


@plugin_router.get(
    "/flavor_name",
    response_model=List[str],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_plugin_types(
    flavor_name: str,
    _: AuthContext = Security(authorize),
) -> List[str]:
    """Returns all event flavors.

    Returns:
        All flavors.
    """
    return plugin_flavor_registry().available_types_for_flavor(
        flavor_name=flavor_name
    )


# -------------------- Flavors --------------------


@plugin_router.get(
    "/{flavor_name}/{plugin_type}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_flavor(
    flavor_name: str,
    plugin_type: PluginType,
    _: AuthContext = Security(authorize),
):
    """Returns the requested flavor.

    Args:
        flavor_name: Name of the flavor.
        plugin_type: Type of Plugin

    Returns:
        The requested stack.
    """
    # TODO: Figure out if typing of the response can be reintroduced
    return (
        plugin_flavor_registry()
        .get_flavor_class(name=flavor_name, _type=plugin_type)
        .get_plugin_flavor_response_model()
    )
