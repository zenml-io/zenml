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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    cast,
)

from pydantic import root_validator

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig
from zenml.utils import secret_utils
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from zenml.secret.base_secret import BaseSecretSchema

logger = get_logger(__name__)

ZENML_SCOPE_PATH_PREFIX = "zenml"
ZENML_SECRET_NAME_LABEL = "zenml_secret_name"
ZENML_DEFAULT_SECRET_SCOPE_PATH_SEPARATOR = "/"


class SecretsManagerScope(StrEnum):
    """Secrets Manager scope enum."""

    NONE = "none"
    GLOBAL = "global"
    COMPONENT = "component"
    NAMESPACE = "namespace"


class BaseSecretsManagerConfig(StackComponentConfig):
    """Base configuration for secrets managers.

    Attributes:
        scope: The scope of the secrets manager.
        namespace: The namespace of the secrets manager.
    """

    SUPPORTS_SCOPING: ClassVar[bool] = False
    scope: SecretsManagerScope = SecretsManagerScope.COMPONENT
    namespace: Optional[str] = None

    def __init__(self, **kwargs: Any) -> None:
        """Ensures that no attributes are specified as a secret reference.

        Args:
            **kwargs: Arguments to initialize this secrets manager.

        Raises:
            ValueError: If any of the secrets manager attributes are specified
                as a secret reference.
        """
        for key, value in kwargs.items():
            if secret_utils.is_secret_reference(value):
                raise ValueError(
                    "Using secret references to specify attributes on a "
                    "secrets manager is not allowed. Please specify the "
                    f"real value for the attribute {key}."
                )

        super().__init__(**kwargs)

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

        Raises:
            ValueError: If the scope value is not valid.
        """
        scope = values.get("scope")

        if scope:
            # fail if the user tries to explicitly use a scope with a
            # Secrets Manager that doesn't support scoping
            if scope != SecretsManagerScope.NONE and not cls.SUPPORTS_SCOPING:
                raise ValueError(
                    "This Secrets Manager does not support "
                    "scoping. You can only use a `none` scope value."
                )
        elif not cls.SUPPORTS_SCOPING:
            # disable scoping by default for Secrets Managers that don't
            # support scoping
            values["scope"] = SecretsManagerScope.NONE

        # warn if the user tries to explicitly disable scoping for a
        # Secrets Manager that does support scoping
        if scope == SecretsManagerScope.NONE and cls.SUPPORTS_SCOPING:
            logger.warning(
                "Unscoped support for this Secrets "
                "Manager is deprecated and will be removed in a future "
                "release. You should use the `global` scope instead."
            )

        return values

    @root_validator
    def namespace_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
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
        scope = cast(SecretsManagerScope, values.get("scope"))
        if scope == SecretsManagerScope.NAMESPACE and not values.get(
            "namespace"
        ):
            raise ValueError(
                "A `namespace` value is required for a namespace scoped "
                "Secrets Manager."
            )
        cls._validate_scope(scope, values.get("namespace"))
        return values

    @classmethod
    def _validate_scope(
        cls,
        scope: SecretsManagerScope,
        namespace: Optional[str],
    ) -> None:
        """Validate the scope and namespace value.

        Subclasses should override this method to implement their own scope
        and namespace validation logic (e.g. raise an exception if a scope is
        not supported or if a namespace has an invalid value).

        Args:
            scope: Scope value.
            namespace: Namespace value.
        """
        ...


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
            old Secrets Manager instances that do not yet understand the
            concept of secrets scoping. Will be deprecated and removed in
            future versions.
        namespace: Optional namespace to use with a `namespace` scoped Secrets
            Manager.
    """

    @property
    def config(self) -> BaseSecretsManagerConfig:
        """Returns the `BaseSecretsManagerConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseSecretsManagerConfig, self._config)

    def _get_scope_path(self) -> List[str]:
        """Get the secret path for the current scope.

        This utility method can be used with Secrets Managers that can map
        the concept of a scope to a hierarchical path.

        Returns:
            the secret scope path
        """
        if self.config.scope == SecretsManagerScope.NONE:
            return []

        path = [ZENML_SCOPE_PATH_PREFIX, self.config.scope]
        if self.config.scope == SecretsManagerScope.COMPONENT:
            path.append(str(self.id))
        elif (
            self.config.scope == SecretsManagerScope.NAMESPACE
            and self.config.namespace
        ):
            path.append(self.config.namespace)

        return path

    def _get_scoped_secret_path(self, secret_name: str) -> List[str]:
        """Convert a ZenML secret name into a scoped secret path.

        This utility method can be used with Secrets Managers that can map
        the concept of a scope to a hierarchical path.

        Args:
            secret_name: the name of the secret

        Returns:
            The scoped secret path
        """
        path = self._get_scope_path()
        path.append(secret_name)
        return path

    def _get_secret_name_from_path(
        self, secret_path: List[str]
    ) -> Optional[str]:
        """Extract the name of a ZenML secret from a scoped secret path.

        This utility method can be used with Secrets Managers that can map
        the concept of a scope to a hierarchical path.

        Args:
            secret_path: the full scoped secret path including the secret name

        Returns:
            The ZenML secret name or None, if the input secret path does not
            belong to the current scope.
        """
        if not len(secret_path):
            return None
        secret_name = secret_path[-1]
        secret_path = secret_path[:-1]
        if not secret_name or secret_path != self._get_scope_path():
            # secret name is not in the current scope
            return None

        return secret_name

    def _get_scoped_secret_name_prefix(
        self,
        separator: str = ZENML_DEFAULT_SECRET_SCOPE_PATH_SEPARATOR,
    ) -> str:
        """Convert the ZenML secret scope into a scoped secret name prefix.

        This utility method can be used with Secrets Managers that can map
        the concept of a scope to a hierarchical path to compose a scoped
        secret name prefix from the scope path.

        Args:
            separator: the path separator to use when constructing a scoped
                secret prefix from a scope path

        Returns:
            The scoped secret name prefix
        """
        return separator.join(self._get_scope_path()) + separator

    def _get_scoped_secret_name(
        self,
        name: str,
        separator: str = ZENML_DEFAULT_SECRET_SCOPE_PATH_SEPARATOR,
    ) -> str:
        """Convert a ZenML secret name into a scoped secret name.

        This utility method can be used with Secrets Managers that can map
        the concept of a scope to a hierarchical path to compose a scoped
        secret name that includes the scope path from a ZenML secret name.

        Args:
            name: the name of the secret
            separator: the path separator to use when constructing a scoped
                secret name from a scope path

        Returns:
            The scoped secret name
        """
        return separator.join(self._get_scoped_secret_path(name))

    def _get_unscoped_secret_name(
        self,
        name: str,
        separator: str = ZENML_DEFAULT_SECRET_SCOPE_PATH_SEPARATOR,
    ) -> Optional[str]:
        """Extract the name of a ZenML secret from a scoped secret name.

        This utility method can be used with Secrets Managers that can map
        the concept of a scope to a hierarchical path to extract the original
        ZenML secret name from a scoped secret name that includes the scope
        path.

        Args:
            name: the name of the scoped secret
            separator: the path separator to use when constructing a scoped
                secret name from a scope path

        Returns:
            The ZenML secret name or None, if the input secret name does not
            belong to the current scope.
        """
        return self._get_secret_name_from_path(name.split(separator))

    def _get_secret_scope_metadata(
        self, secret_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Get a dictionary with metadata uniquely identifying one or more scoped secrets.

        This utility method can be used with Secrets Managers that can
        associate metadata (e.g. tags, labels) with a secret. The scope related
        metadata can be used as a filter criteria when running queries against
        the backend to retrieve all the secrets within the current scope or
        to retrieve a named secret within the current scope (if the
        `secret_name` is supplied).

        Args:
            secret_name: Optional secret name for which to get the scope
                metadata.

        Returns:
            Dictionary with scope metadata information uniquely identifying the
            secret.
        """
        if self.config.scope == SecretsManagerScope.NONE:
            # unscoped secrets do not have tags, for backwards compatibility
            # purposes
            return {}

        metadata = {
            "zenml_scope": self.config.scope.value,
        }
        if secret_name:
            metadata[ZENML_SECRET_NAME_LABEL] = secret_name
        if (
            self.config.scope == SecretsManagerScope.NAMESPACE
            and self.config.namespace
        ):
            metadata["zenml_namespace"] = self.config.namespace
        if self.config.scope == SecretsManagerScope.COMPONENT:
            metadata["zenml_component_uuid"] = str(self.id)

        return metadata

    def _get_secret_metadata(
        self, secret: "BaseSecretSchema"
    ) -> Dict[str, str]:
        """Get a dictionary with metadata describing a secret.

        This is utility method can be used with Secrets Managers that can
        associate metadata (e.g. tags, labels) with a secret. The metadata
        can be used to relay more information about the secret in the Secrets
        Manager backend. Part of the metadata can also be used as a filter
        criteria when running queries against the backend to retrieve all the
        secrets within the current scope or to retrieve a named secret (see
        `_get_secret_scope_metadata`).

        Args:
            secret: The secret for which to get the metadata.

        Returns:
            Dictionary with metadata information describing the secret.
        """
        if self.config.scope == SecretsManagerScope.NONE:
            # unscoped secrets do not have tags, for backwards compatibility
            # purposes
            return {}

        scope_metadata = self._get_secret_scope_metadata(secret.name)
        # include additional metadata not necessarily related to the secret
        # scope
        scope_metadata.update(
            {
                "zenml_component_name": self.name,
                "zenml_component_uuid": str(self.id),
                "zenml_secret_schema": secret.TYPE,
            }
        )

        return scope_metadata

    @abstractmethod
    def register_secret(self, secret: "BaseSecretSchema") -> None:
        """Registers a new secret.

        The implementation should throw a `SecretExistsError` exception if the
        secret already exists.

        Args:
            secret: The secret to register.
        """

    @abstractmethod
    def get_secret(self, secret_name: str) -> "BaseSecretSchema":
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
    def update_secret(self, secret: "BaseSecretSchema") -> None:
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


class BaseSecretsManagerFlavor(Flavor):
    """Class for the `BaseSecretsManagerFlavor`."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.SECRETS_MANAGER

    @property
    def config_class(self) -> Type[BaseSecretsManagerConfig]:
        """Returns the config class.

        Returns:
            The config class.
        """
        return BaseSecretsManagerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseSecretsManager"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
