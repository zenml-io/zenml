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
"""Base secrets store class used for all secrets stores that use a service connector."""


import json
from abc import abstractmethod
from threading import Lock
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Type,
)
from uuid import uuid4

from pydantic import Field, root_validator

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.logger import get_logger
from zenml.models import (
    ServiceConnectorRequest,
)
from zenml.service_connectors.service_connector import ServiceConnector
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    BaseSecretsStore,
)

logger = get_logger(__name__)


class ServiceConnectorSecretsStoreConfiguration(SecretsStoreConfiguration):
    """Base configuration for secrets stores that use a service connector.

    Attributes:
        auth_method: The service connector authentication method to use.
        auth_config: The service connector authentication configuration.
    """

    auth_method: str
    auth_config: Dict[str, Any] = Field(default_factory=dict)

    @root_validator(pre=True)
    def validate_auth_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Convert the authentication configuration if given in JSON format.

        Args:
            values: The configuration values.

        Returns:
            The validated configuration values.
        """
        if isinstance(values.get("auth_config"), str):
            values["auth_config"] = json.loads(values["auth_config"])
        return values


class ServiceConnectorSecretsStore(BaseSecretsStore):
    """Base secrets store class for service connector-based secrets stores.

    All secrets store implementations that use a Service Connector to
    authenticate and connect to the secrets store back-end should inherit from
    this class and:

    * implement the `_initialize_client_from_connector` method
    * use a configuration class that inherits from
    `ServiceConnectorSecretsStoreConfiguration`
    * set the `SERVICE_CONNECTOR_TYPE` to the service connector type used
    to connect to the secrets store back-end
    * set the `SERVICE_CONNECTOR_RESOURCE_TYPE` to the resource type used
    to connect to the secrets store back-end
    """

    config: ServiceConnectorSecretsStoreConfiguration
    CONFIG_TYPE: ClassVar[Type[ServiceConnectorSecretsStoreConfiguration]]
    SERVICE_CONNECTOR_TYPE: ClassVar[str]
    SERVICE_CONNECTOR_RESOURCE_TYPE: ClassVar[str]

    _connector: Optional[ServiceConnector] = None
    _client: Optional[Any] = None
    _lock: Optional[Lock] = None

    def _initialize(self) -> None:
        """Initialize the secrets store."""
        self._lock = Lock()
        # Initialize the client early, just to catch any configuration or
        # authentication errors early, before the Secrets Store is used.
        _ = self.client

    def _get_client(self) -> Any:
        """Initialize and return the secrets store API client.

        Returns:
            The secrets store API client object.
        """
        if self._connector is not None:
            # If the client connector expires, we'll try to get a new one.
            if self._connector.has_expired():
                self._connector = None
                self._client = None

        if self._connector is None:
            # Initialize a base service connector with the credentials from
            # the configuration.
            request = ServiceConnectorRequest(
                name="secrets-store",
                connector_type=self.SERVICE_CONNECTOR_TYPE,
                resource_types=[self.SERVICE_CONNECTOR_RESOURCE_TYPE],
                user=uuid4(),  # Use a fake user ID
                workspace=uuid4(),  # Use a fake workspace ID
                auth_method=self.config.auth_method,
                configuration=self.config.auth_config,
            )
            base_connector = service_connector_registry.instantiate_connector(
                model=request
            )
            self._connector = base_connector.get_connector_client()

        if self._client is None:
            # Use the connector to get a client object.
            client = self._connector.connect(
                # Don't verify again because we already did that when we
                # initialized the connector.
                verify=False
            )

            self._client = self._initialize_client_from_connector(client)
        return self._client

    @property
    def lock(self) -> Lock:
        """Get the lock used to treat the client initialization as a critical section.

        Returns:
            The lock instance.
        """
        assert self._lock is not None
        return self._lock

    @property
    def client(self) -> Any:
        """Get the secrets store API client.

        Returns:
            The secrets store API client instance.
        """
        # Multiple API calls can be made to this secrets store in the context
        # of different threads. We want to make sure that we only initialize
        # the client once, and then reuse it. We have to use a lock to treat
        # this method as a critical section.
        with self.lock:
            return self._get_client()

    @abstractmethod
    def _initialize_client_from_connector(self, client: Any) -> Any:
        """Initialize the client from the service connector.

        Args:
            client: The authenticated client object returned by the service
                connector.

        Returns:
            The initialized client instance.
        """
