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
"""Implementation of a registry to track ZenML integrations."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from zenml.exceptions import IntegrationError
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.integrations.integration import Integration

logger = get_logger(__name__)


class IntegrationRegistry(object):
    """Registry to keep track of ZenML Integrations."""

    def __init__(self) -> None:
        """Initializing the integration registry."""
        self._integrations: Dict[str, Type["Integration"]] = {}

    @property
    def integrations(self) -> Dict[str, Type["Integration"]]:
        """Method to get integrations dictionary.

        Returns:
            A dict of integration key to type of `Integration`.
        """
        return self._integrations

    @integrations.setter
    def integrations(self, i: Any) -> None:
        """Setter method for the integrations property.

        Args:
            i: Value to set the integrations property to.

        Raises:
            IntegrationError: If you try to manually set the integrations property.
        """
        raise IntegrationError(
            "Please do not manually change the integrations within the "
            "registry. If you would like to register a new integration "
            "manually, please use "
            "`integration_registry.register_integration()`."
        )

    def register_integration(
        self, key: str, type_: Type["Integration"]
    ) -> None:
        """Method to register an integration with a given name.

        Args:
            key: Name of the integration.
            type_: Type of the integration.
        """
        self._integrations[key] = type_

    def activate_integrations(self) -> None:
        """Method to activate the integrations with are registered in the registry."""
        for name, integration in self._integrations.items():
            if integration.check_installation():
                integration.activate()
                logger.debug(f"Integration `{name}` is activated.")
            else:
                logger.debug(f"Integration `{name}` could not be activated.")

    @property
    def list_integration_names(self) -> List[str]:
        """Get a list of all possible integrations.

        Returns:
            A list of all possible integrations.
        """
        return [name for name in self._integrations]

    def select_integration_requirements(
        self, integration_name: Optional[str] = None
    ) -> List[str]:
        """Select the requirements for a given integration or all integrations.

        Args:
            integration_name: Name of the integration to check.

        Returns:
            List of requirements for the integration.

        Raises:
            KeyError: If the integration is not found.
        """
        if integration_name:
            if integration_name in self.list_integration_names:
                return self._integrations[integration_name].REQUIREMENTS
            else:
                raise KeyError(
                    f"Version {integration_name} does not exist. "
                    f"Currently the following integrations are implemented. "
                    f"{self.list_integration_names}"
                )
        else:
            return [
                requirement
                for name in self.list_integration_names
                for requirement in self._integrations[name].REQUIREMENTS
            ]

    def is_installed(self, integration_name: Optional[str] = None) -> bool:
        """Checks if all requirements for an integration are installed.

        Args:
            integration_name: Name of the integration to check.

        Returns:
            True if all requirements are installed, False otherwise.

        Raises:
            KeyError: If the integration is not found.
        """
        if integration_name in self.list_integration_names:
            return self._integrations[integration_name].check_installation()
        elif not integration_name:
            all_installed = [
                self._integrations[item].check_installation()
                for item in self.list_integration_names
            ]
            return all(all_installed)
        else:
            raise KeyError(
                f"Integration '{integration_name}' not found. "
                f"Currently the following integrations are available: "
                f"{self.list_integration_names}"
            )

    def get_installed_integrations(self) -> List[str]:
        """Returns list of installed integrations.

        Returns:
            List of installed integrations.
        """
        return [
            name
            for name, integration in integration_registry.integrations.items()
            if integration.check_installation()
        ]


integration_registry = IntegrationRegistry()
