#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utility functions for the integrations module."""

import importlib
import inspect
import sys

from zenml.integrations.integration import Integration, IntegrationMeta


def get_integration_for_module(
    module_name: str,
) -> type[Integration] | None:
    """Gets the integration class for a module inside an integration.

    If the module given by `module_name` is not part of a ZenML integration,
    this method will return `None`. If it is part of a ZenML integration,
    it will return the integration class found inside the integration
    __init__ file.

    Args:
        module_name: The name of the module to get the integration for.

    Returns:
        The integration class for the module.
    """
    integration_prefix = "zenml.integrations."
    if not module_name.startswith(integration_prefix):
        return None

    integration_module_name = ".".join(module_name.split(".", 3)[:3])
    try:
        integration_module = sys.modules[integration_module_name]
    except KeyError:
        integration_module = importlib.import_module(integration_module_name)

    for _, member in inspect.getmembers(integration_module):
        if (
            member is not Integration
            and isinstance(member, IntegrationMeta)
            and issubclass(member, Integration)
        ):
            return member

    return None


def get_requirements_for_module(module_name: str) -> list[str]:
    """Gets requirements for a module inside an integration.

    If the module given by `module_name` is not part of a ZenML integration,
    this method will return an empty list. If it is part of a ZenML integration,
    it will return the list of requirements specified inside the integration
    class found inside the integration __init__ file.

    Args:
        module_name: The name of the module to get requirements for.

    Returns:
        A list of requirements for the module.
    """
    integration = get_integration_for_module(module_name)
    return integration.get_requirements() if integration else []
