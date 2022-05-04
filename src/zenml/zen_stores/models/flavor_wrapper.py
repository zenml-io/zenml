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
from typing import Optional, Type

from pydantic import BaseModel

from zenml.enums import StackComponentType
from zenml.stack.stack_component import StackComponent
from zenml.utils.source_utils import load_source_path_class


def validate_flavor_source(
    source: str, component_type: StackComponentType
) -> Type[StackComponent]:
    """Utility function to import a StackComponent class from a given source
    and validate its type.

    Args:
        source: source path of the implementation
        component_type: the type of the stack component

    Raises:
        ValueError: If ZenML can not find the given module path
        TypeError: If the given module path does not point to a subclass of a
            StackComponent which has the right component type.
    """
    try:
        stack_component_class = load_source_path_class(source)
    except (ValueError, AttributeError, ImportError):
        raise ValueError(
            f"ZenML can not import the source '{source}' of the given module."
        )

    if not issubclass(stack_component_class, StackComponent):
        raise TypeError(
            f"The source '{source}' does not point to a subclass of the ZenML"
            f"StackComponent."
        )

    if stack_component_class.TYPE != component_type:  # noqa
        raise TypeError(
            f"The source points to a {stack_component_class.TYPE}, not a "  # noqa
            f"{component_type}."
        )

    return stack_component_class  # noqa


class FlavorWrapper(BaseModel):
    """Network serializable wrapper representing the custom implementation of
    a stack component flavor."""

    name: str
    type: StackComponentType
    source: str
    integration: Optional[str]

    @property
    def reachable(self) -> bool:
        """Property to which indicates whether ZenML can import the module
        within the source."""
        from zenml.integrations.registry import integration_registry

        if self.integration:
            if self.integration == "built-in":
                return True
            else:
                return integration_registry.is_installed(self.integration)

        else:
            try:
                validate_flavor_source(
                    source=self.source, component_type=self.type
                )
                return True
            except (AssertionError, ModuleNotFoundError, ImportError):
                pass

            return False

    @classmethod
    def from_flavor(cls, flavor: Type[StackComponent]) -> "FlavorWrapper":
        """Creates a FlavorWrapper from a flavor class.

        Args:
            flavor: the class which defines the flavor
        """
        return FlavorWrapper(
            name=flavor.FLAVOR,
            type=flavor.TYPE,
            source=flavor.__module__ + "." + flavor.__name__,
        )

    def to_flavor(self) -> Type[StackComponent]:
        """Imports and returns the class of the flavor."""
        try:
            return load_source_path_class(source=self.source)  # noqa
        except (ModuleNotFoundError, ImportError, NotImplementedError):
            if self.integration:
                raise ImportError(
                    f"The {self.type} flavor '{self.name}' is "
                    f"a part of ZenML's '{self.integration}' "
                    f"integration, which is currently not installed on your "
                    f"system. You can install it by executing: 'zenml "
                    f"integration install {self.integration}'."
                )
            else:
                raise ImportError(
                    f"The {self.type} that you are trying to register has "
                    f"a custom flavor '{self.name}'. In order to "
                    f"register it, ZenML needs to be able to import the flavor "
                    f"through its source which is defined as: "
                    f"{self.source}. Unfortunately, this is not "
                    f"possible due to the current set of available modules/"
                    f"working directory. Please make sure that this execution "
                    f"is carried out in an environment where this source "
                    f"is reachable as a module."
                )
