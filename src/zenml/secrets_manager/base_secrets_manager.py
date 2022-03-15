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
from typing import Dict, List

from pydantic import BaseModel

from zenml.enums import SecretsManagerFlavor


class BaseSecretsManager(BaseModel, ABC):
    """Base class for all ZenML secret managers."""

    @property
    @abstractmethod
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""

    @property
    @abstractmethod
    def create_secret(self) -> SecretsManagerFlavor:
        """Create secret."""

    @property
    @abstractmethod
    def get_secret_by_key(self) -> Dict[str, str]:
        """Get secret."""

    @property
    @abstractmethod
    def get_all_secret_keys(self) -> List[str]:
        """Get secret."""

    @property
    @abstractmethod
    def update_secret_by_key(self) -> None:
        """Update existing secret."""

    @property
    @abstractmethod
    def delete_secret_by_key(self) -> None:
        """Delete existing secret."""
