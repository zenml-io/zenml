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
"""Model definitions for stack."""

import json
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from zenml.enums import StackComponentType
from zenml.models.component_model import ComponentModel
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


class StackModel(AnalyticsTrackedModelMixin):
    """Network Serializable Model describing the Stack.

    name, description, components and is_shared can be specified explicitly by
    the user through the user interface.

    project, owner, created_at are added implicitly within domain logic

    id is set when the database entry is created
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "project_id",
        "owner",
        "is_shared",
    ]

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
    project_id: Optional[UUID] = Field(
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
        """Pydantic config."""

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
                "project_id": "5e4286b5-51f4-4286-b1f8-b0143e9a27ce",
                "owner": "8d0acbc3-c51a-452c-bda3-e1b5469f79fd",
                "created_at": "2022-08-12T07:12:45.931Z",
            }
        }

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the stack components to the stack analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata.update(
            {ct: c.flavor_name for ct, c in self.components.items()}
        )
        return metadata

    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.

        Returns:
            True if the stack is valid, False otherwise.
        """
        # TODO: [server] the Model should validate if the stack configuration
        #  is valid in theory
        if (
            StackComponentType.ARTIFACT_STORE
            and StackComponentType.ORCHESTRATOR in self.components.keys()
        ):
            return True
        else:
            return False

    def to_yaml(self) -> Dict[str, Any]:
        """Create yaml representation of the Stack Model.

        Returns:
            The yaml representation of the Stack Model.
        """
        component_data = {}
        for component_type, component in self.components.items():
            component_dict = json.loads(component.json())
            component_dict.pop("project_id")  # Not needed in the yaml repr
            component_dict.pop("created_at")  # Not needed in the yaml repr
            component_data[component_type.value] = component_dict

        # write zenml version and stack dict to YAML
        yaml_data = {
            "stack_name": self.name,
            "components": component_data,
        }

        return yaml_data
