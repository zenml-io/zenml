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

from typing import Dict, List, Optional, Type

from zenml.logger import get_logger
from zenml.models import ServiceConnectorBaseModel
from zenml.service_connectors.service_connector import ServiceConnector

logger = get_logger(__name__)


class ServiceConnectorRegistry:
    """Service connector registry."""

    def __init__(self) -> None:
        """Initialize the service connector registry."""
        self.service_connectors: Dict[str, Type[ServiceConnector]] = {}
        self.register_builtin_service_connectors()

    def register_service_connector(
        self,
        service_connector: Type[ServiceConnector],
        overwrite: bool = False,
    ) -> None:
        """Registers a new service connector.

        Args:
            service_connector: Service connector.
            overwrite: Whether to overwrite an existing service connector.
        """
        spec = service_connector.get_specification()
        if spec.type not in self.service_connectors or overwrite:
            self.service_connectors[spec.type] = service_connector
            logger.debug(
                f"Registered service connector with type {spec.type}."
            )
        else:
            logger.debug(
                f"Found existing service connector for type "
                f"{spec.type}: Skipping registration."
            )

    def get_service_connector(
        self,
        connector_type: str,
    ) -> Type[ServiceConnector]:
        """Get a service connector by its connector type identifier.

        Args:
            connector_type: The service connector type identifier.

        Returns:
            A service connector that was registered for the given
            connector type identifier.
        """
        return self.service_connectors[connector_type]

    def __getitem__(self, key: str) -> Type[ServiceConnector]:
        """Get a service connector by its connector type identifier.

        Args:
            key: The service connector type identifier.

        Returns:
            A service connector that was registered for the given service
            connector type identifier.

        Raises:
            KeyError: If no service connector was registered for the given type
                identifier.
        """
        return self.get_service_connector(key)

    def get_service_connectors(
        self,
    ) -> Dict[str, Type[ServiceConnector]]:
        """Get all registered service connectors.

        Returns:
            A dictionary of registered service connector types.
        """
        return self.service_connectors.copy()

    def is_registered(self, connector_type: str) -> bool:
        """Returns if a service connector is registered for the given type identifier.

        Args:
            connector_type: The service connector type identifier.

        Returns:
            True if a service connector is registered for the given type
            identifier, False otherwise.
        """
        return connector_type in self.service_connectors

    def find_service_connector(
        self,
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> List[Type[ServiceConnector]]:
        """Find one or more service connectors that match the given criteria.

        Args:
            connector_type: Filter by service connector type identifier.
            resource_type: Filter by a resource type that the connector can
                be used to give access to.
            auth_method: Filter by an authentication method that the connector
                uses to authenticate with the resource provider.

        Returns:
            A list of service connector types that match the given criteria.
        """
        matches: List[Type[ServiceConnector]] = []
        for service_connector in self.service_connectors.values():
            spec = service_connector.get_specification()
            if (
                (connector_type is None or connector_type == spec.type)
                and (
                    resource_type is None
                    or resource_type in spec.resource_type_map
                )
                and (
                    auth_method is None or auth_method in spec.auth_method_map
                )
            ):
                matches.append(service_connector)

        return matches

    def instantiate_service_connector(
        self,
        model: ServiceConnectorBaseModel,
    ) -> ServiceConnector:
        """Validate a service connector model and create an instance from it.

        Args:
            model: The service connector model to validate and instantiate.

        Returns:
            A service connector instance.

        Raises:
            NotImplementedError: If no service connector is registered for the
                given type identifier.
        """
        try:
            service_connector = self.get_service_connector(model.type)
        except KeyError:
            raise NotImplementedError(
                f"Service connector type {model.type} is not available. "
                f"Please make sure the corresponding packages and/or ZenML "
                f"integration are installed and try again."
            )

        try:
            return service_connector.from_model(model)
        except ValueError as e:
            raise ValueError(
                f"The service connector configuration is not valid: {e}"
            )

    @property
    def builtin_connectors(self) -> List[Type[ServiceConnector]]:
        """A list of all default in-built importable connectors.

        Returns:
            A list of builtin importable connectors.
        """
        builtin_connectors: List[Type[ServiceConnector]] = []
        try:
            from zenml.service_connectors.aws_service_connector import (
                AWSServiceConnector,
            )

            builtin_connectors.append(AWSServiceConnector)
        except ImportError as e:
            logger.warning(f"Could not import AWS service connector: {e}.")

        return builtin_connectors

    def register_builtin_service_connectors(self) -> None:
        """Registers the default built-in service connectors."""
        for connector in self.builtin_connectors:
            self.register_service_connector(connector, overwrite=True)


service_connector_registry = ServiceConnectorRegistry()
