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
from zenml.secret_sets.base_secret_set import BaseSecretSet
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.utils import yaml_utils

logger = get_logger(__name__)

LOCAL_SECRETS_FILENAME = "secrets.yaml"


def encode_string(string: str) -> str:
    encoded_bytes = base64.b64encode(string.encode("utf-8"))
    return str(encoded_bytes, "utf-8")


def decode_string(secret: str) -> str:
    decoded_bytes = base64.b64decode(secret)
    return str(decoded_bytes, "utf-8")


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

    def _verify_set_key_exists(self, set_key: str) -> bool:
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        try:
            return set_key in secrets_store_items
        except TypeError:
            return False

    def _verify_secret_key_exists(self, secret_key: str, set_key: str) -> bool:
        secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        try:
            return secret_key in secrets_store_items.get(set_key)
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

    def register_secret_set(
        self,
        secret_set_name: str,
        secret_set: BaseSecretSet,
    ) -> None:
        """Register secret."""
        if not self._verify_set_key_exists(secret_set_name):
            encoded_secret_set = secret_set.__dict__
            for k in encoded_secret_set:
                encoded_secret_set[k] = encode_string(encoded_secret_set[k])
            secrets_store_items = self._get_all_secret_sets()
            secrets_store_items[secret_set_name] = encoded_secret_set
            yaml_utils.append_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret set `{secret_set_name}` already exists.")

    def get_secret_set_by_key(self, secret_set_name: str) -> Dict[str, str]:
        """Get secret set, given a name passed in to identify it."""
        secret_sets_store_items = self._get_all_secret_sets()
        if self._verify_set_key_exists(secret_set_name):
            return secret_sets_store_items[secret_set_name]
        else:
            raise KeyError(f"Secret set `{secret_set_name}` does not exists.")

    def get_all_secret_sets_keys(self) -> List[Optional[str]]:
        """Get all secret sets keys."""
        secrets_store_items = self._get_all_secret_sets()
        return list(secrets_store_items.keys())

    def update_secret_set_by_key(
        self,
        secret_set_name: str,
        secret_set: BaseSecretSet,
    ) -> None:
        """Update Existing secret set, given a name passed in to identify it."""
        if self._verify_set_key_exists(secret_set_name):
            """Get all secret sets and update the one we want to update"""
            encoded_secret_set = secret_set.__dict__
            for k in encoded_secret_set:
                encoded_secret_set[k] = encode_string(encoded_secret_set[k])

            secrets_store_items = self._get_all_secret_sets()
            secrets_store_items[secret_set_name] = encoded_secret_set
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret `{secret_set_name}` does not exists.")

    def delete_secret_set_by_key(self, secret_set_name: str) -> None:
        """Delete Existing secret set, given a name passed in to identify it."""
        if self._verify_set_key_exists(secret_set_name):
            """Get all secret sets and remove the one we want to delete"""
            secrets_store_items = self._get_all_secret_sets()
            try:
                secrets_store_items.pop(secret_set_name)
                yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
            except KeyError:
                error(f"Secret Set {secret_set_name} does not exist.")
        else:
            raise KeyError(f"Secret `{secret_set_name}` does not exists.")

    def register_secret(
        self, name: str, secret_value: str, secret_set: str
    ) -> None:
        """Register secret."""
        if not self._verify_secret_key_exists(name, secret_set):
            encoded_secret = encode_string(secret_value)
            secrets_store_items = self._get_all_secret_sets()
            secrets_store_items[secret_set].update({name: encoded_secret})
            yaml_utils.append_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret `{name}` already exists.")

    def get_secret_by_key(self, name: str, secret_set: str) -> Optional[str]:
        """Get secret, given a name passed in to identify it."""
        secrets_store_items = self._get_all_secret_sets()
        if self._verify_secret_key_exists(name, secret_set):
            secrets_set_items = secrets_store_items[secret_set]
            return decode_string(secrets_set_items[name])
        else:
            raise KeyError(f"Secret `{name}` does not exist.")

    def get_all_secret_keys(self, secret_set: str) -> List[Optional[str]]:
        """Get all secret keys."""
        secrets_store_items = self._get_secrets_within_set(secret_set)
        return list(secrets_store_items.keys())

    def update_secret_by_key(
        self, name: str, secret_value: str, secret_set: str
    ) -> None:
        """Update existing secret."""
        secrets_store_items = self._get_all_secret_sets()
        if self._verify_secret_key_exists(name, secret_set):
            encoded_secret = encode_string(secret_value)
            secrets_store_items[secret_set][name] = encoded_secret
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret `{name}` does not exist.")

    def delete_secret_by_key(self, name: str, secret_set: str) -> None:
        """Delete existing secret."""
        secrets_store_items = self._get_all_secret_sets()
        try:
            secrets_store_items[secret_set].pop(name)
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        except KeyError:
            error(f"Secret {name} does not exist.")
