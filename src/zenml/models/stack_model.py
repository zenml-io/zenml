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
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.component_models import ComponentModel
from zenml.stack import Stack


class StackModel(BaseModel):
    """Network Serializable Model describing the Stack.

    name, description, components and is_shared can be specified explicitly by
    the user through the user interface.

    project, owner, created_at are added implicitly within domain logic

    id is set when the database entry is created
    """

    id: Optional[UUID]
    name: str
    description: Optional[str] = Field(
        default=None, title="The description of the stack", max_length=300
    )
    components: Dict[StackComponentType, ComponentModel] = Field(
        title="A mapping of stack component types to the id's of"
        "instances of components of this type."
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this stack is shared.",
    )
    project: Optional[str] = Field(
        default=None, title="The project that contains this stack."
    )
    owner: Optional[UUID] = Field(
        default=None,
        title="The id of the user, that created this stack.",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        title="The time at which the stack was registered.",
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "8d0acbc3-c51a-452c-bda3-e1b5469f79fd",
                "name": "prd_stack",
                "description": "A stack for running pipelines in production.",
                "components": {
                    "alerter": "d3bbe238-d42a-42a2-b6a6-2319c4fbe5c9",
                    "orchestrator": "5e4286b5-51f4-4286-b1f8-b0143e9a27ce",
                },
                "is_shared": "True",
                "project": "cat_project",
                "owner": "8d0acbc3-c51a-452c-bda3-e1b5469f79fd",
                "created_at": "2022-08-12T07:12:45.931Z",
            }
        }

    @classmethod
    def from_stack(cls, stack: Stack) -> "StackModel":
        """Creates a StackModel from an actual Stack instance.

        Args:
            stack: the instance of a Stack

        Returns:
            a StackModel
        """
        return cls(
            name=stack.name,
            components={
                type_: ComponentModel.from_component(component)
                for type_, component in stack.components.items()
            },
        )

    def to_stack(self) -> Stack:
        """Creates the corresponding Stack instance from the StackModel.

        Returns:
            the corresponding Stack instance
        """
        stack_components = {
            type_: model.to_component() 
            for type_, model in self.components.items()
        }
        return Stack.from_components(
            name=self.name, components=stack_components
        )

    def get_component_wrapper(
        self, component_type: StackComponentType
    ) -> Optional[ComponentModel]:
        """Returns the component of the given type.

        Args:
            component_type: the type of the component to return

        Returns:
            the component of the given type or None if not found
        """
        from zenml.repository import Repository

        if component_type in self.components.keys():
            repo = Repository()
            component_model = repo.zen_store.get_stack_component(
                component_type, self.components[component_type]
            )

            return component_model

        return None
