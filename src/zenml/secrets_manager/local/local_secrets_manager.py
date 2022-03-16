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
from typing import Dict, List, Optional

from zenml.cli.utils import error
from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.repository import Repository
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component import StackComponent
from zenml.utils import yaml_utils
from zenml.io.utils import get_global_config_directory
from zenml.io.fileio import create_file_if_not_exists

LOCAL_SECRETS_FILENAME = "secrets.yaml"


def encode_string(string: str) -> str:
    encodedBytes = base64.b64encode(string.encode("utf-8"))
    return str(encodedBytes, "utf-8")


def decode_string(secret: str) -> str:
    decodedBytes = base64.b64decode(secret)
    return str(decodedBytes, "utf-8")


class LocalSecretsManager(BaseSecretsManager):
    """Local class for ZenML secret manager."""

    secrets_file: str = os.path.join(
        get_global_config_directory(), LOCAL_SECRETS_FILENAME
    )
    supports_local_execution: bool = True
    supports_remote_execution: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        create_file_if_not_exists(self.secrets_file, "")

    def _verify_key_exists(self, key: str) -> bool:
        secrets_store_items = self.parse_obj(
            yaml_utils.read_yaml(self.secrets_file)
        )
        return key in secrets_store_items

    def _get_all_secrets(self) -> Dict[str, str]:
        return self.parse_obj(yaml_utils.read_yaml(self.secrets_file))

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""
        return SecretsManagerFlavor.LOCAL

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    @property
    def create_secret(self, name: str, secret_value: str) -> None:
        """Create secret."""
        encoded_secret = encode_string(secret_value)
        secrets_store_items = self._get_all_secrets()
        if not secrets_store_items[name]:
            secrets_store_items[name] = encoded_secret
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret `{name}` already exists.")

    @property
    def get_secret_by_key(self, name: str) -> Optional[str]:
        """Get secret, given a name passed in to identify it."""
        secrets_store_items = self._get_all_secrets()
        if self._verify_key_exists(name):
            return decode_string(secrets_store_items.get(name))
        else:
            raise KeyError(f"Secret `{name}` does not exist.")

    @property
    def get_all_secret_keys(self) -> List[Optional[str]]:
        """Get all secret keys."""
        secrets_store_items = self._get_all_secrets()
        return list(secrets_store_items.keys())

    @property
    def update_secret_by_key(self, name: str, secret_value: str) -> None:
        """Update existing secret."""
        secrets_store_items = self._get_all_secrets()
        if self._verify_key_exists(name):
            secrets_store_items[name] = secret_value
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        else:
            raise KeyError(f"Secret `{name}` does not exist.")

    @property
    def delete_secret_by_key(self, name: str) -> None:
        """Delete existing secret."""
        secrets_store_items = self._get_all_secrets()
        try:
            secrets_store_items.pop(name)
            yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        except KeyError:
            error(f"Secret {name} does not exist.")
