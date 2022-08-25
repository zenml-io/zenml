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
from typing import TYPE_CHECKING
from uuid import UUID

import yaml
from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.stack import StackComponent

logger = get_logger(__name__)


class ComponentModel(BaseModel):
    """Serializable Configuration of a StackComponent."""

    id: UUID = Field(
        title="The id of the Stack Component.",
    )
    name: str = Field(
        title="The name of the Stack Component.",
    )
    type: StackComponentType = Field(
        title="The type of the Stack Component.",
    )
    flavor: str = Field(
        title="The flavor of the Stack Component.",
    )
    config: bytes = Field(  # b64 encoded yaml config
        title="The id of the Stack Component.",
    )
    created_by: str = Field(
        title="The id of the user, that created this component.",
    )
    created_at: str = Field(
        title="The time at which the component was registered.",
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "5e4286b5-51f4-4286-b1f8-b0143e9a27ce",
                "name": "vertex_prd_orchestrator",
                "type": "orchestrator",
                "flavor": "vertex",
                "config": b"RANDOM64STRING",
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
            flavor=component.FLAVOR,
            name=component.name,
            uuid=component.uuid,
            config=base64.b64encode(
                yaml.dump(json.loads(component.json())).encode()
            ),
        )

    def to_component(self) -> "StackComponent":
        """Converts the ComponentModel into an actual instance of a Stack Component.

        Returns:
            a StackComponent
        """
        from zenml.repository import Repository

        flavor = Repository(skip_repository_check=True).get_flavor(  # type: ignore[call-arg]
            name=self.flavor, component_type=self.type
        )

        config = yaml.safe_load(base64.b64decode(self.config).decode())

        return flavor.parse_obj(config)
