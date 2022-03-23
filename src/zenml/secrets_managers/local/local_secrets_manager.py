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
from typing import Any, Dict, List, Optional

from zenml.cli.utils import error
from zenml.constants import LOCAL_SECRETS_FILENAME
from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.io.fileio import create_file_if_not_exists
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.secret import SecretSchemaClassRegistry
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.utils import yaml_utils
from zenml.utils.secrets_manager_utils import decode_secret_dict, encode_secret

logger = get_logger(__name__)


@register_stack_component_class(
    component_type=StackComponentType.SECRETS_MANAGER,
    component_flavor=SecretsManagerFlavor.LOCAL,
)
class LocalSecretsManager(BaseSecretsManager):
    """Class for ZenML local filebased secret manager."""

    secrets_file: str = os.path.join(
        get_global_config_directory(), LOCAL_SECRETS_FILENAME
    )
    supports_local_execution: bool = True
    supports_remote_execution: bool = False

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        create_file_if_not_exists(self.secrets_file)

    def _verify_secret_exists(self, set_key: str) -> bool:
        """Checks if a secret exists."""
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        return set_key in secrets_store_items

    def _verify_secret_key_exists(self, secret_name: str) -> bool:
        """Checks if a secret key exists."""
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        try:
            return secret_name in secrets_store_items
        except TypeError:
            return False

    def _get_all_secrets(self) -> Dict[str, Dict[str, str]]:
        return yaml_utils.read_yaml(self.secrets_file) or {}

    def _get_secrets_within_set(self, set_key: str) -> Dict[str, str]:
        return yaml_utils.read_yaml(self.secrets_file).get(set_key) or {}

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The local filesystem-based secrets manager flavor."""
        return SecretsManagerFlavor.LOCAL

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret."""

        if self._verify_secret_key_exists(secret_name=secret.name):
            raise KeyError(f"Secret set `{secret.name}` already exists.")
        encoded_secret = encode_secret(secret)

        secrets_store_items = self._get_all_secrets()
        secrets_store_items[secret.name] = encoded_secret
        yaml_utils.append_yaml(self.secrets_file, secrets_store_items)

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret."""
        secret_sets_store_items = self._get_all_secrets()
        if not self._verify_secret_key_exists(secret_name=secret_name):
            raise KeyError(f"Secret set `{secret_name}` does not exists.")
        secret_dict = secret_sets_store_items[secret_name]

        decoded_secret_dict, zenml_schema_name = decode_secret_dict(
            secret_dict
        )
        decoded_secret_dict["name"] = secret_name

        secret_schema = SecretSchemaClassRegistry.get_class(
            secret_schema=zenml_schema_name
        )
        return secret_schema(**decoded_secret_dict)

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys."""
        secrets_store_items = self._get_all_secrets()
        return list(secrets_store_items.keys())

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret."""
        if not self._verify_secret_key_exists(secret_name=secret.name):
            raise KeyError(f"Secret set `{secret.name}` did not exist.")
        encoded_secret = encode_secret(secret)

        secrets_store_items = self._get_all_secrets()
        secrets_store_items[secret.name] = encoded_secret
        yaml_utils.append_yaml(self.secrets_file, secrets_store_items)

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret."""
        if not self._verify_secret_key_exists(secret_name=secret_name):
            raise KeyError(f"Secret `{secret_name}` does not exists.")
        secrets_store_items = self._get_all_secrets()

        try:
            secrets_store_items.pop(secret_name)
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        except KeyError:
            error(f"Secret Set {secret_name} does not exist.")

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets."""
        raise NotImplementedError

    def get_value_by_key(self, key: str, secret_name: str) -> Optional[str]:
        """Get value for a particular key within a Secret."""
        secret = self.get_secret(secret_name)

        secret_contents = secret.content
        if key in secret_contents:
            return secret_contents[key]
        else:
            raise KeyError(
                f"Secret `{key}` does not exist in Secret `{secret_name}`."
            )
