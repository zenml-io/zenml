#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Initialization for the Vault Secrets Manager integration.

The Vault secrets manager integration submodule provides a way 
to access the HashiCorp Vault secrets manager from within your ZenML 
pipeline runs.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import VAULT
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

VAULT_SECRETS_MANAGER_FLAVOR = "vault"


class VaultSecretsManagerIntegration(Integration):
    """Definition of HashiCorp Vault integration with ZenML."""

    NAME = VAULT
    REQUIREMENTS = ["hvac>=0.11.2"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Vault integration.

        Returns:
            List of stack component flavors.
        """
        return [
            FlavorWrapper(
                name=VAULT_SECRETS_MANAGER_FLAVOR,
                source="zenml.integrations.vault.secrets_manager.VaultSecretsManager",
                type=StackComponentType.SECRETS_MANAGER,
                integration=cls.NAME,
            )
        ]


VaultSecretsManagerIntegration.check_installation()
