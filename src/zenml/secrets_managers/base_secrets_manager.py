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
"""Base class for ZenML secrets managers."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import root_validator

from zenml.enums import StackComponentType
from zenml.secret.base_secret import BaseSecretSchema
from zenml.stack import StackComponent
from zenml.utils.enum_utils import StrEnum


class SecretsManagerScope(StrEnum):
    """Secrets Manager scope enum."""

    NONE = "none"
    GLOBAL = "global"
    COMPONENT = "component"
    NAMESPACE = "namespace"


class BaseSecretsManager(StackComponent, ABC):
    """Base class for all ZenML secrets managers.

    Attributes:
        scope: The Secrets Manager scope determines how secrets are visible and
            shared across different Secrets Manager instances:

            * global: secrets are shared across all Secrets Manager instances
            that connect to the same backend and have a global scope.
            * component: secrets are not shared outside this Secrets Manager
            instance.
            * namespace: secrets are shared only by Secrets Manager instances
            that connect to the same backend *and* have the same `namespace`
            value configured.
            * none: only used to preserve backwards compatibility with
            previous Secrets Manager instances that do not yet understand the
            concept of secrets scoping.
        namespace: Optional namespace to use with a `namespace` scoped Secrets
            Manager.
    """

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.SECRETS_MANAGER
    FLAVOR: ClassVar[str]

    scope: SecretsManagerScope = SecretsManagerScope.COMPONENT
    namespace: Optional[str] = None

    @root_validator(pre=True)
    def scope_initializer(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Pydantic root_validator for the scope.

        This root validator is used for backwards compatibility purposes. It
        ensures that existing Secrets Managers continue to use no scope for
        secrets while new instances default to using the component scope.

        Args:
            values: Values passed to the object constructor

        Returns:
            Values passed to the object constructor
        """
        if "uuid" not in values or "scope" in values:
            # this is a new Secrets Manager instance or the scope has been
            # explicitly set; just use the new default behavior
            return values

        # for existing Secrets Manager instances, continue to use no scope for
        # secrets
        values["scope"] = SecretsManagerScope.NONE
        return values

    @root_validator
    def namespace_initializer(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Pydantic root validator for the namespace.

        For a namespace scoped Secret Manager, the namespace is required.

        Args:
            values: Values passed to the object constructor

        Returns:
            Values passed to the object constructor

        Raises:
            ValueError: If a namespace is not configured for a namespace scoped
                Secret Manager.
        """
        if values.get(
            "scope"
        ) == SecretsManagerScope.NAMESPACE and not values.get("namespace"):
            raise ValueError(
                "A `namespace` value is required for a namespace scoped "
                "Secrets Manager."
            )
        return values

    @abstractmethod
    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        The implementation should throw a `SecretExistsError` exception if the
        secret already exists.

        Args:
            secret: The secret to register.
        """

    @abstractmethod
    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        The implementation should throw a `KeyError` exception if the
        secret doesn't exist.

        Args:
            secret_name: The name of the secret to get.
        """

    @abstractmethod
    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys."""

    @abstractmethod
    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        The implementation should throw a `KeyError` exception if the
        secret doesn't exist.

        Args:
            secret: The secret to update.
        """

    @abstractmethod
    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        The implementation should throw a `KeyError` exception if the
        secret doesn't exist.

        Args:
            secret_name: The name of the secret to delete.
        """

    @abstractmethod
    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
