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
"""GCP secrets manager flavor."""

import re
from typing import TYPE_CHECKING, ClassVar, Optional, Type

from zenml.integrations.gcp import GCP_SECRETS_MANAGER_FLAVOR
from zenml.secrets_managers import (
    BaseSecretsManagerConfig,
    BaseSecretsManagerFlavor,
)
from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope

if TYPE_CHECKING:
    from zenml.integrations.gcp.secrets_manager import GCPSecretsManager


def validate_gcp_secret_name_or_namespace(name: str) -> None:
    """Validate a secret name or namespace.

    A Google secret ID is a string with a maximum length of 255 characters
    and can contain uppercase and lowercase letters, numerals, and the
    hyphen (-) and underscore (_) characters. For scoped secrets, we have to
    limit the size of the name and namespace even further to allow space for
    both in the Google secret ID.

    Given that we also save secret names and namespaces as labels, we are
    also limited by the limitation that Google imposes on label values: max
    63 characters and must only contain lowercase letters, numerals
    and the hyphen (-) and underscore (_) characters

    Args:
        name: the secret name or namespace

    Raises:
        ValueError: if the secret name or namespace is invalid
    """
    if not re.fullmatch(r"[a-z0-9_\-]+", name):
        raise ValueError(
            f"Invalid secret name or namespace '{name}'. Must contain "
            f"only lowercase alphanumeric characters and the hyphen (-) and "
            f"underscore (_) characters."
        )

    if name and len(name) > 63:
        raise ValueError(
            f"Invalid secret name or namespace '{name}'. The length is "
            f"limited to maximum 63 characters."
        )


class GCPSecretsManagerConfig(BaseSecretsManagerConfig):
    """Configuration for the GCP Secrets Manager.

    Attributes:
        project_id: This is necessary to access the correct GCP project.
            The project_id of your GCP project space that contains the Secret
            Manager.
    """

    SUPPORTS_SCOPING: ClassVar[bool] = True
    project_id: str

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
            validate_gcp_secret_name_or_namespace(namespace)


class GCPSecretsManagerFlavor(BaseSecretsManagerFlavor):
    """Class for the `GCPSecretsManagerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GCP_SECRETS_MANAGER_FLAVOR

    @property
    def config_class(self) -> Type[GCPSecretsManagerConfig]:
        """Returns GCPSecretsManagerConfig config class.

        Returns:
                The config class.
        """
        return GCPSecretsManagerConfig

    @property
    def implementation_class(self) -> Type["GCPSecretsManager"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.secrets_manager import GCPSecretsManager

        return GCPSecretsManager
