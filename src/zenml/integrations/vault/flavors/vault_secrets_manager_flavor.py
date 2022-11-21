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
"""HashiCorp Vault secrets manager flavor."""

import re
from typing import TYPE_CHECKING, ClassVar, Optional, Type

from zenml.integrations.vault import VAULT_SECRETS_MANAGER_FLAVOR
from zenml.secrets_managers import (
    BaseSecretsManagerConfig,
    BaseSecretsManagerFlavor,
)
from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope

if TYPE_CHECKING:
    from zenml.integrations.vault.secrets_manager import VaultSecretsManager


def validate_vault_secret_name_or_namespace(name: str) -> None:
    """Validate a secret name or namespace.

    For compatibility across secret managers the secret names should contain
    only alphanumeric characters and the characters /_+=.@-. The `/`
    character is only used internally to delimit scopes.

    Args:
        name: the secret name or namespace

    Raises:
        ValueError: if the secret name or namespace is invalid
    """
    if not re.fullmatch(r"[a-zA-Z0-9_+=\.@\-]*", name):
        raise ValueError(
            f"Invalid secret name or namespace '{name}'. Must contain "
            f"only alphanumeric characters and the characters _+=.@-."
        )


class VaultSecretsManagerConfig(BaseSecretsManagerConfig):
    """Configuration for the Vault Secrets Manager.

    Attributes:
        url: The url of the Vault server.
        token: The token to use to authenticate with Vault.
        cert: The path to the certificate to use to authenticate with Vault.
        verify: Whether to verify the certificate or not.
        mount_point: The mount point of the secrets manager.
    """

    SUPPORTS_SCOPING: ClassVar[bool] = True

    url: str
    token: str
    mount_point: str
    cert: Optional[str]  # TODO: unused
    verify: Optional[str]  # TODO: unused

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
            validate_vault_secret_name_or_namespace(namespace)


class VaultSecretsManagerFlavor(BaseSecretsManagerFlavor):
    """Class for the `VaultSecretsManagerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return VAULT_SECRETS_MANAGER_FLAVOR

    @property
    def config_class(self) -> Type[VaultSecretsManagerConfig]:
        """Returns `VaultSecretsManagerConfig` config class.

        Returns:
                The config class.
        """
        return VaultSecretsManagerConfig

    @property
    def implementation_class(self) -> Type["VaultSecretsManager"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.vault.secrets_manager import VaultSecretsManager

        return VaultSecretsManager
