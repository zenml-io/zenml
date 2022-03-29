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
from typing import Callable, ClassVar, Dict, Type, TypeVar, Union

from zenml.enums import SecretSchemaType
from zenml.integrations.aws.secret_schemas import AWSSecretSchema
from zenml.logger import get_logger
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
        secret_schema: SecretSchemaType,
        secret: Type[BaseSecretSchema],
    ) -> None:
        """Registers a SecretSchema class.

        Args:
            secret_schema: The flavor of the SecretSchema class to register.
            secret: The SecretSchema class to register.
        """
        secret_schema_value = secret_schema.value
        flavors = cls.secret_schema_classes
        if secret_schema_value in flavors:
            logger.warning(
                "Overwriting previously registered stack component class `%s` "
                "for type '%s' and flavor '%s'.",
                flavors[secret_schema_value].__class__.__name__,
                secret_schema_value,
            )

        flavors[secret_schema_value] = secret
        logger.debug(
            "Registered stack component class for type '%s' and flavor '%s'.",
            secret_schema_value,
        )

    @classmethod
    def get_class(
        cls,
        secret_schema: Union[SecretSchemaType, str],
    ) -> Type[BaseSecretSchema]:
        """Returns the SecretSchema class for the given type and flavor.

        Args:
            secret_schema: The flavor of the SecretSchema class to return.

        Returns:
            The SecretSchema class for the given type and flavor.

        Raises:
            KeyError: If no SecretSchema class is registered for the given type
                and flavor.
        """
        if isinstance(secret_schema, SecretSchemaType):
            secret_schema = secret_schema.value

        available_schemas = cls.secret_schema_classes
        try:
            return available_schemas[secret_schema]
        except KeyError:
            # TODO [ENG-722]: Probably remove this exception catch. Doesn't apply
            # to SecretSchema
            # The SecretSchema might be part of an integration
            # -> Activate the integrations and try again
            from zenml.integrations.registry import integration_registry

            integration_registry.activate_integrations()

            try:
                return available_schemas[secret_schema]
            except KeyError:
                raise KeyError(
                    f"No SecretSchema class found for SecretSet  "
                    f"of flavor {secret_schema}. Registered flavors are:"
                    f" {set(available_schemas)}."
                ) from None


C = TypeVar("C", bound=BaseSecretSchema)


def register_secret_schema_class(
    secret_schema: SecretSchemaType,
) -> Callable[[Type[C]], Type[C]]:
    """Parametrized decorator function to register SecretSchema classes.

    Args:
        secret_schema: The flavor of the SecretSchema class to register.

    Returns:
        A decorator function that registers and returns the decorated SecretSchema class.
    """

    def decorator_function(cls: Type[C]) -> Type[C]:
        """Registers the SecretSchema class and returns it unmodified.

        Args:
            cls: The SecretSchema class to register.

        Returns:
            The (unmodified) SecretSchema class to register.
        """
        SecretSchemaClassRegistry.register_class(
            secret_schema=secret_schema,
            secret=cls,
        )
        return cls

    return decorator_function


SecretSchemaClassRegistry.register_class(
    SecretSchemaType.AWS,
    AWSSecretSchema,
)
SecretSchemaClassRegistry.register_class(
    SecretSchemaType.ARBITRARY,
    ArbitrarySecretSchema,
)
