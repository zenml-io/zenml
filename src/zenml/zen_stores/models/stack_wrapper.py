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
"""Stack wrapper implementation."""

from typing import List, Optional
from uuid import UUID

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

        Returns:
            a StackWrapper
        """
        return cls(
            name=stack.name,
            components=[
                ComponentWrapper.from_component(component)
                for t, component in stack.components.items()
            ],
        )

    def to_stack(self) -> Stack:
        """Creates the corresponding Stack instance from the wrapper.

        Returns:
            the corresponding Stack instance
        """
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
        """Returns the component of the given type.

        Args:
            component_type: the type of the component to return

        Returns:
            the component of the given type or None if not found
        """
        for component_wrapper in self.components:
            if component_wrapper.type == component_type:
                return component_wrapper

        return None


class StoreAssociation(BaseModel):
    """Model for the association between an artifact store and a metadata store.

    Args:
        artifact_store_uuid: The UUID of the artifact store.
        metadata_store_uuid: The UUID of the metadata store.
    """

    artifact_store_uuid: UUID
    metadata_store_uuid: UUID
