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
from uuid import UUID, uuid4

from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StackComponentType
from zenml.models.component_models import ComponentModel
from zenml.models.project_models import ProjectModel
from zenml.models.user_management_models import UserModel
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


class StackModel(AnalyticsTrackedModelMixin):
    """Domain Model describing the Stack."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "project",
        "user",
        "is_shared",
    ]

    id: UUID = Field(default_factory=uuid4, title="The unique id of the stack.")
    name: str = Field(title="The name of the stack.")
    description: Optional[str] = Field(
        default=None, title="The description of the stack", max_length=300
    )
    components: Dict[StackComponentType, List[UUID]] = Field(
        title="A mapping of stack component types to the id's of"
        "instances of components of this type."
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this stack is shared.",
    )
    project: UUID = Field(title="The project that contains this stack.")
    user: UUID = Field(
        title="The id of the user, that created this stack.",
    )
    creation_date: datetime = Field(
        default_factory=datetime.now,
        title="The time at which the stack was registered.",
    )

    @property
    def is_valid(self):
        """Check if the stack is valid.

        Returns:
            True if the stack is valid, False otherwise.
        """
        if (
            StackComponentType.ARTIFACT_STORE
            and StackComponentType.ORCHESTRATOR in self.components.keys()
        ):
            return True
        else:
            return False

    def to_hydrated_model(self) -> "HydratedStackModel":
        zen_store = GlobalConfiguration().zen_store

        components = {}
        for comp_type, comp_id_list in self.components.items():
            components[comp_type] = [
                zen_store.get_stack_component(c_id) for c_id in comp_id_list
            ]

        project = zen_store.get_project(self.project)
        user = zen_store.get_user(self.user)

        return HydratedStackModel(
            id=self.id,
            name=self.name,
            description=self.description,
            components=components,
            project=project,
            user=user,
            is_shared=self.is_shared,
            creation_date=self.creation_date,
        )


class HydratedStackModel(StackModel):
    """Network Serializable Model describing the Stack with Components,
    User and Project fully hydrated.
    """

    components: Dict[StackComponentType, List[ComponentModel]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )
    project: ProjectModel = Field(
        default=None, title="The project that contains this stack."
    )
    user: UserModel = Field(
        default=None,
        title="The id of the user, that created this stack.",
    )

    class Config:
        """Pydantic config."""

        schema_extra = {
            "example": {
                "id": "8d0acbc3-c51a-452c-bda3-e1b5469f79fd",
                "name": "prd_stack",
                "description": "A stack for running pipelines in production.",
                "components": {
                    "alerter": [{}, {}],
                    "orchestrator": [{}],
                },
                "is_shared": "True",
                "project": {
                    "id": "da63ad01-9117-4082-8a99-557ca5a7d324",
                    "name": "default",
                    "description": "Best project.",
                    "creation_date": "2022-09-13T16:03:52.317039",
                },
                "user": {
                    "id": "43d73159-04fe-418b-b604-b769dd5b771b",
                    "name": "default",
                    "creation_date": "2022-09-13T16:03:52.329928",
                },
                "creation_date": "2022-08-12T07:12:45.931Z",
            }
        }

    def to_yaml(self) -> Dict[str, Any]:
        """Create yaml representation of the Stack Model.

        Returns:
            The yaml representation of the Stack Model.
        """
        component_data = {}
        for component_type, components_list in self.components.items():
            component_dict = json.loads(components_list[0].json())
            component_dict.pop("project")  # Not needed in the yaml repr
            component_dict.pop("creation_date")  # Not needed in the yaml repr
            component_data[component_type.value] = component_dict

        # write zenml version and stack dict to YAML
        yaml_data = {
            "stack_name": self.name,
            "components": component_data,
        }

        return yaml_data

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the stack components to the stack analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata.update({ct: c[0].flavor for ct, c in self.components.items()})
        return metadata
