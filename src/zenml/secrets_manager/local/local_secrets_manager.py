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
from typing import Dict, List

from zenml.enums import SecretsManagerFlavor
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager


class LocalSecretsManager(BaseSecretsManager):
    """Base class for all ZenML secret managers."""

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor."""
        return SecretsManagerFlavor.LOCAL

    @property
    def create_secret(self) -> SecretsManagerFlavor:
        """Create secret."""
        raise NotImplementedError

    @property
    def get_secret_by_key(self) -> Dict[str, str]:
        """Get secret."""
        raise NotImplementedError

    @property
    def get_all_secret_keys(self) -> List[str]:
        """Get secret."""
        raise NotImplementedError

    @property
    def update_secret_by_key(self) -> None:
        """Update existing secret."""
        raise NotImplementedError

    @property
    def delete_secret_by_key(self) -> None:
        """Delete existing secret."""
        raise NotImplementedError
