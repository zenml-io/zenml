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
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models import ComponentModel


class CreateComponentModel(BaseModel):
    """Model used for all update operations on stacks."""

    name: str = Field(
        title="The name of the Stack Component.",
    )
    type: StackComponentType = Field(
        title="The type of the Stack Component.",
    )
    flavor: Optional[str] = Field(
        title="The flavor of the Stack Component.",
    )
    configuration: Dict[
        str, Any
    ] = Field(  # Json representation of the configuration
        title="The id of the Stack Component.",
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this component is shared.",
    )

    def to_model(self, project: UUID, user: UUID) -> "ComponentModel":
        """Applies user defined changes to this model.

        Args:
            project: Project context of the stack.
            user: User context of the stack

        Returns:
            The updated model.
        """
        return ComponentModel(project=project, user=user, **self.dict())


class UpdateComponentModel(BaseModel):
    """Model used for all update operations on stacks."""

    name: Optional[str] = Field(
        title="The name of the Stack Component.",
    )
    type: Optional[StackComponentType] = Field(
        title="The type of the Stack Component.",
    )
    flavor: Optional[str] = Field(
        title="The flavor of the Stack Component.",
    )
    configuration: Optional[Dict[str, Any]] = Field(
        title="The id of the Stack Component.",
    )  # Json representation of the configuration
    is_shared: Optional[bool] = Field(
        default=False,
        title="Flag describing if this component is shared.",
    )

    def apply_to_model(self, stack: "ComponentModel") -> "ComponentModel":
        """Applies user defined changes to this model.

        Args:
            stack: Component model the changes will be applied to

        Returns:
            The updated component model
        """
        for key, value in self.dict().items():
            if value is not None:
                setattr(stack, key, value)

        return stack
