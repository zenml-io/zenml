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
"""Azure secrets manager flavor."""

import re
from typing import TYPE_CHECKING, ClassVar, Optional, Type

from zenml.integrations.azure import AZURE_SECRETS_MANAGER_FLAVOR
from zenml.secrets_managers import (
    BaseSecretsManagerConfig,
    BaseSecretsManagerFlavor,
)
from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope

if TYPE_CHECKING:
    from zenml.integrations.azure.secrets_managers import AzureSecretsManager


def validate_azure_secret_name_or_namespace(
    name: str,
    scope: SecretsManagerScope,
) -> None:
    """Validate a secret name or namespace.

    Azure secret names must contain only alphanumeric characters and the
    character `-`.

    Given that we also save secret names and namespaces as labels, we are
    also limited by the 256 maximum size limitation that Azure imposes on
    label values. An arbitrary length of 100 characters is used here for
    the maximum size for the secret name and namespace.

    Args:
        name: the secret name or namespace
        scope: the current scope

    Raises:
        ValueError: if the secret name or namespace is invalid
    """
    if scope == SecretsManagerScope.NONE:
        # to preserve backwards compatibility, we don't validate the
        # secret name for unscoped secrets.
        return

    if not re.fullmatch(r"[0-9a-zA-Z-]+", name):
        raise ValueError(
            f"Invalid secret name or namespace '{name}'. Must contain "
            f"only alphanumeric characters and the character -."
        )

    if len(name) > 100:
        raise ValueError(
            f"Invalid secret name or namespace '{name}'. The length is "
            f"limited to maximum 100 characters."
        )


class AzureSecretsManagerConfig(BaseSecretsManagerConfig):
    """Configuration for the Azure Secrets Manager.

    Attributes:
        key_vault_name: Name of an Azure Key Vault that this secrets manager
            will use to store secrets.
    """

    SUPPORTS_SCOPING: ClassVar[bool] = True

    key_vault_name: str

    @classmethod
    def _validate_scope(
        cls,
        scope: SecretsManagerScope,
        namespace: Optional[str],
    ) -> None:
        """Validate the scope and namespace value.

        Args:
            scope: Scope value.
            namespace: Optional namespace value.
        """
        if namespace:
            validate_azure_secret_name_or_namespace(namespace, scope)


class AzureSecretsManagerFlavor(BaseSecretsManagerFlavor):
    """Class for the `AzureSecretsManagerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AZURE_SECRETS_MANAGER_FLAVOR

    @property
    def config_class(self) -> Type[AzureSecretsManagerConfig]:
        """Returns AzureSecretsManagerConfig config class.

        Returns:
            The config class.
        """
        return AzureSecretsManagerConfig

    @property
    def implementation_class(self) -> Type["AzureSecretsManager"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.azure.secrets_managers import (
            AzureSecretsManager,
        )

        return AzureSecretsManager
