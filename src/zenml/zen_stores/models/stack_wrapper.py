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
from typing import List, Optional

from pydantic import BaseModel

from zenml.enums import StackComponentType
from zenml.stack import Stack
from zenml.zen_stores.models import ComponentWrapper


class StackWrapper(BaseModel):
    """Network Serializable Wrapper describing a Stack."""

    name: str
    components: List[ComponentWrapper]

    @classmethod
    def from_stack(cls, stack: Stack) -> "StackWrapper":
        """Creates a StackWrapper from an actual Stack instance.

        Args:
            stack: the instance of a Stack
        """
        return cls(
            name=stack.name,
            components=[
                ComponentWrapper.from_component(component)
                for t, component in stack.components.items()
            ],
        )

    def to_stack(self) -> Stack:
        """Creates the corresponding Stack instance from the wrapper."""
        stack_components = {}
        for component_wrapper in self.components:
            component_type = component_wrapper.type
            component = component_wrapper.to_component()
            stack_components[component_type] = component

        return Stack.from_components(
            name=self.name, components=stack_components
        )

    def get_component_wrapper(
        self, component_type: StackComponentType
    ) -> Optional[ComponentWrapper]:
        """Returns the component of the given type."""
        for component_wrapper in self.components:
            if component_wrapper.type == component_type:
                return component_wrapper

        return None
