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

from zenml.enums import SecretsManagerFlavor
from zenml.secret_sets.base_secret_set import BaseSecretSet
from zenml.stack import StackComponent


class BaseSecretsManager(StackComponent, ABC):
    """Base class for all ZenML secrets managers."""

    @property
    @abstractmethod
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""

    @abstractmethod
    def register_secret_set(
        self, secret_set_name: str, secret_set: "BaseSecretSet"
    ) -> None:
        """Register secret set."""

    @abstractmethod
    def get_secret_set_by_key(self, secret_set_name: str) -> Dict[str, str]:
        """Get secret set by key."""

    @abstractmethod
    def get_all_secret_sets_keys(self) -> List[Optional[str]]:
        """Get all secret set keys."""

    @abstractmethod
    def update_secret_set_by_key(
        self, secret_set_name: str, secret_set: "BaseSecretSet"
    ) -> None:
        """Update secret set by key."""

    @abstractmethod
    def delete_secret_set_by_key(self, secret_set_name: str) -> None:
        """Delete secret set by key."""

    @abstractmethod
    def register_secret(
        self, name: str, secret_value: str, secret_set: str
    ) -> None:
        """Register secret."""

    @abstractmethod
    def get_secret_by_key(self, name: str, secret_set: str) -> Optional[str]:
        """Get secret, given a name passed in to identify it."""

    @abstractmethod
    def get_all_secret_keys(self, secret_set: str) -> List[Optional[str]]:
        """Get all secret keys."""

    @abstractmethod
    def update_secret_by_key(
        self, name: str, secret_value: str, secret_set: str
    ) -> None:
        """Update existing secret."""

    @abstractmethod
    def delete_secret_by_key(self, name: str, secret_set: str) -> None:
        """Delete existing secret."""
