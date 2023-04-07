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
"""Implementation of a service connector registry."""

from typing import TYPE_CHECKING, Any, Dict, Type

from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.service_connectors.service_connector import ServiceConnector


class ServiceConnectorRegistry:
    """Service connector registry."""

    def __init__(self) -> None:
        """Initialize the service connector registry."""
        self.service_connector_types: Dict[str, Type["ServiceConnector"]] = {}

    def register_service_connector_type(
        self,
        connector_type: str,
        type_: Type["ServiceConnector"],
        overwrite: bool = False,
    ) -> None:
        """Registers a new service connector.

        Args:
            connector_type: Service connector type identifier.
            type_: A ServiceConnector subclass.
            overwrite: Whether to overwrite an existing connector.
        """
        if connector_type not in self.service_connector_types or overwrite:
            self.service_connector_types[connector_type] = type_
            logger.debug(
                f"Registered service connector {type_} for {connector_type}"
            )
        else:
            logger.debug(
                f"Found existing materializer class for {connector_type}: "
                f"{self.service_connector_types[connector_type]}. Skipping "
                f"registration of {type_}."
            )

    def get_service_connector_type(
        self,
        connector_type: str,
    ) -> Type["ServiceConnector"]:
        """Get a service connector class by its type identifier.

        Args:
            connector_type: The service connector type identifier.

        Returns:
            A `ServiceConnector` subclass that was registered for the given
            type identifier.
        """
        return self.service_connector_types[connector_type]

    def __getitem__(self, key: str) -> Type["ServiceConnector"]:
        """Get a service connector class by its type identifier.

        Args:
            key: The service connector type identifier.

        Returns:
            A `ServiceConnector` subclass that was registered for the given
            type identifier.

        Raises:
            KeyError: If no service connector was registered for the given
                type identifier.
        """
        return self.get_service_connector_type(key)

    def get_service_connector_types(
        self,
    ) -> Dict[str, Type["ServiceConnector"]]:
        """Get all registered service connector types.

        Returns:
            A dictionary of registered service connector types.
        """
        return self.service_connector_types.copy()

    def is_registered(self, connector_type: str) -> bool:
        """Returns if a service connector is registered for the given type.

        Args:
            connector_type: The service connector type identifier.

        Returns:
            True if a service connector is registered for the given type,
            False otherwise.
        """
        return connector_type in self.service_connector_types


service_connector_registry = ServiceConnectorRegistry()
