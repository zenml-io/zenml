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
"""Component wrapper implementation."""

import base64
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import UUID

import yaml
from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.stack import StackComponent

logger = get_logger(__name__)


class ComponentModel(BaseModel):
    """Network Serializable Model describing the StackComponent.

    name, type, flavor and config are specified explicitly by the user
    through the user interface. These values + owner can be updated.

    owner, created_by, created_at are added implicitly set within domain logic

    id is set when the database entry is created
    """

    id: Optional[UUID] = Field(
        default=None,
        title="The id of the Stack Component.",
    )
    name: str = Field(
        title="The name of the Stack Component.",
    )
    type: StackComponentType = Field(
        title="The type of the Stack Component.",
    )
    flavor_name: Optional[str] = Field(
        title="The flavor of the Stack Component.",
    )
    configuration: str = Field(  # Json representation of the configuration
        title="The id of the Stack Component.",
    )
    owner: Optional[UUID] = Field(
        default=None,
        title="The id of the user, that owns this component.",
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this component is shared.",
    )
    project: Optional[str] = Field(
        default=None, title="The project that contains this component."
    )
    created_at: Optional[datetime] = Field(
        default=None,
        title="The time at which the component was registered.",
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "5e4286b5-51f4-4286-b1f8-b0143e9a27ce",
                "name": "vertex_prd_orchestrator",
                "type": "orchestrator",
                "flavor": "vertex",
                "config": {"location": "europe-west3"},
                "owner": "8d0acbc3-c51a-452c-bda3-e1b5469f79fd",
                "created_by": "8d0acbc3-c51a-452c-bda3-e1b5469f79fd",
                "created_at": "2022-08-12T07:12:44.931Z",
            }
        }

    @classmethod
    def from_component(cls, component: "StackComponent") -> "ComponentModel":
        """Creates a ComponentModel from an instance of a Stack Component.

        Args:
            component: the instance of a StackComponent

        Returns:
            a ComponentModel
        """
        return cls(
            type=component.TYPE,
            flavor_name=component.FLAVOR,
            name=component.name,
            id=component.uuid,
            configuration=component.json()
        )

    def to_component(self) -> "StackComponent":
        """Converts the ComponentModel into an instance of a Stack Component.

        Returns:
            a StackComponent
        """
        from zenml.repository import Repository

        flavor = Repository(skip_repository_check=True).get_flavor(  # type: ignore[call-arg]
            name=self.flavor_name, component_type=self.type
        )

        config = json.loads(self.configuration)
        config["uuid"] = self.id
        config["name"] = self.name
        return flavor.parse_obj(config)
