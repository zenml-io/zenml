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
"""Azure Secrets Store implementation."""

import json
import logging
from typing import (
    Any,
    ClassVar,
    Dict,
    Type,
    cast,
)
from uuid import UUID

from azure.core.credentials import TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.keyvault.secrets import SecretClient
from pydantic import ConfigDict, model_validator

from zenml.enums import (
    SecretsStoreType,
)
from zenml.integrations.azure import (
    AZURE_CONNECTOR_TYPE,
    AZURE_RESOURCE_TYPE,
)
from zenml.integrations.azure.service_connectors.azure_service_connector import (
    AzureAuthenticationMethods,
)
from zenml.logger import get_logger
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.zen_stores.secrets_stores.service_connector_secrets_store import (
    ServiceConnectorSecretsStore,
    ServiceConnectorSecretsStoreConfiguration,
)

logger = get_logger(__name__)


AZURE_ZENML_SECRET_NAME_PREFIX = "zenml"


class AzureSecretsStoreConfiguration(
    ServiceConnectorSecretsStoreConfiguration
):
    """Azure secrets store configuration.

    Attributes:
        type: The type of the store.
        key_vault_name: Name of the Azure Key Vault that this secrets store
            will use to store secrets.
    """

    type: SecretsStoreType = SecretsStoreType.AZURE
    key_vault_name: str

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def populate_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Populate the connector configuration from legacy attributes.

        Args:
            data: Dict representing user-specified runtime settings.

        Returns:
            Validated settings.
        """
        # Search for legacy attributes and populate the connector configuration
        # from them, if they exist.
        if (
            data.get("azure_client_id")
            and data.get("azure_client_secret")
            and data.get("azure_tenant_id")
        ):
            logger.warning(
                "The `azure_client_id`, `azure_client_secret` and "
                "`azure_tenant_id` attributes are deprecated and will be "
                "removed in a future version or ZenML. Please use the "
                "`auth_method` and `auth_config` attributes instead."
            )
            data["auth_method"] = AzureAuthenticationMethods.SERVICE_PRINCIPAL
            data["auth_config"] = dict(
                client_id=data.get("azure_client_id"),
                client_secret=data.get("azure_client_secret"),
                tenant_id=data.get("azure_tenant_id"),
            )

        return data

    model_config = ConfigDict(extra="allow")


class AzureSecretsStore(ServiceConnectorSecretsStore):
    """Secrets store implementation that uses the Azure Key Vault API.

    This secrets store implementation uses the Azure Key Vault API to
    store secrets. It allows a single Azure Key Vault to be shared with other
    ZenML deployments as well as other third party users and applications.

    Here are some implementation highlights:

    * the name/ID of an Azure secret is derived from the ZenML secret UUID and a
    `zenml` prefix in the form `zenml-{zenml_secret_uuid}`. This clearly
    identifies a secret as being managed by ZenML in the Azure console.

    * the Secrets Store also uses Azure Key Vault secret tags to store metadata
    associated with a ZenML secret. The `zenml` tag in particular is used to
    identify and group all secrets that belong to the same ZenML deployment.

    * all secret key-values configured in a ZenML secret are stored as a single
    JSON string value in the Azure Key Vault secret value.
    """

    config: AzureSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.AZURE
    CONFIG_TYPE: ClassVar[Type[ServiceConnectorSecretsStoreConfiguration]] = (
        AzureSecretsStoreConfiguration
    )
    SERVICE_CONNECTOR_TYPE: ClassVar[str] = AZURE_CONNECTOR_TYPE
    SERVICE_CONNECTOR_RESOURCE_TYPE: ClassVar[str] = AZURE_RESOURCE_TYPE

    @property
    def client(self) -> SecretClient:
        """Initialize and return the Azure Key Vault client.

        Returns:
            The Azure Key Vault client.
        """
        return cast(SecretClient, super().client)

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize_client_from_connector(self, client: Any) -> Any:
        """Initialize the Azure Key Vault client from the service connector client.

        Args:
            client: The authenticated client object returned by the service
                connector.

        Returns:
            The Azure Key Vault client.
        """
        assert isinstance(client, TokenCredential)
        azure_logger = logging.getLogger("azure")

        # Suppress the INFO logging level of the Azure SDK if the
        # ZenML logging level is WARNING or lower.
        if logger.level <= logging.WARNING:
            azure_logger.setLevel(logging.WARNING)
        else:
            azure_logger.setLevel(logging.INFO)

        vault_url = f"https://{self.config.key_vault_name}.vault.azure.net"
        return SecretClient(vault_url=vault_url, credential=client)

    # ------
    # Secrets
    # ------

    @staticmethod
    def _get_azure_secret_id(
        secret_id: UUID,
    ) -> str:
        """Get the Azure secret ID corresponding to a ZenML secret ID.

        The convention used for Azure secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the Azure secret name,
        i.e. `zenml-<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The Azure secret name.
        """
        return f"{AZURE_ZENML_SECRET_NAME_PREFIX}-{str(secret_id)}"

    def store_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Store secret values for a new secret.

        Args:
            secret_id: ID of the secret.
            secret_values: Values for the secret.

        Raises:
            RuntimeError: if the Azure Key Vault API returns an unexpected
                error.
        """
        azure_secret_id = self._get_azure_secret_id(secret_id)
        secret_value = json.dumps(secret_values)

        # Use the ZenML secret metadata as Azure tags
        metadata = self._get_secret_metadata(secret_id=secret_id)

        try:
            self.client.set_secret(
                azure_secret_id,
                secret_value,
                tags=metadata,
                content_type="application/json",
            )
        except HttpResponseError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug(f"Created Azure secret: {azure_secret_id}")

    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: if the Azure Key Vault API returns an unexpected
                error.
        """
        azure_secret_id = self._get_azure_secret_id(secret_id)

        try:
            azure_secret = self.client.get_secret(
                azure_secret_id,
            )
        except ResourceNotFoundError as e:
            raise KeyError(
                f"Can't find the secret values for secret ID '{secret_id}' "
                f"in the secrets store back-end: {str(e)}"
            ) from e
        except HttpResponseError as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        # The _verify_secret_metadata method raises a KeyError if the
        # secret is not valid or does not belong to this server. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place.
        assert azure_secret.properties.tags is not None
        self._verify_secret_metadata(
            secret_id=secret_id,
            metadata=azure_secret.properties.tags,
        )

        values = json.loads(azure_secret.value) if azure_secret.value else {}

        if not isinstance(values, dict):
            raise RuntimeError(
                f"Azure Key Vault secret values for secret {azure_secret_id} "
                "could not be retrieved: invalid type for values"
            )

        logger.debug(f"Retrieved Azure secret: {azure_secret_id}")

        return values

    def update_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Updates secret values for an existing secret.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_values: The new secret values.

        Raises:
            RuntimeError: if the Azure Key Vault API returns an unexpected
                error.
        """
        azure_secret_id = self._get_azure_secret_id(secret_id)
        secret_value = json.dumps(secret_values)

        # Convert the ZenML secret metadata to Azure tags
        metadata = self._get_secret_metadata(secret_id=secret_id)

        try:
            self.client.set_secret(
                azure_secret_id,
                secret_value,
                tags=metadata,
                content_type="application/json",
            )
        except HttpResponseError as e:
            raise RuntimeError(f"Error updating secret {secret_id}: {e}")

        logger.debug(f"Updated Azure secret: {azure_secret_id}")

    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: if the Azure Key Vault API returns an unexpected
                error.
        """
        azure_secret_id = self._get_azure_secret_id(secret_id)

        try:
            self.client.begin_delete_secret(
                azure_secret_id,
            ).wait()
        except ResourceNotFoundError:
            raise KeyError(f"Secret with ID {secret_id} not found")
        except HttpResponseError as e:
            raise RuntimeError(
                f"Error deleting secret with ID {secret_id}: {e}"
            )

        logger.debug(f"Deleted Azure secret: {azure_secret_id}")
