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
"""Stack Models for the API endpoint definitions."""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models import StackModel
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)


class CreateStackRequest(BaseModel):
    """Stack model for create requests."""

    name: str = Field(
        title="The stack name.", max_length=MODEL_NAME_FIELD_MAX_LENGTH
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the stack",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )
    components: Dict[StackComponentType, List[UUID]] = Field(
        default=None,
        title=(
            "A mapping of stack component types to the id's of"
            "instances of components of this type."
        ),
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this stack is shared.",
    )

    def to_model(self, project: UUID, user: UUID) -> "StackModel":
        """Create a `StackModel` from this object.

        Args:
            project: Project context of the stack.
            user: User context of the stack

        Returns:
            The created `StackModel`.
        """
        return StackModel(project=project, user=user, **self.dict())

    @classmethod
    def from_model(cls, stack: StackModel) -> "CreateStackRequest":
        """Convert from a stack model."""
        return cls(**stack.dict())


class UpdateStackRequest(BaseModel):
    """Stack model for update requests."""

    name: Optional[str] = Field(
        default=None,
        title="The stack name.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The updated description of the stack",
        max_length=300,
    )
    components: Optional[Dict[StackComponentType, List[UUID]]] = Field(
        default=None,
        title=(
            "An updated mapping of stack component types to the id's of"
            "instances of components of this type."
        ),
    )
    is_shared: Optional[bool] = Field(
        default=None,
        title="Updated flag describing if this stack is shared.",
    )

    def apply_to_model(self, stack: "StackModel") -> "StackModel":
        """Update a `StackModel` from this object.

        Args:
            stack: The `StackModel` to apply the changes to.

        Returns:
            The updated `StackModel`.
        """
        for key, value in self.dict(exclude_none=True).items():
            setattr(stack, key, value)

        return stack

    @classmethod
    def from_model(cls, stack: StackModel) -> "UpdateStackRequest":
        """Convert from a `StackModel` model."""
        return cls(**stack.dict())
