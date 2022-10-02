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
"""AWS secrets manager flavor."""

import re
from typing import TYPE_CHECKING, ClassVar, Optional, Type

from zenml.integrations.aws import AWS_SECRET_MANAGER_FLAVOR
from zenml.secrets_managers import (
    BaseSecretsManagerConfig,
    BaseSecretsManagerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.aws.secrets_managers import AWSSecretsManager
    from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope


def validate_aws_secret_name_or_namespace(name: str) -> None:
    """Validate a secret name or namespace.

    AWS secret names must contain only alphanumeric characters and the
    characters /_+=.@-. The `/` character is only used internally to delimit
    scopes.

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


class AWSSecretsManagerConfig(BaseSecretsManagerConfig):
    """Configuration for the AWS Secrets Manager.

    Attributes:
        region_name: The region name of the AWS Secrets Manager.
    """

    SUPPORTS_SCOPING: ClassVar[bool] = True

    region_name: str

    @classmethod
    def _validate_scope(
        cls,
        scope: "SecretsManagerScope",
        namespace: Optional[str],
    ) -> None:
        """Validate the scope and namespace value.

        Args:
            scope: Scope value.
            namespace: Optional namespace value.
        """
        if namespace:
            validate_aws_secret_name_or_namespace(namespace)


class AWSSecretsManagerFlavor(BaseSecretsManagerFlavor):
    """Class for the `AWSSecretsManagerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            Name of the flavor.
        """
        return AWS_SECRET_MANAGER_FLAVOR

    @property
    def config_class(self) -> Type[AWSSecretsManagerConfig]:
        """Config class for this flavor.

        Returns:
            Config class for this flavor.
        """
        return AWSSecretsManagerConfig

    @property
    def implementation_class(self) -> Type["AWSSecretsManager"]:
        """Implementation class.

        Returns:
            Implementation class.
        """
        from zenml.integrations.aws.secrets_managers import AWSSecretsManager

        return AWSSecretsManager
