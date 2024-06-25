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
"""HashiCorp Vault Secrets Store implementation."""

from typing import (
    ClassVar,
    Dict,
    Optional,
    Type,
)
from uuid import UUID

import hvac  # type: ignore[import-untyped]
from hvac.exceptions import (  # type: ignore[import-untyped]
    InvalidPath,
    VaultError,
)
from pydantic import ConfigDict

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretsStoreType,
)
from zenml.logger import get_logger
from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    BaseSecretsStore,
)

logger = get_logger(__name__)


HVAC_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_VAULT_SECRET_VALUES_KEY = "zenml_secret_values"
ZENML_VAULT_SECRET_METADATA_KEY = "zenml_secret_metadata"


class HashiCorpVaultSecretsStoreConfiguration(SecretsStoreConfiguration):
    """HashiCorp Vault secrets store configuration.

    Attributes:
        type: The type of the store.
        vault_addr: The url of the Vault server. If not set, the value will be
            loaded from the VAULT_ADDR environment variable, if configured.
        vault_token: The token used to authenticate with the Vault server. If
            not set, the token will be loaded from the VAULT_TOKEN environment
            variable or from the ~/.vault-token file, if configured.
        vault_namespace: The Vault Enterprise namespace.
        mount_point: The mount point to use for all secrets.
        max_versions: The maximum number of secret versions to keep.
    """

    type: SecretsStoreType = SecretsStoreType.HASHICORP

    vault_addr: str
    vault_token: Optional[PlainSerializedSecretStr] = None
    vault_namespace: Optional[str] = None
    mount_point: Optional[str] = None
    max_versions: int = 1
    model_config = ConfigDict(extra="forbid")


class HashiCorpVaultSecretsStore(BaseSecretsStore):
    """Secrets store implementation that uses the HashiCorp Vault API.

    This secrets store implementation uses the HashiCorp Vault API to
    store secrets. It allows a single HashiCorp Vault server to be shared with
    other ZenML deployments as well as other third party users and applications.

    Here are some implementation highlights:

    * the name/ID of an HashiCorp Vault secret is derived from the ZenML secret
    UUID and a `zenml` prefix in the form `zenml/{zenml_secret_uuid}`. This
    clearly identifies a secret as being managed by ZenML in the HashiCorp Vault
    server.

    * given that HashiCorp Vault secrets do not support attaching arbitrary
    metadata in the form of label or tags, we store the entire ZenML secret
    metadata alongside the secret values in the HashiCorp Vault secret value.

    Attributes:
        config: The configuration of the HashiCorp Vault secrets store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
    """

    config: HashiCorpVaultSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.HASHICORP
    CONFIG_TYPE: ClassVar[Type[SecretsStoreConfiguration]] = (
        HashiCorpVaultSecretsStoreConfiguration
    )

    _client: Optional[hvac.Client] = None

    @property
    def client(self) -> hvac.Client:
        """Initialize and return the HashiCorp Vault client.

        Returns:
            The HashiCorp Vault client.
        """
        if self._client is None:
            # Initialize the HashiCorp Vault client with the
            # credentials from the configuration.
            self._client = hvac.Client(
                url=self.config.vault_addr,
                token=self.config.vault_token.get_secret_value()
                if self.config.vault_token
                else None,
                namespace=self.config.vault_namespace,
            )
            self._client.secrets.kv.v2.configure(
                max_versions=self.config.max_versions,
            )
            if self.config.mount_point:
                self._client.secrets.kv.v2.configure(
                    mount_point=self.config.mount_point,
                )
        return self._client

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the HashiCorp Vault secrets store."""
        logger.debug("Initializing HashiCorpVaultSecretsStore")

        # Initialize the HashiCorp Vault client early, just to catch any
        # configuration or authentication errors early, before the Secrets
        # Store is used.
        _ = self.client

    # ------
    # Secrets
    # ------

    @staticmethod
    def _get_vault_secret_id(
        secret_id: UUID,
    ) -> str:
        """Get the HashiCorp Vault secret ID corresponding to a ZenML secret ID.

        The convention used for HashiCorp Vault secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the HashiCorp Vault secret name,
        i.e. `zenml/<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The HashiCorp Vault secret name.
        """
        return f"{HVAC_ZENML_SECRET_NAME_PREFIX}/{str(secret_id)}"

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
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        metadata = self._get_secret_metadata(secret_id=secret_id)

        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_secret_id,
                # Store the ZenML secret metadata alongside the secret values
                secret={
                    ZENML_VAULT_SECRET_VALUES_KEY: secret_values,
                    ZENML_VAULT_SECRET_METADATA_KEY: metadata,
                },
                # Do not allow overwriting an existing secret
                cas=0,
            )
        except VaultError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug(f"Created HashiCorp Vault secret: {vault_secret_id}")

    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        try:
            vault_secret = (
                self.client.secrets.kv.v2.read_secret(
                    path=vault_secret_id,
                )
                .get("data", {})
                .get("data", {})
            )
        except InvalidPath as e:
            raise KeyError(
                f"Can't find the secret values for secret ID '{secret_id}' "
                f"in the secrets store back-end: {str(e)}"
            ) from e
        except VaultError as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        try:
            metadata = vault_secret[ZENML_VAULT_SECRET_METADATA_KEY]
            values = vault_secret[ZENML_VAULT_SECRET_VALUES_KEY]
        except (KeyError, ValueError) as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        if not isinstance(values, dict) or not isinstance(metadata, dict):
            raise RuntimeError(
                f"HashiCorp Vault secret values for secret {vault_secret_id} "
                "could not be retrieved: invalid type for metadata or values"
            )

        # The _verify_secret_metadata method raises a KeyError if the
        # secret is not valid or does not belong to this server. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place.
        self._verify_secret_metadata(
            secret_id=secret_id,
            metadata=metadata,
        )

        logger.debug(f"Fetched HashiCorp Vault secret: {vault_secret_id}")

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
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        # Convert the ZenML secret metadata to HashiCorp Vault tags
        metadata = self._get_secret_metadata(secret_id=secret_id)

        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_secret_id,
                # Store the ZenML secret metadata alongside the secret values
                secret={
                    ZENML_VAULT_SECRET_VALUES_KEY: secret_values,
                    ZENML_VAULT_SECRET_METADATA_KEY: metadata,
                },
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} does not exist.")
        except VaultError as e:
            raise RuntimeError(f"Error updating secret {secret_id}: {e}")

        logger.debug(f"Updated HashiCorp Vault secret: {vault_secret_id}")

    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=vault_secret_id,
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} does not exist.")
        except VaultError as e:
            raise RuntimeError(
                f"Error deleting secret with ID {secret_id}: {e}"
            )

        logger.debug(f"Deleted HashiCorp Vault secret: {vault_secret_id}")
