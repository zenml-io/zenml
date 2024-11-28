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

import threading
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from zenml.logger import get_logger
from zenml.models import ServiceConnectorTypeModel

if TYPE_CHECKING:
    from zenml.models import (
        ServiceConnectorRequest,
        ServiceConnectorResponse,
    )
    from zenml.service_connectors.service_connector import ServiceConnector
logger = get_logger(__name__)


class ServiceConnectorRegistry:
    """Service connector registry."""

    def __init__(self) -> None:
        """Initialize the service connector registry."""
        self.service_connector_types: Dict[str, ServiceConnectorTypeModel] = {}
        self.initialized = False
        self.lock = threading.RLock()

    def register_service_connector_type(
        self,
        service_connector_type: ServiceConnectorTypeModel,
        overwrite: bool = False,
    ) -> None:
        """Registers a service connector type.

        Args:
            service_connector_type: Service connector type.
            overwrite: Whether to overwrite an existing service connector type.
        """
        with self.lock:
            if (
                service_connector_type.connector_type
                not in self.service_connector_types
                or overwrite
            ):
                self.service_connector_types[
                    service_connector_type.connector_type
                ] = service_connector_type
                logger.debug(
                    "Registered service connector type "
                    f"{service_connector_type.connector_type}."
                )
            else:
                logger.debug(
                    f"Found existing service connector for type "
                    f"{service_connector_type.connector_type}: Skipping "
                    "registration."
                )

    def get_service_connector_type(
        self,
        connector_type: str,
    ) -> ServiceConnectorTypeModel:
        """Get a service connector type by its connector type identifier.

        Args:
            connector_type: The service connector type identifier.

        Returns:
            A service connector type that was registered for the given
            connector type identifier.

        Raises:
            KeyError: If no service connector was registered for the given type
                identifier.
        """
        self.register_builtin_service_connectors()

        if connector_type not in self.service_connector_types:
            raise KeyError(
                f"Service connector type {connector_type} is not available. "
                f"Please make sure the corresponding packages and/or ZenML "
                f"integration are installed and try again."
            )
        return self.service_connector_types[connector_type].model_copy()

    def __getitem__(self, key: str) -> ServiceConnectorTypeModel:
        """Get a service connector type by its connector type identifier.

        Args:
            key: The service connector type identifier.

        Returns:
            A service connector that was registered for the given service
            connector type identifier.
        """
        return self.get_service_connector_type(key)

    def is_registered(self, connector_type: str) -> bool:
        """Returns if a service connector is registered for the given type identifier.

        Args:
            connector_type: The service connector type identifier.

        Returns:
            True if a service connector is registered for the given type
            identifier, False otherwise.
        """
        self.register_builtin_service_connectors()
        return connector_type in self.service_connector_types

    def list_service_connector_types(
        self,
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> List[ServiceConnectorTypeModel]:
        """Find one or more service connector types that match the given criteria.

        Args:
            connector_type: Filter by service connector type identifier.
            resource_type: Filter by a resource type that the connector can
                be used to give access to.
            auth_method: Filter by an authentication method that the connector
                uses to authenticate with the resource provider.

        Returns:
            A list of service connector type models that match the given
            criteria.
        """
        self.register_builtin_service_connectors()

        matches: List[ServiceConnectorTypeModel] = []
        for service_connector_type in self.service_connector_types.values():
            if (
                (
                    connector_type is None
                    or connector_type == service_connector_type.connector_type
                )
                and (
                    resource_type is None
                    or resource_type
                    in service_connector_type.resource_type_dict
                )
                and (
                    auth_method is None
                    or auth_method in service_connector_type.auth_method_dict
                )
            ):
                matches.append(service_connector_type.model_copy())

        return matches

    def instantiate_connector(
        self,
        model: Union[
            "ServiceConnectorRequest",
            "ServiceConnectorResponse",
        ],
    ) -> "ServiceConnector":
        """Validate a service connector model and create an instance from it.

        Args:
            model: The service connector model to validate and instantiate.

        Returns:
            A service connector instance.

        Raises:
            NotImplementedError: If no service connector is registered for the
                given type identifier.
            ValueError: If the service connector model is not valid.
        """
        try:
            service_connector_type = self.get_service_connector_type(
                model.type
            )
        except KeyError:
            raise NotImplementedError(
                f"Service connector type {model.type} is not available "
                "locally. Please make sure the corresponding packages and/or "
                "ZenML integration are installed and try again."
            )

        assert service_connector_type.connector_class is not None

        try:
            return service_connector_type.connector_class.from_model(model)
        except ValueError as e:
            raise ValueError(
                f"The service connector configuration is not valid: {e}"
            )

    def register_builtin_service_connectors(self) -> None:
        """Registers the default built-in service connectors."""
        # Only register built-in service connectors once
        with self.lock:
            if self.initialized:
                return

            self.initialized = True

            try:
                from zenml.integrations.aws.service_connectors.aws_service_connector import (  # noqa
                    AWSServiceConnector,
                )
            except ImportError as e:
                logger.warning(f"Could not import AWS service connector: {e}.")

            try:
                from zenml.integrations.gcp.service_connectors.gcp_service_connector import (  # noqa
                    GCPServiceConnector,
                )
            except ImportError as e:
                logger.warning(f"Could not import GCP service connector: {e}.")

            try:
                from zenml.integrations.azure.service_connectors.azure_service_connector import (  # noqa
                    AzureServiceConnector,
                )
            except ImportError as e:
                logger.warning(
                    f"Could not import Azure service connector: {e}."
                )

            try:
                from zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector import (  # noqa
                    KubernetesServiceConnector,
                )
            except ImportError as e:
                logger.warning(
                    f"Could not import Kubernetes service connector: {e}."
                )

            try:
                from zenml.service_connectors.docker_service_connector import (  # noqa
                    DockerServiceConnector,
                )
            except ImportError as e:
                logger.warning(
                    f"Could not import Docker service connector: {e}."
                )

            try:
                from zenml.integrations.hyperai.service_connectors.hyperai_service_connector import (  # noqa
                    HyperAIServiceConnector,
                )
            except ImportError as e:
                logger.warning(
                    f"Could not import HyperAI service connector: {e}."
                )


service_connector_registry = ServiceConnectorRegistry()
