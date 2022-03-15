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
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from pydantic import BaseModel

from zenml.enums import SecretsManagerFlavor, StackComponentType


class BaseSecretsManager(BaseModel, ABC):
    """Base class for all ZenML secrets managers."""

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.SECRETS_MANAGER

    @property
    @abstractmethod
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""

    @property
    @abstractmethod
    def create_secret(self, name: str, secret_value: str) -> None:
        """Create secret."""

    @property
    @abstractmethod
    def get_secret_by_key(self, name: str) -> Optional[str]:
        """Get secret, given a name passed in to identify it."""

    @property
    @abstractmethod
    def get_all_secret_keys(self) -> List[Optional[Dict[str, str]]]:
        """Get all secret keys."""

    @property
    @abstractmethod
    def update_secret_by_key(self, name: str, secret_value: str) -> None:
        """Update existing secret."""

    @property
    @abstractmethod
    def delete_secret_by_key(self, name: str) -> None:
        """Delete existing secret."""
