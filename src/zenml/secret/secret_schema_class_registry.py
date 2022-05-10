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
from typing import ClassVar, Dict, Type, TypeVar

from zenml.logger import get_logger
from zenml.metadata_stores.mysql_secret_schema import MYSQLSecretSchema
from zenml.secret import BaseSecretSchema
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema

logger = get_logger(__name__)


class SecretSchemaClassRegistry:
    """Registry for SecretSchema classes.

    All SecretSchema classes must be registered here so they can be
    instantiated from the component type and flavor specified inside the
    ZenML repository configuration.
    """

    secret_schema_classes: ClassVar[Dict[str, Type[BaseSecretSchema]]] = dict()

    @classmethod
    def register_class(
        cls,
        secret: Type[BaseSecretSchema],
    ) -> None:
        """Registers a SecretSchema class.

        Args:
            secret: The SecretSchema class to register.
        """
        flavors = cls.secret_schema_classes
        if secret.TYPE in flavors:
            logger.warning(
                "Overwriting previously registered secret schema class `%s` "
                "for type '%s' and flavor '%s'.",
                flavors[secret.TYPE].__class__.__name__,
                secret.TYPE,
            )

        flavors[secret.TYPE] = secret
        logger.debug(
            "Registered secret schema class for type '%s' and flavor '%s'.",
            secret.__class__.__name__,
            secret.TYPE,
        )

    @classmethod
    def get_class(
        cls,
        secret_schema: str,
    ) -> Type[BaseSecretSchema]:
        """Returns the SecretSchema class for the given flavor.

        Args:
            secret_schema: The flavor of the SecretSchema class to return.

        Returns:
            The SecretSchema class for the given flavor.

        Raises:
            KeyError: If no SecretSchema class is registered for the given
                flavor.
        """
        available_schemas = cls.secret_schema_classes
        try:
            return available_schemas[secret_schema]
        except KeyError:
            # The SecretSchema might be part of an integration
            # -> Activate the integrations and try again
            from zenml.integrations.registry import integration_registry

            integration_registry.activate_integrations()

            try:
                return available_schemas[secret_schema]
            except KeyError:
                raise KeyError(
                    f"No SecretSchema class found for schema flavor "
                    f"`{secret_schema}`. Registered flavors are: "
                    f"{set(available_schemas)}. If your secret schema "
                    f"class is part of a ZenML integration, make "
                    f"sure the corresponding integration is installed by "
                    f"running `zenml integration install INTEGRATION_NAME`."
                ) from None


C = TypeVar("C", bound=BaseSecretSchema)


def register_secret_schema_class(cls: Type[C]) -> Type[C]:
    """Registers the SecretSchema class and returns it unmodified.

    Args:
        cls: The SecretSchema class to register.

    Returns:
        The (unmodified) SecretSchema class to register.
    """
    SecretSchemaClassRegistry.register_class(secret=cls)
    return cls


SecretSchemaClassRegistry.register_class(ArbitrarySecretSchema)
SecretSchemaClassRegistry.register_class(MYSQLSecretSchema)
