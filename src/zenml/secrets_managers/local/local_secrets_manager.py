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
"""Implementation of the ZenML local secrets manager."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Type, cast

from zenml.cli.utils import error
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import LOCAL_SECRETS_FILENAME
from zenml.exceptions import SecretExistsError
from zenml.io.fileio import remove
from zenml.logger import get_logger
from zenml.secret import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import (
    BaseSecretsManager,
    BaseSecretsManagerConfig,
    BaseSecretsManagerFlavor,
)
from zenml.secrets_managers.utils import decode_secret_dict, encode_secret
from zenml.utils import yaml_utils
from zenml.utils.io_utils import create_file_if_not_exists

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.secret.base_secret import BaseSecretSchema


logger = get_logger(__name__)


class LocalSecretsManagerConfig(BaseSecretsManagerConfig):
    """Configuration for the local secrets manager.

    Attributes:
        secrets_file: The path to the secrets file.
    """

    secrets_file: str = ""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True


class LocalSecretsManager(BaseSecretsManager):
    """Class for ZenML local file-based secret manager."""

    @property
    def config(self) -> LocalSecretsManagerConfig:
        """Returns the `LocalSecretsManagerConfig` config.

        Returns:
            The configuration.
        """
        return cast(LocalSecretsManagerConfig, self._config)

    @property
    def secrets_file(self) -> str:
        """Gets the secrets file path.

        If the secrets file was not provided in the config by the user, this
        will return the default secrets file path based on the component ID.

        Returns:
            The secrets file path.
        """
        if self.config.secrets_file:
            return self.config.secrets_file
        return self.get_default_secret_store_path(self.id)

    @staticmethod
    def get_default_secret_store_path(id_: "UUID") -> str:
        """Get the path to the secret store.

        Args:
            id_: The ID of the secret store.

        Returns:
            The path to the secret store.
        """
        return os.path.join(
            GlobalConfiguration().local_stores_path,
            str(id_),
            LOCAL_SECRETS_FILENAME,
        )

    @property
    def local_path(self) -> str:
        """Path to the local directory where the secrets are stored.

        Returns:
            The path to the local directory where the secrets are stored.
        """
        return str(Path(self.secrets_file).parent)

    def _create_secrets_file__if_not_exists(self) -> None:
        """Makes sure the secrets yaml file exists."""
        create_file_if_not_exists(self.secrets_file)

    def _verify_secret_key_exists(self, secret_name: str) -> bool:
        """Checks if a secret key exists.

        Args:
            secret_name: The name of the secret key.

        Returns:
            True if the secret key exists, False otherwise.
        """
        self._create_secrets_file__if_not_exists()
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        try:
            return secret_name in secrets_store_items
        except TypeError:
            return False

    def _get_all_secrets(self) -> Dict[str, Dict[str, str]]:
        """Gets all secrets.

        Returns:
            A dictionary containing all secrets.
        """
        self._create_secrets_file__if_not_exists()
        return yaml_utils.read_yaml(self.secrets_file) or {}

    def register_secret(self, secret: "BaseSecretSchema") -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.

        Raises:
            SecretExistsError: If the secret already exists.
        """
        self._create_secrets_file__if_not_exists()

        if self._verify_secret_key_exists(secret_name=secret.name):
            raise SecretExistsError(f"Secret `{secret.name}` already exists.")
        encoded_secret = encode_secret(secret)

        secrets_store_items = self._get_all_secrets()
        secrets_store_items[secret.name] = encoded_secret
        yaml_utils.append_yaml(self.secrets_file, secrets_store_items)

    def get_secret(self, secret_name: str) -> "BaseSecretSchema":
        """Gets a specific secret.

        Args:
            secret_name: The name of the secret.

        Returns:
            The secret.

        Raises:
            KeyError: If the secret does not exist.
        """
        self._create_secrets_file__if_not_exists()

        secret_store_items = self._get_all_secrets()
        if not self._verify_secret_key_exists(secret_name=secret_name):
            raise KeyError(f"Secret `{secret_name}` does not exists.")
        secret_dict = secret_store_items[secret_name]

        decoded_secret_dict, zenml_schema_name = decode_secret_dict(secret_dict)
        decoded_secret_dict["name"] = secret_name

        secret_schema = SecretSchemaClassRegistry.get_class(
            secret_schema=zenml_schema_name
        )
        return secret_schema(**decoded_secret_dict)

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        Returns:
            A list of all secret keys.
        """
        self._create_secrets_file__if_not_exists()

        secrets_store_items = self._get_all_secrets()
        return list(secrets_store_items.keys())

    def update_secret(self, secret: "BaseSecretSchema") -> None:
        """Update an existing secret.

        Args:
            secret: The secret to update.

        Raises:
            KeyError: If the secret does not exist.
        """
        self._create_secrets_file__if_not_exists()

        if not self._verify_secret_key_exists(secret_name=secret.name):
            raise KeyError(f"Secret `{secret.name}` did not exist.")
        encoded_secret = encode_secret(secret)

        secrets_store_items = self._get_all_secrets()
        secrets_store_items[secret.name] = encoded_secret
        yaml_utils.append_yaml(self.secrets_file, secrets_store_items)

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: The name of the secret to delete.

        Raises:
            KeyError: If the secret does not exist.
        """
        self._create_secrets_file__if_not_exists()

        if not self._verify_secret_key_exists(secret_name=secret_name):
            raise KeyError(f"Secret `{secret_name}` does not exists.")
        secrets_store_items = self._get_all_secrets()

        try:
            secrets_store_items.pop(secret_name)
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        except KeyError:
            error(f"Secret {secret_name} does not exist.")

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
        self._create_secrets_file__if_not_exists()
        remove(self.secrets_file)


class LocalSecretsManagerFlavor(BaseSecretsManagerFlavor):
    """Class for the `LocalSecretsManagerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "local"

    @property
    def config_class(self) -> Type[LocalSecretsManagerConfig]:
        """The config class for this flavor.

        Returns:
            The config class for this flavor.
        """
        return LocalSecretsManagerConfig

    @property
    def implementation_class(self) -> Type["LocalSecretsManager"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return LocalSecretsManager
