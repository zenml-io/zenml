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
import os
import uuid
from pathlib import Path
from typing import Any, ClassVar, Dict, List

from pydantic import root_validator

from zenml.cli.utils import error
from zenml.constants import LOCAL_SECRETS_FILENAME, LOCAL_STORES_DIRECTORY_NAME
from zenml.exceptions import SecretExistsError
from zenml.io.fileio import remove
from zenml.io.utils import (
    create_file_if_not_exists,
    get_global_config_directory,
)
from zenml.logger import get_logger
from zenml.secret import SecretSchemaClassRegistry
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.utils import yaml_utils
from zenml.utils.secrets_manager_utils import decode_secret_dict, encode_secret

logger = get_logger(__name__)


class LocalSecretsManager(BaseSecretsManager):
    """Class for ZenML local file-based secret manager."""

    secrets_file: str = ""

    # Class configuration
    FLAVOR: ClassVar[str] = "local"

    @root_validator(skip_on_failure=True)
    def set_secrets_file(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Sets the secrets_file attribute value according to the component
        UUID."""
        if values.get("secrets_file"):
            return values

        # not likely to happen, due to Pydantic validation, but mypy complains
        assert "uuid" in values

        values["secrets_file"] = cls.get_secret_store_path(values["uuid"])
        return values

    @staticmethod
    def get_secret_store_path(uuid: uuid.UUID) -> str:
        """Get the path to the secret store.

        Args:
            uuid: The UUID of the secret store.

        Returns:
            The path to the secret store."""
        return os.path.join(
            get_global_config_directory(),
            LOCAL_STORES_DIRECTORY_NAME,
            str(uuid),
            LOCAL_SECRETS_FILENAME,
        )

    @property
    def local_path(self) -> str:
        """Path to the local directory where the secrets are stored."""
        return str(Path(self.secrets_file).parent)

    def _create_secrets_file__if_not_exists(self) -> None:
        """Makes sure the secrets yaml file exists"""
        create_file_if_not_exists(self.secrets_file)

    def _verify_secret_key_exists(self, secret_name: str) -> bool:
        """Checks if a secret key exists.

        Args:
            secret_name: The name of the secret key.

        Returns:
            True if the secret key exists, False otherwise."""
        self._create_secrets_file__if_not_exists()
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        try:
            return secret_name in secrets_store_items
        except TypeError:
            return False

    def _get_all_secrets(self) -> Dict[str, Dict[str, str]]:
        self._create_secrets_file__if_not_exists()
        return yaml_utils.read_yaml(self.secrets_file) or {}

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.

        Raises:
            KeyError: If the secret already exists."""
        self._create_secrets_file__if_not_exists()

        if self._verify_secret_key_exists(secret_name=secret.name):
            raise SecretExistsError(f"Secret `{secret.name}` already exists.")
        encoded_secret = encode_secret(secret)

        secrets_store_items = self._get_all_secrets()
        secrets_store_items[secret.name] = encoded_secret
        yaml_utils.append_yaml(self.secrets_file, secrets_store_items)

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets a specific secret.

        Args:
            secret_name: The name of the secret.

        Returns:
            The secret.

        Raises:
            KeyError: If the secret does not exist."""
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
            A list of all secret keys."""
        self._create_secrets_file__if_not_exists()

        secrets_store_items = self._get_all_secrets()
        return list(secrets_store_items.keys())

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: The secret to update.

        Raises:
            KeyError: If the secret does not exist."""
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
            KeyError: If the secret does not exist."""
        self._create_secrets_file__if_not_exists()

        if not self._verify_secret_key_exists(secret_name=secret_name):
            raise KeyError(f"Secret `{secret_name}` does not exists.")
        secrets_store_items = self._get_all_secrets()

        try:
            secrets_store_items.pop(secret_name)
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        except KeyError:
            error(f"Secret {secret_name} does not exist.")

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: If True, delete all secrets.

        Raises:
            ValueError: If force is False."""
        self._create_secrets_file__if_not_exists()

        if not force:
            raise ValueError(
                "This operation will delete all secrets. "
                "To confirm, please pass `--yes`."
            )
        remove(self.secrets_file)
