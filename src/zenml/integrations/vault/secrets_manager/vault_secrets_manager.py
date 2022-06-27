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
"""Implementation of the HashiCorp Vault Secrets Manager integration."""

import re
from typing import Any, ClassVar, List, Optional, Set

import hvac  # type: ignore[import]

from zenml.exceptions import SecretExistsError
from zenml.integrations.vault import VAULT_SECRETS_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_PATH = "zenml"


def sanitize_secret_name(secret_name: str) -> str:
    """Sanitize the secret name to be used in Vault.

    Args:
        secret_name: The secret name to sanitize.

    Returns:
        The sanitized secret name.
    """
    return re.sub(r"[^0-9a-zA-Z_\.]+", "_", secret_name).strip("-_.")


def prepend_secret_schema_to_secret_name(secret: BaseSecretSchema) -> str:
    """Prepend the secret schema name to the secret name.

    Args:
        secret: The secret to prepend the secret schema name to.

    Returns:
        The secret name with the secret schema name prepended.
    """
    secret_name = sanitize_secret_name(secret.name)
    secret_schema_name = secret.TYPE
    return f"{secret_schema_name}-{secret_name}"


def remove_secret_schema_name(combined_secret_name: str) -> str:
    """Remove the secret schema name from the secret name.

    Args:
        combined_secret_name: The secret name to remove the secret schema name from.

    Returns:
        The secret name without the secret schema name.

    Raises:
        RuntimeError: If the secret name does not have a secret schema name on it.
    """
    if "-" in combined_secret_name:
        return combined_secret_name.split("-")[1]
    else:
        raise RuntimeError(
            f"Secret name `{combined_secret_name}` does not have a "
            f"Secret_schema name on it."
        )


def get_secret_schema_name(combined_secret_name: str) -> str:
    """Get the secret schema name from the secret name.

    Args:
        combined_secret_name: The secret name to get the secret schema name from.

    Returns:
        The secret schema name.

    Raises:
        RuntimeError: If the secret name does not have a secret schema name on it.
    """
    if "-" in combined_secret_name:
        return combined_secret_name.split("-")[0]
    else:
        raise RuntimeError(
            f"Secret name `{combined_secret_name}` does not have a "
            f"Secret_schema name on it."
        )


