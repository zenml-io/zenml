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
"""Implementation of the Azure Secrets Manager integration."""

from typing import Any, ClassVar, Dict, List

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient  # type: ignore[import]

from zenml.exceptions import SecretExistsError
from zenml.integrations.azure import AZURE_SECRETS_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_GROUP_KEY = "zenml-group-key"


def prepend_group_name_to_keys(secret: BaseSecretSchema) -> Dict[str, str]:
    """Adds the secret group name to the keys of each secret key-value pair.

    This allows using the same key across multiple
    secrets.

    Args:
        secret: The ZenML Secret schema

    Returns:
        A dictionary with the secret keys prepended with the group name
    """
    return {f"{secret.name}-{k}": v for k, v in secret.content.items()}


def remove_group_name_from_key(combined_key_name: str, group_name: str) -> str:
    """Removes the secret group name from the secret key.

    Args:
        combined_key_name: Full name as it is within the Azure secrets manager
        group_name: Group name (the ZenML Secret name)

    Returns:
        The cleaned key

    Raises:
        RuntimeError: If the group name is not found in the key name
    """
    if combined_key_name.startswith(f"{group_name}-"):
        return combined_key_name[len(f"{group_name}-") :]
    else:
        raise RuntimeError(
            f"Key-name `{combined_key_name}` does not have the "
            f"prefix `{group_name}`. Key could not be "
            f"extracted."
        )


class AzureSecretsManager(BaseSecretsManager):
    """Class to interact with the Azure secrets manager.

    Attributes:
        project_id:  This is necessary to access the correct Azure project.
                     The project_id of your Azure project space that contains
                     the Secret Manager.
    """

    key_vault_name: str

    # Class configuration
    FLAVOR: ClassVar[str] = AZURE_SECRETS_MANAGER_FLAVOR
    CLIENT: ClassVar[Any] = None

    @classmethod
    def _ensure_client_connected(cls, vault_name: str) -> None:
        if cls.CLIENT is None:
            KVUri = f"https://{vault_name}.vault.azure.net"

            credential = DefaultAzureCredential()
            cls.CLIENT = SecretClient(vault_url=KVUri, credential=credential)

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register

        Raises:
            SecretExistsError: if the secret already exists
            ValueError: if the secret name contains an underscore.
        """
        self._ensure_client_connected(self.key_vault_name)

        if "_" in secret.name:
            raise ValueError(
                f"The secret name `{secret.name}` contains an underscore. "
                f"This will cause issues with Azure. Please try again."
            )

        if secret.name in self.get_all_secret_keys():
            raise SecretExistsError(
                f"A Secret with the name '{secret.name}' already exists."
            )

        adjusted_content = prepend_group_name_to_keys(secret)

        for k, v in adjusted_content.items():
            # Create the secret, this only creates an empty secret with the
            #  supplied name.
            azure_secret = self.CLIENT.set_secret(k, v)
            self.CLIENT.update_secret_properties(
                azure_secret.name,
                tags={
                    ZENML_GROUP_KEY: secret.name,
                    ZENML_SCHEMA_NAME: secret.TYPE,
                },
            )

            logger.debug("Created created secret: %s", azure_secret.name)
            logger.debug("Added value to secret.")

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Get a secret by its name.

        Args:
            secret_name: the name of the secret to get

        Returns:
            The secret.

        Raises:
            RuntimeError: if the secret does not exist
            ValueError: if the secret is named 'name'
        """
        self._ensure_client_connected(self.key_vault_name)

        secret_contents = {}
        zenml_schema_name = ""

        for secret_property in self.CLIENT.list_properties_of_secrets():
            response = self.CLIENT.get_secret(secret_property.name)
            tags = response.properties.tags
            if tags and tags.get(ZENML_GROUP_KEY) == secret_name:
                secret_key = remove_group_name_from_key(
                    combined_key_name=response.name, group_name=secret_name
                )
                if secret_key == "name":
                    raise ValueError("The secret's key cannot be 'name'.")

                secret_contents[secret_key] = response.value

                zenml_schema_name = tags.get(ZENML_SCHEMA_NAME)

        if not secret_contents:
            raise RuntimeError(f"No secrets found within the {secret_name}")

        secret_contents["name"] = secret_name

        secret_schema = SecretSchemaClassRegistry.get_class(
            secret_schema=zenml_schema_name
        )
        return secret_schema(**secret_contents)

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        Returns:
            A list of all secret keys
        """
        self._ensure_client_connected(self.key_vault_name)

        set_of_secrets = set()

        for secret_property in self.CLIENT.list_properties_of_secrets():
            tags = secret_property.tags
            if tags:
                set_of_secrets.add(tags.get(ZENML_GROUP_KEY))

        return list(set_of_secrets)

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret by creating new versions of the existing secrets.

        Args:
            secret: the secret to update
        """
        self._ensure_client_connected(self.key_vault_name)

        adjusted_content = prepend_group_name_to_keys(secret)

        for k, v in adjusted_content.items():
            self.CLIENT.set_secret(k, v)
            self.CLIENT.update_secret_properties(
                k,
                tags={
                    ZENML_GROUP_KEY: secret.name,
                    ZENML_SCHEMA_NAME: secret.TYPE,
                },
            )

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret. by name.

        In Azure a secret is a single k-v pair. Within ZenML a secret is a
        collection of k-v pairs. As such, deleting a secret will iterate through
        all secrets and delete the ones with the secret_name as label.

        Args:
            secret_name: the name of the secret to delete
        """
        self._ensure_client_connected(self.key_vault_name)

        # Go through all Azure secrets and delete the ones with the secret_name
        #  as label.
        for secret_property in self.CLIENT.list_properties_of_secrets():
            response = self.CLIENT.get_secret(secret_property.name)
            tags = response.properties.tags
            if tags and tags.get(ZENML_GROUP_KEY) == secret_name:
                self.CLIENT.begin_delete_secret(secret_property.name).result()

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: whether to force delete all secrets
        """
        self._ensure_client_connected(self.key_vault_name)

        # List all secrets.
        for secret_property in self.CLIENT.list_properties_of_secrets():
            response = self.CLIENT.get_secret(secret_property.name)
            tags = response.properties.tags
            if tags and (ZENML_GROUP_KEY in tags or ZENML_SCHEMA_NAME in tags):
                logger.info(
                    "Deleted key-value pair {`%s`, `***`} from secret " "`%s`",
                    secret_property.name,
                    tags.get(ZENML_GROUP_KEY),
                )
                self.CLIENT.begin_delete_secret(secret_property.name).result()
