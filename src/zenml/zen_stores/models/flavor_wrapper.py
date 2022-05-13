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
from zenml.utils.source_utils import (
    load_source_path_class,
    validate_flavor_source,
)


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
