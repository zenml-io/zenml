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

from zenml.enums import SecretSetFlavor
from zenml.integrations.aws.secret_sets.aws_secret_set import AWSSecretSet
from zenml.logger import get_logger
from zenml.secret_sets.base_secret_set import BaseSecretSet
from zenml.secret_sets.defaul_secret_set import DefaultSecretSet

logger = get_logger(__name__)


class SecretSetClassRegistry:
    """Registry for stack component classes.

    All stack component classes must be registered here so they can be
    instantiated from the component type and flavor specified inside the
    ZenML repository configuration.
    """

    secret_set_classes: ClassVar[Dict[str, Type[BaseSecretSet]]] = dict()

    @classmethod
    def register_class(
        cls,
        secret_set_flavor: "SecretSetFlavor",
        secret_set: Type[BaseSecretSet],
    ) -> None:
        """Registers a stack component class.

        Args:
            secret_set_flavor: The flavor of the component class to register.
            secret_set: The component class to register.
        """
        secret_set_flavor = secret_set_flavor.value
        flavors = cls.secret_set_classes
        if secret_set_flavor in flavors:
            logger.warning(
                "Overwriting previously registered stack component class `%s` "
                "for type '%s' and flavor '%s'.",
                flavors[secret_set_flavor].__class__.__name__,
                secret_set_flavor,
            )

        flavors[secret_set_flavor] = secret_set
        logger.debug(
            "Registered stack component class for type '%s' and flavor '%s'.",
            secret_set_flavor,
        )

    @classmethod
    def get_class(
        cls,
        secret_set_flavor: Union[SecretSetFlavor, str],
    ) -> Type[BaseSecretSet]:
        """Returns the stack component class for the given type and flavor.

        Args:
            secret_set_flavor: The flavor of the component class to return.

        Raises:
            KeyError: If no component class is registered for the given type
                and flavor.
        """
        if isinstance(secret_set_flavor, SecretSetFlavor):
            secret_set_flavor = secret_set_flavor.value

        available_flavors = cls.secret_set_classes
        try:
            return available_flavors[secret_set_flavor]
        except KeyError:
            # The stack component might be part of an integration
            # -> Activate the integrations and try again
            from zenml.integrations.registry import integration_registry

            integration_registry.activate_integrations()

            try:
                return available_flavors[secret_set_flavor]
            except KeyError:
                raise KeyError(
                    f"No stack component class found for SecretSet  "
                    f"of flavor {secret_set_flavor}. Registered flavors are:"
                    f" {set(available_flavors)}."
                ) from None


C = TypeVar("C", bound=BaseSecretSet)


def register_secret_set_class(
    secret_set_flavor: SecretSetFlavor,
) -> Callable[[Type[C]], Type[C]]:
    """Parametrized decorator function to register secret set classes.

    Args:
        secret_set_flavor: The flavor of the component class to register.

    Returns:
        A decorator function that registers and returns the decorated stack
        component class.
    """

    def decorator_function(cls: Type[C]) -> Type[C]:
        """Registers the stack component class and returns it unmodified."""
        SecretSetClassRegistry.register_class(
            secret_set_flavor=secret_set_flavor,
            secret_set=cls,
        )
        return cls

    return decorator_function


SecretSetClassRegistry.register_class(
    SecretSetFlavor.AWS,
    AWSSecretSet,
)

SecretSetClassRegistry.register_class(
    SecretSetFlavor.DEFAULT,
    DefaultSecretSet,
)
