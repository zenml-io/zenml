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

from zenml.console import console
from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.io.utils import get_global_config_directory
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

LOCAL_SQLITE_FILENAME = "local_sql_secret_store.db"
LOCAL_SQLITE_URL = f"sqlite:///{os.path.join(get_global_config_directory(),LOCAL_SQLITE_FILENAME)}"


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
    component_flavor=SecretsManagerFlavor.LOCAL_SQLITE,
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
        return SecretsManagerFlavor.LOCAL_SQLITE

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    def register_secret(self, secret: BaseSecretSchema) -> None:

        console.print(f"THIS REALLY WORKED {secret}!")
        # raise NotImplementedError

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        raise NotImplementedError

    def get_all_secret_keys(self) -> List[str]:
        raise NotImplementedError

    def update_secret(self, secret: BaseSecretSchema) -> None:
        raise NotImplementedError

    def delete_secret(self, secret_name: str) -> None:
        raise NotImplementedError

    def delete_all_secrets(self, force: bool = False) -> None:
        raise NotImplementedError

    def get_value_by_key(self, key: str, secret_name: str) -> Optional[str]:
        raise NotImplementedError
