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

import base64
import json
from typing import Any, ClassVar, List, Optional, cast

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from zenml.exceptions import SecretExistsError
from zenml.integrations.azure.flavors.azure_secrets_manager_flavor import (
    AzureSecretsManagerConfig,
    validate_azure_secret_name_or_namespace,
)
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import (
    ZENML_SECRET_NAME_LABEL,
    BaseSecretsManager,
    SecretsManagerScope,
)
from zenml.secrets_managers.utils import secret_from_dict, secret_to_dict

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml-schema-name"
ZENML_GROUP_KEY = "zenml-group-key"
ZENML_KEY_NAME = "zenml-key-name"
ZENML_AZURE_SECRET_SCOPE_PATH_SEPARATOR = "-"


class AzureSecretsManager(BaseSecretsManager):
    """Class to interact with the Azure secrets manager."""

    CLIENT: ClassVar[Any] = None

    @property
    def config(self) -> AzureSecretsManagerConfig:
        """Returns the `AzureSecretsManagerConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureSecretsManagerConfig, self._config)

    @classmethod
    def _ensure_client_connected(cls, vault_name: str) -> None:
        if cls.CLIENT is None:
            KVUri = f"https://{vault_name}.vault.azure.net"

            credential = DefaultAzureCredential()
            cls.CLIENT = SecretClient(vault_url=KVUri, credential=credential)

    def validate_secret_name(self, name: str) -> None:
        """Validate a secret name.

        Args:
            name: the secret name
        """
        validate_azure_secret_name_or_namespace(name, self.config.scope)

    def _create_or_update_secret(self, secret: BaseSecretSchema) -> None:
        """Creates a new secret or updated an existing one.

        Args:
            secret: the secret to register or update
        """
        if self.config.scope == SecretsManagerScope.NONE:
            # legacy, non-scoped secrets

            for key, value in secret.content.items():
                encoded_key = base64.b64encode(
                    f"{secret.name}-{key}".encode()
                ).hex()
                azure_secret_name = f"zenml-{encoded_key}"

                self.CLIENT.set_secret(azure_secret_name, value)
                self.CLIENT.update_secret_properties(
                    azure_secret_name,
                    tags={
                        ZENML_GROUP_KEY: secret.name,
                        ZENML_KEY_NAME: key,
                        ZENML_SCHEMA_NAME: secret.TYPE,
                    },
                )

                logger.debug(
                    "Secret `%s` written to the Azure Key Vault.",
                    azure_secret_name,
                )
        else:
            azure_secret_name = self._get_scoped_secret_name(
                secret.name,
                separator=ZENML_AZURE_SECRET_SCOPE_PATH_SEPARATOR,
            )
            self.CLIENT.set_secret(
                azure_secret_name,
                json.dumps(secret_to_dict(secret)),
            )
            self.CLIENT.update_secret_properties(
                azure_secret_name,
                tags=self._get_secret_metadata(secret),
            )

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register

        Raises:
            SecretExistsError: if the secret already exists
        """
        self.validate_secret_name(secret.name)
        self._ensure_client_connected(self.config.key_vault_name)

        if secret.name in self.get_all_secret_keys():
            raise SecretExistsError(
                f"A Secret with the name '{secret.name}' already exists."
            )

        self._create_or_update_secret(secret)

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Get a secret by its name.

        Args:
            secret_name: the name of the secret to get

        Returns:
            The secret.

        Raises:
            KeyError: if the secret does not exist
            ValueError: if the secret is named 'name'
        """
        self.validate_secret_name(secret_name)
        self._ensure_client_connected(self.config.key_vault_name)
        zenml_secret: Optional[BaseSecretSchema] = None

        if self.config.scope == SecretsManagerScope.NONE:
            # Legacy secrets are mapped to multiple Azure secrets, one for
            # each secret key

            secret_contents = {}
            zenml_schema_name = ""

            for secret_property in self.CLIENT.list_properties_of_secrets():
                tags = secret_property.tags

                if tags and tags.get(ZENML_GROUP_KEY) == secret_name:
                    secret_key = tags.get(ZENML_KEY_NAME)
                    if not secret_key:
                        raise ValueError("Missing secret key tag.")

                    if secret_key == "name":
                        raise ValueError("The secret's key cannot be 'name'.")

                    response = self.CLIENT.get_secret(secret_property.name)
                    secret_contents[secret_key] = response.value

                    zenml_schema_name = tags.get(ZENML_SCHEMA_NAME)

            if secret_contents:
                secret_contents["name"] = secret_name

                secret_schema = SecretSchemaClassRegistry.get_class(
                    secret_schema=zenml_schema_name
                )
                zenml_secret = secret_schema(**secret_contents)
        else:
            # Scoped secrets are mapped 1-to-1 with Azure secrets

            try:
                response = self.CLIENT.get_secret(
                    self._get_scoped_secret_name(
                        secret_name,
                        separator=ZENML_AZURE_SECRET_SCOPE_PATH_SEPARATOR,
                    ),
                )

                scope_tags = self._get_secret_scope_metadata(secret_name)

                # all scope tags need to be included in the Azure secret tags,
                # otherwise the secret does not belong to the current scope,
                # even if it has the same name
                if scope_tags.items() <= response.properties.tags.items():
                    zenml_secret = secret_from_dict(
                        json.loads(response.value), secret_name=secret_name
                    )
            except ResourceNotFoundError:
                pass

        if not zenml_secret:
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        return zenml_secret

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        Returns:
            A list of all secret keys
        """
        self._ensure_client_connected(self.config.key_vault_name)

        set_of_secrets = set()

        for secret_property in self.CLIENT.list_properties_of_secrets():
            tags = secret_property.tags
            if not tags:
                continue

            if self.config.scope == SecretsManagerScope.NONE:
                # legacy, non-scoped secrets
                if ZENML_GROUP_KEY in tags:
                    set_of_secrets.add(tags.get(ZENML_GROUP_KEY))
                continue

            scope_tags = self._get_secret_scope_metadata()
            # all scope tags need to be included in the Azure secret tags,
            # otherwise the secret does not belong to the current scope
            if scope_tags.items() <= tags.items():
                set_of_secrets.add(tags.get(ZENML_SECRET_NAME_LABEL))

        return list(set_of_secrets)

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret by creating new versions of the existing secrets.

        Args:
            secret: the secret to update

        Raises:
            KeyError: if the secret does not exist
        """
        self.validate_secret_name(secret.name)
        self._ensure_client_connected(self.config.key_vault_name)

        if secret.name not in self.get_all_secret_keys():
            raise KeyError(f"Can't find the specified secret '{secret.name}'")

        self._create_or_update_secret(secret)

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret. by name.

        Args:
            secret_name: the name of the secret to delete

        Raises:
            KeyError: if the secret no longer exists
        """
        self.validate_secret_name(secret_name)
        self._ensure_client_connected(self.config.key_vault_name)

        if self.config.scope == SecretsManagerScope.NONE:
            # legacy, non-scoped secrets

            # Go through all Azure secrets and delete the ones with the
            # secret_name as label.
            for secret_property in self.CLIENT.list_properties_of_secrets():
                tags = secret_property.tags
                if tags and tags.get(ZENML_GROUP_KEY) == secret_name:
                    self.CLIENT.begin_delete_secret(
                        secret_property.name
                    ).result()

        else:
            if secret_name not in self.get_all_secret_keys():
                raise KeyError(
                    f"Can't find the specified secret '{secret_name}'"
                )
            self.CLIENT.begin_delete_secret(
                self._get_scoped_secret_name(
                    secret_name,
                    separator=ZENML_AZURE_SECRET_SCOPE_PATH_SEPARATOR,
                ),
            ).result()

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
        self._ensure_client_connected(self.config.key_vault_name)

        # List all secrets.
        for secret_property in self.CLIENT.list_properties_of_secrets():

            tags = secret_property.tags
            if not tags:
                continue

            if self.config.scope == SecretsManagerScope.NONE:
                # legacy, non-scoped secrets
                if ZENML_GROUP_KEY in tags:
                    logger.info(
                        "Deleted key-value pair {`%s`, `***`} from secret "
                        "`%s`",
                        secret_property.name,
                        tags.get(ZENML_GROUP_KEY),
                    )
                    self.CLIENT.begin_delete_secret(
                        secret_property.name
                    ).result()
                continue

            scope_tags = self._get_secret_scope_metadata()
            # all scope tags need to be included in the Azure secret tags,
            # otherwise the secret does not belong to the current scope
            if scope_tags.items() <= tags.items():
                self.CLIENT.begin_delete_secret(secret_property.name).result()
