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
import base64
import os
from typing import Any, Dict, List, Optional

from zenml.cli.utils import error
from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.io.fileio import create_file_if_not_exists
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.secret import SecretSchemaClassRegistry
from zenml.secret.base_secret import Secret
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.utils import yaml_utils

logger = get_logger(__name__)

LOCAL_SECRETS_FILENAME = "secrets.yaml"
ZENML_SCHEMA_NAME = "zenml_schema_name"


def encode_string(string: str) -> str:
    encoded_bytes = base64.b64encode(string.encode("utf-8"))
    return str(encoded_bytes, "utf-8")


def encode_secret(secret: Secret) -> Dict[str, str]:
    """Base64 Encode all values within a secret

    Args:
        secret: Secret containing key-value pairs
    """
    encoded_secret = dict()
    for k, v in secret.get_contents.items():
        encoded_secret[k] = encode_string(v)

    return encoded_secret


def decode_string(secret: str) -> str:
    decoded_bytes = base64.b64decode(secret)
    return str(decoded_bytes, "utf-8")


def decode_secret_dict(secret_dict: Dict[str, str]) -> Dict[str, str]:
    decoded_secret = dict()
    for k, v in secret_dict.items():
        decoded_secret[k] = decode_string(v)

    return decoded_secret


@register_stack_component_class(
    component_type=StackComponentType.SECRETS_MANAGER,
    component_flavor=SecretsManagerFlavor.LOCAL,
)
class LocalSecretsManager(BaseSecretsManager):
    """Local class for ZenML secret manager."""

    secrets_file: str = os.path.join(
        get_global_config_directory(), LOCAL_SECRETS_FILENAME
    )
    supports_local_execution: bool = True
    supports_remote_execution: bool = False

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        create_file_if_not_exists(self.secrets_file, "{default:{}}")

    def _verify_secret_exists(self, set_key: str) -> bool:
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        return set_key in secrets_store_items

    def _verify_secret_key_exists(self, secret_name: str) -> bool:
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        try:
            return secret_name in secrets_store_items
        except TypeError:
            return False

    def _get_all_secret_sets(self) -> Dict[str, Dict[str, str]]:
        return yaml_utils.read_yaml(self.secrets_file) or {}

    def _get_secrets_within_set(self, set_key: str) -> Dict[str, str]:
        return yaml_utils.read_yaml(self.secrets_file).get(set_key) or {}

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""
        return SecretsManagerFlavor.LOCAL

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    def register_secret(self, secret: Secret) -> None:
        """Register secret."""

        if not self._verify_secret_key_exists(secret_name=secret.name):
            encoded_secret = encode_secret(secret)

            secrets_store_items = self._get_all_secret_sets()
            secrets_store_items[secret.name] = encoded_secret
            yaml_utils.append_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret set `{secret.name}` already exists.")

    def get_secret(self, secret_name: str) -> Dict[str, str]:
        """Get secret set, given a name passed in to identify it."""
        secret_sets_store_items = self._get_all_secret_sets()
        if self._verify_secret_key_exists(secret_name=secret_name):
            secret_dict = secret_sets_store_items[secret_name]
            try:
                zenml_schema_name = secret_dict.pop(ZENML_SCHEMA_NAME)
            except KeyError:
                secret = Secret(
                    name=secret_name,
                    contents=decode_secret_dict(secret_dict),
                )
            else:
                secret_schema = SecretSchemaClassRegistry.get_class(
                    secret_schema=zenml_schema_name
                )
                secret = Secret(
                    name=secret_name,
                    contents=secret_schema(**decode_secret_dict(secret_dict)),
                )
            return secret
        else:
            raise KeyError(f"Secret set `{secret_name}` does not exists.")

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys."""
        secrets_store_items = self._get_all_secret_sets()
        return list(secrets_store_items.keys())

    def update_secret(self, secret: Secret) -> None:
        """Update existing secret."""
        raise NotImplementedError

    def delete_secret(self, secret_name: str) -> None:
        """Delete Existing secret set, given a name passed in to identify it."""
        if not self._verify_secret_key_exists(secret_name=secret_name):
            """Get all secret sets and remove the one we want to delete"""
            secrets_store_items = self._get_all_secret_sets()
            try:
                secrets_store_items.pop(secret_name)
                yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
            except KeyError:
                error(f"Secret Set {secret_name} does not exist.")
        else:
            raise KeyError(f"Secret `{secret_name}` does not exists.")

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete existing secret."""
        raise NotImplementedError

    def get_value_by_key(self, key: str, secret_name: str) -> Optional[str]:
        """Get value at key within secret"""
        secret = self.get_secret(secret_name)

        secret_contents = secret.contents
        if key in secret_contents:
            secret_value = secret_contents[key]
            return secret_value
        else:
            raise KeyError(
                f"Secret `{key}` does not exist in secret-set "
                f"'{secret_name}'."
            )
