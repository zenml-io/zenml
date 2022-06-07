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
import re
from typing import Any, ClassVar, List, Optional, Set

import hvac

from zenml.exceptions import SecretDoesNotExistError, SecretExistsError
from zenml.integrations.vault import VAULT_SECRETS_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_PATH = "zenml"


def sanitize_secret_name(secret_name: str) -> str:
    """Sanitize the secret name to be used in Vault."""
    return re.sub(r"[^0-9a-zA-Z_\.]+", "_", secret_name).strip("-_.")


def prepend_secret_schema_to_secret_name(secret: BaseSecretSchema) -> str:
    """
    Prepend the secret schema name to the secret name.

    Args:
        secret: The secret to prepend the secret schema name to.

    Returns:
        The secret name with the secret schema name prepended.
    """
    secret_name = sanitize_secret_name(secret.name)
    secret_schema_name = secret.TYPE
    return f"{secret_schema_name}-{secret_name}"


def remove_secret_schema_name(combined_secret_name: str) -> str:
    """
    Remove the secret schema name from the secret name.

    Args:
        combined_secret_name: The secret name to remove the secret schema name from.

    Returns:
        The secret name with the secret schema name removed.
    """
    if "-" in combined_secret_name:
        return combined_secret_name.split("-")[1]
    else:
        raise RuntimeError(
            f"Secret name `{combined_secret_name}` does not have a "
            f"Secret_schema name on it."
        )


def get_secret_schema_name(combined_secret_name: str) -> str:
    """
    Get the secret schema name from the secret name.

    Args:
        combined_secret_name: The secret name to get the secret schema name from.

    Returns:
        The secret schema name.
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
    cert: Optional[str]
    verify: Optional[str]
    namespace: Optional[str]
    mount_point: Optional[str] = "secret"

    @classmethod
    def _ensure_client_connected(cls, url: str, token: str) -> None:

        if cls.CLIENT is None:
            # Create a Vault Secrets Manager client
            cls.CLIENT = hvac.Client(
                url=url,
                token=token,
            )

    def _ensure_client_is_authenticated(self) -> None:
        """
        Ensure the client is authenticated.

        Raises:
            RuntimeError: If the client is not initialized or authenticated.
        """

        self._ensure_client_connected(url=self.url, token=self.token)

        if not self.CLIENT:
            raise RuntimeError("Vault client is not initialized.")
        else:
            if not self.CLIENT.is_authenticated():
                raise RuntimeError("Vault client is not authenticated.")
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

        if secret_name in self.get_all_secret_keys():
            raise SecretExistsError(
                f"A Secret with the name '{secret_name}' already exists."
            )

        self.CLIENT.secrets.kv.v2.create_or_update_secret(
            path=f"{ZENML_PATH}/{secret_name}",
            secret=secret.content,
        )

        logger.debug("Created secret: %s", f"{ZENML_PATH}/{secret_name}")
        logger.debug("Added value to secret.")

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        Args:
            secret_name: The name of the secret to get.

        Returns:
            The secret.

        Raises:
            SecretDoesNotExistError: If the secret does not exist.
        """

        try:
            vault_secret_name = self.vault_secret_name(secret_name)
        except SecretDoesNotExistError:
            raise SecretDoesNotExistError(
                f"The secret {secret_name} does not exist."
            )

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

    def vaul_list_secrets(self) -> List[str]:
        """
        List all secrets in the secrets manager without any reformatting.
        All secrets names stored in Vault in the format: <secret_schema>-<secret_name>

        Returns:
            A list of all secrets in the secrets manager.

        Raises:
            RuntimeError: If the client is not initialized or authenticated.
            InvalidPath: If the path is invalid.
        """

        self._ensure_client_is_authenticated()

        set_of_secrets: Set[str] = set()
        try:
            secrets = self.CLIENT.secrets.kv.v2.list_secrets(
                path=f"{ZENML_PATH}/", mount_point=self.mount_point
            )
        except hvac.exceptions.InvalidPath:
            print(
                f"There are no secrets created within the path `{ZENML_PATH}` "
            )
            return list(set_of_secrets)

        secrets_keys = secrets.get("data", {}).get("keys", [])
        for secret_key in secrets_keys:
            set_of_secrets.add(secret_key)
        return list(set_of_secrets)

    def vault_secret_name(self, secret_name: str) -> str:
        """
        Get the secret name in the Vault secrets manager, without any reformatting.
        The secret name should be in the format `<secret_schema_name>-<secret_name>`.

        Args:
            secret_name: The name of the secret to get.

        Returns:
            The secret name in the Vault secrets manager.

        Raises:
            SecretDoesNotExistError: If the secret does not exist.
        """

        self._ensure_client_is_authenticated()

        secrets_keys = self.vaul_list_secrets()

        for secret_key in secrets_keys:
            sanitized_secret_name = sanitize_secret_name(secret_name)
            secret_name_without_schema = remove_secret_schema_name(secret_key)
            if sanitized_secret_name == secret_name_without_schema:
                return secret_key
        raise SecretDoesNotExistError(
            f"The secret {secret_name} does not exist."
        )

    def get_all_secret_keys(self) -> List[str]:
        """
        Get all secret keys in the secrets manager.

        Returns:
            A list of all secret keys in the secrets manager.
        """

        return [
            remove_secret_schema_name(secret_key)
            for secret_key in self.vaul_list_secrets()
        ]

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: The secret to update.

        Raises:
            SecretDoesNotExistError: If the secret does not exist.
        """

        self._ensure_client_is_authenticated()

        secret_name = prepend_secret_schema_to_secret_name(secret=secret)

        if secret_name in self.vaul_list_secrets():
            self.CLIENT.secrets.kv.v2.create_or_update_secret(
                path=f"{ZENML_PATH}/{secret.name}",
                secret=secret.content.items(),
            )
        else:
            raise SecretDoesNotExistError(
                f"A Secret with the name '{secret.name}' does not exist."
            )

        logger.debug("Updated secret: %s", f"{ZENML_PATH}/{secret.name}")
        logger.debug("Added value to secret.")

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: The name of the secret to delete.

        Raises:
            SecretDoesNotExistError: If the secret does not exist.
        """

        self._ensure_client_is_authenticated()

        try:
            vault_secret_name = self.vault_secret_name(secret_name)
        except SecretDoesNotExistError:
            raise SecretDoesNotExistError(
                f"The secret {secret_name} does not exist."
            )

        self.CLIENT.secrets.kv.v2.delete_metadata_and_all_versions(
            path=f"{ZENML_PATH}/{vault_secret_name}",
        )

        logger.debug("Deleted secret: %s", f"{ZENML_PATH}/{secret_name}")

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: Whether to force deletion of secrets.
        """
        self._ensure_client_is_authenticated()

        try:
            self.CLIENT.secrets.kv.v2.delete_metadata_and_all_versions(
                path=f"{ZENML_PATH}",
            )
        except hvac.exceptions.InvalidPath:
            print(
                f"There are no secrets created within the path `{ZENML_PATH}` "
            )
            return