class VaultSecretsManager(BaseSecretsManager):
    """Class to interact with the Vault secrets manager - Key/value Engine.

    Attributes:
        url: The url of the Vault server.
        token: The token to use to authenticate with Vault.
        cert: The path to the certificate to use to authenticate with Vault.
        verify: Whether to verify the certificate or not.
        mount_point: The mount point of the secrets manager.
        namespace: The namespace of the secrets manager.
    """

    # Class configuration
    FLAVOR: ClassVar[str] = VAULT_SECRETS_MANAGER_FLAVOR
    CLIENT: ClassVar[Any] = None

    url: str
    token: str
    mount_point: str
    cert: Optional[str]
    verify: Optional[str]
    namespace: Optional[str]

    @classmethod
    def _ensure_client_connected(cls, url: str, token: str) -> None:
        """Ensure the client is connected.

        This function initializes the client if it is not initialized.

        Args:
            url: The url of the Vault server.
            token: The token to use to authenticate with Vault.
        """
        if cls.CLIENT is None:
            # Create a Vault Secrets Manager client
            cls.CLIENT = hvac.Client(
                url=url,
                token=token,
            )

    def _ensure_client_is_authenticated(self) -> None:
        """Ensure the client is authenticated.

        Raises:
            RuntimeError: If the client is not initialized or authenticated.
        """
        self._ensure_client_connected(url=self.url, token=self.token)

        if not self.CLIENT.is_authenticated():
            raise RuntimeError(
                "There was an error authenticating with Vault. Please check your configuration."
            )
        else:
            pass

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.

        Raises:
            SecretExistsError: If the secret already exists.
        """
        self._ensure_client_is_authenticated()

        secret_name = prepend_secret_schema_to_secret_name(secret=secret)

        if secret.name in self.get_all_secret_keys():
            raise SecretExistsError(
                f"A Secret with the name '{secret.name}' already exists."
            )

        self.CLIENT.secrets.kv.v2.create_or_update_secret(
            path=f"{ZENML_PATH}/{secret_name}",
            mount_point=self.mount_point,
            secret=secret.content,
        )

        logger.info("Created secret: %s", f"{ZENML_PATH}/{secret_name}")
        logger.info("Added value to secret.")

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        Args:
            secret_name: The name of the secret to get.

        Returns:
            The secret.
        """
        vault_secret_name = self.vault_secret_name(secret_name)

        secret_items = (
            self.CLIENT.secrets.kv.v2.read_secret_version(
                path=f"{ZENML_PATH}/{vault_secret_name}",
                mount_point=self.mount_point,
            )
            .get("data", {})
            .get("data", {})
        )

        secret_schema = SecretSchemaClassRegistry.get_class(
            secret_schema=get_secret_schema_name(vault_secret_name)
        )
        secret_items["name"] = sanitize_secret_name(secret_name)
        return secret_schema(**secret_items)

    def vault_list_secrets(self) -> List[str]:
        """List all secrets in Vault without any reformatting.

        This function tries to get all secrets from Vault and returns
        them as a list of strings (all secrets' names)
        in the format: <secret_schema>-<secret_name>

        Returns:
            A list of all secrets in the secrets manager.
        """
        self._ensure_client_is_authenticated()

        set_of_secrets: Set[str] = set()
        try:
            secrets = self.CLIENT.secrets.kv.v2.list_secrets(
                path=f"{ZENML_PATH}/", mount_point=self.mount_point
            )
        except hvac.exceptions.InvalidPath:
            logger.error(
                f"There are no secrets created within the path `{ZENML_PATH}` "
            )
            return list(set_of_secrets)

        secrets_keys = secrets.get("data", {}).get("keys", [])
        for secret_key in secrets_keys:
            set_of_secrets.add(secret_key)
        return list(set_of_secrets)

    def vault_secret_name(self, secret_name: str) -> str:
        """Get the secret name in the form it is stored in Vault.

        This function retrieves the secret name in the Vault secrets manager, without
        any reformatting. This secret should be in the format `<secret_schema_name>-<secret_name>`.

        Args:
            secret_name: The name of the secret to get.

        Returns:
            The secret name in the Vault secrets manager.

        Raises:
            KeyError: If the secret does not exist.
        """
        self._ensure_client_is_authenticated()

        secrets_keys = self.vault_list_secrets()
        sanitized_secret_name = sanitize_secret_name(secret_name)

        for secret_key in secrets_keys:
            secret_name_without_schema = remove_secret_schema_name(secret_key)
            if sanitized_secret_name == secret_name_without_schema:
                return secret_key
        raise KeyError(f"The secret {secret_name} does not exist.")

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        This function tries to get all secrets from Vault and returns
        them as a list of strings. All secrets names are without the schema.

        Returns:
            A list of all secret keys in the secrets manager.
        """
        return [
            remove_secret_schema_name(secret_key)
            for secret_key in self.vault_list_secrets()
        ]

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: The secret to update.

        Raises:
            KeyError: If the secret does not exist.
        """
        self._ensure_client_is_authenticated()

        secret_name = prepend_secret_schema_to_secret_name(secret=secret)

        if secret_name in self.vault_list_secrets():
            self.CLIENT.secrets.kv.v2.create_or_update_secret(
                path=f"{ZENML_PATH}/{secret_name}",
                mount_point=self.mount_point,
                secret=secret.content,
            )
        else:
            raise KeyError(
                f"A Secret with the name '{secret.name}' does not exist."
            )

        logger.info("Updated secret: %s", f"{ZENML_PATH}/{secret.name}")
        logger.info("Added value to secret.")

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: The name of the secret to delete.

        Raises:
            KeyError: If the secret does not exist.
        """
        self._ensure_client_is_authenticated()

        try:
            vault_secret_name = self.vault_secret_name(secret_name)
        except KeyError:
            raise KeyError(f"The secret {secret_name} does not exist.")

        self.CLIENT.secrets.kv.v2.delete_metadata_and_all_versions(
            path=f"{ZENML_PATH}/{vault_secret_name}",
            mount_point=self.mount_point,
        )

        logger.info("Deleted secret: %s", f"{ZENML_PATH}/{secret_name}")

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
        self._ensure_client_is_authenticated()

        for secret_name in self.get_all_secret_keys():
            self.delete_secret(secret_name)

        logger.info("Deleted all secrets.")
