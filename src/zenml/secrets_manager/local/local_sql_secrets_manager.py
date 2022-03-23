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

# sourcery skip: avoid-builtin-shadow

import base64
import os
from typing import Any, Dict, List, Optional

from sqlmodel import Field, SQLModel, create_engine

from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

LOCAL_SQL_SECRETS_FILENAME = "local_sql_secret_store.db"
LOCAL_SQLITE_URL = f"sqlite:///{os.path.join(get_global_config_directory(),LOCAL_SQL_SECRETS_FILENAME)}"


class SecretSet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    set_name: str


class Secret(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    secret_key: str
    secret_value: str
    secret_set: Optional[int] = Field(default=None, foreign_key="secretset.id")


def initialize_secret_store_db() -> None:
    """Create the secret store database if it doesn't already exist."""
    engine = create_engine(LOCAL_SQLITE_URL)
    SQLModel.metadata.create_all(engine)


def encode_string(string: str) -> str:
    encoded_bytes = base64.b64encode(string.encode("utf-8"))
    return str(encoded_bytes, "utf-8")


def decode_string(secret: str) -> str:
    decoded_bytes = base64.b64decode(secret)
    return str(decoded_bytes, "utf-8")


@register_stack_component_class(
    component_type=StackComponentType.SECRETS_MANAGER,
    component_flavor=SecretsManagerFlavor.LOCAL_SQL,
)
class LocalSqlSecretsManager(BaseSecretsManager):
    """Class for ZenML SQLite secret manager."""

    supports_local_execution: bool = True
    supports_remote_execution: bool = False

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        initialize_secret_store_db()

    def _get_engine(self) -> Any:
        return create_engine(LOCAL_SQLITE_URL)

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""
        return SecretsManagerFlavor.LOCAL_SQL

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    def _verify_set_key_exists(self, set_key: str) -> bool:
        pass
        # secrets_store_items = yaml_utils.read_yaml(self.secrets_file)
        # try:
        #     return set_key in secrets_store_items
        # except TypeError:
        #     return False

    def _get_all_secret_sets(self) -> Dict[str, Dict[str, str]]:
        pass
        # return yaml_utils.read_yaml(self.secrets_file) or {}

    def _verify_secret_key_exists(self, set_key: str, secret_key: str) -> bool:
        pass
        # with Session(self._get_engine()) as session:
        #     statement = select(Secret)
        #     secrets_store_items = session.exec(statement)
        #     # TODO [HIGH] : FIX THIS
        #     try:
        #         return secret_key in secrets_store_items.get(set_key)
        #     except TypeError:
        #         return False

    def _get_secrets_within_set(self, set_key: str) -> Dict[str, str]:
        pass
        # return yaml_utils.read_yaml(self.secrets_file).get(set_key) or {}

    def register_secret(
        self,
        secret_set_name: str,
        secret_set: BaseSecretSet,
    ) -> None:
        pass
        # """Register secret."""
        # if self._verify_set_key_exists(secret_set_name):
        #     raise KeyError(f"Secret set `{secret_set_name}` already exists.")
        # encoded_secret_set = secret_set.__dict__
        # for k in encoded_secret_set:
        #     encoded_secret_set[k] = encode_string(encoded_secret_set[k])
        # secrets_store_items = self._get_all_secret_sets()
        # secrets_store_items[secret_set_name] = encoded_secret_set
        # yaml_utils.append_yaml(self.secrets_file, secrets_store_items)

    def get_secret_by_key(
        self, secret_set_name: str
    ) -> Optional[Dict[str, str]]:
        pass
        # """Get secret set, given a name passed in to identify it."""
        # secret_sets_store_items = self._get_all_secret_sets()
        # if self._verify_set_key_exists(secret_set_name):
        #     return secret_sets_store_items[secret_set_name]
        # else:
        #     raise KeyError(f"Secret set `{secret_set_name}` does not exists.")

    def get_all_secret_sets_keys(self) -> List[Optional[str]]:
        pass
        # """Get all secret sets keys."""
        # secrets_store_items = self._get_all_secret_sets()
        # return list(secrets_store_items.keys())

    def update_secret_set_by_key(
        self,
        secret_set_name: str,
        secret_set: Dict[str, str],
    ) -> None:
        pass
        # """Update Existing secret set, given a name passed in to identify it"""
        # if not self._verify_set_key_exists(secret_set_name):
        #     raise KeyError(f"Secret `{secret_set_name}` does not exists.")
        # # Get all secret sets and update the one we want to update
        # encoded_secret_set = secret_set.__dict__
        # for k in encoded_secret_set:
        #     encoded_secret_set[k] = encode_string(encoded_secret_set[k])

        # secrets_store_items = self._get_all_secret_sets(secret_set)
        # secrets_store_items[secret_set_name] = secret_set
        # yaml_utils.write_yaml(self.secrets_file, secrets_store_items)

    def delete_secret_set_by_key(self, secret_set_name: str) -> None:
        pass
        # """Delete Existing secret set, given a name passed in to identify it."""
        # if not self._verify_set_key_exists(secret_set_name):
        #     raise KeyError(f"Secret `{secret_set_name}` does not exists.")
        # # Get all secret sets and remove the one we want to delete
        # secrets_store_items = self._get_all_secret_sets()
        # try:
        #     secrets_store_items.pop(secret_set_name)
        #     yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        # except KeyError:
        #     error(f"Secret Set {secret_set_name} does not exist.")

    def register_secret(
        self, name: str, secret_value: str, secret_set_name: str
    ) -> None:
        pass
        # """Register secret."""
        # if not self._verify_secret_key_exists(name, secret_set_name):
        #     encoded_secret = encode_string(secret_value)
        #     secrets_store_items = self._get_all_secret_sets()
        #     secrets_store_items[secret_set_name].update({name: encoded_secret})
        #     yaml_utils.append_yaml(self.secrets_file, secrets_store_items)
        # else:
        #     raise KeyError(f"Secret `{name}` already exists.")

    def get_secret_by_key(
        self, name: str, secret_set_name: str
    ) -> Optional[str]:
        pass
        # """Get secret, given a name passed in to identify it."""
        # secrets_store_items = self._get_all_secret_sets()
        # if self._verify_secret_key_exists(name, secret_set_name):
        #     secrets_set_items = secrets_store_items[secret_set_name]
        #     return decode_string(secrets_set_items[name])
        # else:
        #     raise KeyError(f"Secret `{name}` does not exist.")

    def get_all_secrets(self) -> List[Secret]:
        pass
        # """Get all secrets."""
        # with Session(self._get_engine()) as session:
        #     statement = select(Secret)
        #     secrets_store_items = session.exec(statement)
        #     return List(secrets_store_items)

    def get_all_secret_keys(self, secret_set_name: str) -> List[Optional[str]]:
        pass
        # """Get all secret keys for a given secret key."""
        # secrets_store_items = self._get_secrets_within_set(secret_set_name)
        # return list(secrets_store_items.keys())

    def update_secret_by_key(
        self, name: str, secret_value: str, secret_set: str
    ) -> None:
        pass
        # """Update existing secret."""
        # secrets_store_items = self._get_all_secret_sets()
        # if self._verify_secret_key_exists(name, secret_set):
        #     encoded_secret = encode_string(secret_value)
        #     secrets_store_items[secret_set][name] = encoded_secret
        #     yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        # else:
        #     raise KeyError(f"Secret `{name}` does not exist.")

    def delete_secret_by_key(self, name: str, secret_set: str) -> None:
        pass
        # """Delete existing secret."""
        # secrets_store_items = self._get_all_secret_sets()
        # if self._verify_secret_key_exists(name, secret_set):
        #     try:
        #         secrets_store_items[secret_set].pop(name)
        #         yaml_utils.write_yaml(self.secrets_file, secrets_store_items)
        #     except KeyError:
        #         error(f"Secret {name} does not exist.")
        # else:
        #     raise KeyError(f"Secret `{name}` does not exist.")
