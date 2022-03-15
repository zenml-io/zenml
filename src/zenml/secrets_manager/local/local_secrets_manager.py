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
from typing import Dict, List, Optional

from zenml.cli.utils import error
from zenml.enums import SecretsManagerFlavor
from zenml.repository import Repository
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component import StackComponent
from zenml.utils import yaml_utils


class LocalSecretsManager(BaseSecretsManager):
    """Base class for all ZenML secret managers."""

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""
        return SecretsManagerFlavor.LOCAL

    @property
    def create_secret(self, name: str, secret_value: str) -> None:
        """Create secret."""
        secrets_manager = Repository().active_stack.components.get(
            StackComponent.SECRETS_MANAGER
        )
        secrets_manager_config_path = secrets_manager.config_path
        secrets_store_items = self.parse_obj(
            yaml_utils.read_yaml(secrets_manager_config_path)
        )
        secrets_store_items[name] = secret_value
        yaml_utils.write_yaml(secrets_manager_config_path, secrets_store_items)

    @property
    def get_secret_by_key(self, name: str) -> Optional[str]:
        """Get secret, given a name passed in to identify it."""
        secrets_manager = Repository().active_stack.components.get(
            StackComponent.SECRETS_MANAGER
        )
        secrets_manager_config_path = secrets_manager.config_path
        secrets_store_items = self.parse_obj(
            yaml_utils.read_yaml(secrets_manager_config_path)
        )
        return secrets_store_items.get(name)

    @property
    def get_all_secret_keys(self) -> List[Optional[Dict[str, str]]]:
        """Get all secret keys."""
        secrets_manager = Repository().active_stack.components.get(
            StackComponent.SECRETS_MANAGER
        )
        secrets_manager_config_path = secrets_manager.config_path
        secrets_store_items = self.parse_obj(
            yaml_utils.read_yaml(secrets_manager_config_path)
        )
        return list(secrets_store_items)

    @property
    def update_secret_by_key(self, name: str, secret_value: str) -> None:
        """Update existing secret."""
        secrets_manager = Repository().active_stack.components.get(
            StackComponent.SECRETS_MANAGER
        )
        secrets_manager_config_path = secrets_manager.config_path
        secrets_store_items = self.parse_obj(
            yaml_utils.read_yaml(secrets_manager_config_path)
        )
        secrets_store_items[name] = secret_value
        yaml_utils.write_yaml(secrets_manager_config_path, secrets_store_items)

    @property
    def delete_secret_by_key(self, name: str) -> None:
        """Delete existing secret."""
        secrets_manager = Repository().active_stack.components.get(
            StackComponent.SECRETS_MANAGER
        )
        secrets_manager_config_path = secrets_manager.config_path
        secrets_store_items = self.parse_obj(
            yaml_utils.read_yaml(secrets_manager_config_path)
        )
        try:
            secrets_store_items.pop(name)
        except KeyError:
            error(f"Secret {name} does not exist.")
        yaml_utils.write_yaml(secrets_manager_config_path, secrets_store_items)
