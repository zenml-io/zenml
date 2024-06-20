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

from fastapi import APIRouter, Security

from zenml.assistant.base_assistant import BaseAssistantHandler
from zenml.constants import (
    API,
    AGENT,
    VERSION_1,
)
from zenml.enums import PluginType
from zenml.models.v2.core.assistant import AssistantRequest, AssistantResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_make_call,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    plugin_flavor_registry,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

try:
    from zenml_cloud_plugins.plugins.base_agent import BaseAgentHandler
except ImportError as e:
    logger.error(e)
    pass

assistant_router = APIRouter(
    prefix=API + VERSION_1 + AGENT,
    tags=["AI"],
    responses={401: error_response, 403: error_response},
)


@assistant_router.post(
    "",
    response_model=AssistantResponse,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def make_assistant_call(
    user_request: AssistantRequest,
    _: AuthContext = Security(authorize),
) -> AssistantResponse:
    """Makes call to the assistant.

    Args:
        user_request: Request to Assistant

    Returns:
        The created assistant.

    Raises:
        ValueError: If the plugin for the assistant is not valid.
    """
    agent_handler = plugin_flavor_registry().get_plugin(
        name=user_request.flavor,
        _type=PluginType.AGENT,
        subtype=user_request.plugin_subtype,
    )

    # Validate that the flavor and plugin_type correspond to an event source
    # implementation
    if not isinstance(agent_handler, BaseAgentHandler):
        raise ValueError(
            f"Assistant plugin {user_request.plugin_subtype} "
            f"for flavor {user_request.flavor} is not a valid assistant "
            "handler implementation."
        )

    return verify_permissions_and_make_call(
        request_model=user_request,
        destination_method=agent_handler.make_assistant_call,
    )
