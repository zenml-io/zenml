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
from typing import Any, ClassVar, Dict, List
from uuid import UUID

from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StackComponentType
from zenml.models.base_models import ShareableProjectScopedDomainModel
from zenml.models.component_model import ComponentModel
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)
from zenml.models.project_models import ProjectModel
from zenml.models.user_management_models import UserModel
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


class StackModel(ShareableProjectScopedDomainModel, AnalyticsTrackedModelMixin):
    """Domain Model describing the Stack."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "project",
        "user",
        "is_shared",
    ]

    name: str = Field(
        title="The name of the stack.", max_length=MODEL_NAME_FIELD_MAX_LENGTH
    )
    description: str = Field(
        default="",
        title="The description of the stack",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )
    components: Dict[StackComponentType, List[UUID]] = Field(
        title=(
            "A mapping of stack component types to the id's of"
            "instances of components of this type."
        )
    )

    class Config:
        """Example of a json-serialized instance."""

        schema_extra = {
            "example": {
                "id": "cbc7d4fd-8c88-49dd-ab12-d998e4fafe22",
                "name": "default",
                "description": "",
                "components": {
                    "artifact_store": ["55a32b96-7995-4622-8474-12e7c94f3054"],
                    "orchestrator": ["67441c8b-e4e7-439b-bad3-e5883659d387"],
                },
                "is_shared": "False",
                "project": "c5600721-8432-436d-ac59-a47aec6dec0f",
                "user": "ae1fd828-fb3b-48e8-a31a-f3ecb3cdb294",
                "created": "2022-09-15T11:43:29.994722",
                "updated": "2022-09-15T11:43:29.994722",
            }
        }

    @property
    def is_valid(self) -> bool:
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
        """Create a hydrated version of the stack model.

        Returns:
            A hydrated version of the stack model.
        """
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
            created=self.created,
            updated=self.updated,
        )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the stack components to the stack analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata.update({ct: c[0] for ct, c in self.components.items()})
        return metadata


class HydratedStackModel(StackModel):
    """Stack model with Components, User and Project fully hydrated."""

    components: Dict[StackComponentType, List[ComponentModel]] = Field(  # type: ignore[assignment]
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )
    project: ProjectModel = Field(title="The project that contains this stack.")  # type: ignore[assignment]
    user: UserModel = Field(  # type: ignore[assignment]
        title="The user that created this stack.",
    )

    class Config:
        """Example of a json-serialized instance."""

        schema_extra = {
            "example": {
                "id": "cbc7d4fd-8c88-49dd-ab12-d998e4fafe22",
                "name": "default",
                "description": "",
                "components": {
                    "artifact_store": [
                        {
                            "id": "55a32b96-7995-4622-8474-12e7c94f3054",
                            "name": "default",
                            "type": "artifact_store",
                            "flavor": "local",
                            "configuration": {
                                "path": "../zenml/local_stores/default_local_store"
                            },
                            "user": "ae1fd828-fb3b-48e8-a31a-f3ecb3cdb294",
                            "is_shared": "False",
                            "project": "c5600721-8432-436d-ac59-a47aec6dec0f",
                            "created": "2022-09-15T11:43:29.987627",
                            "updated": "2022-09-15T11:43:29.987627",
                        }
                    ],
                    "orchestrator": [
                        {
                            "id": "67441c8b-e4e7-439b-bad3-e5883659d387",
                            "name": "default",
                            "type": "orchestrator",
                            "flavor": "local",
                            "configuration": {},
                            "user": "ae1fd828-fb3b-48e8-a31a-f3ecb3cdb294",
                            "is_shared": "False",
                            "project": "c5600721-8432-436d-ac59-a47aec6dec0f",
                            "created": "2022-09-15T11:43:29.987627",
                            "updated": "2022-09-15T11:43:29.987627",
                        }
                    ],
                },
                "is_shared": "False",
                "project": {
                    "id": "c5600721-8432-436d-ac59-a47aec6dec0f",
                    "name": "default",
                    "description": "",
                    "created": "2022-09-15T11:43:29.987627",
                    "updated": "2022-09-15T11:43:29.987627",
                },
                "user": {
                    "id": "ae1fd828-fb3b-48e8-a31a-f3ecb3cdb294",
                    "name": "default",
                    "full_name": "",
                    "email": "",
                    "active": "True",
                    "created": "2022-09-15T11:43:29.987627",
                    "updated": "2022-09-15T11:43:29.987627",
                },
                "created": "2022-09-15T11:43:29.987627",
                "updated": "2022-09-15T11:43:29.987627",
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
            component_dict.pop("created")  # Not needed in the yaml repr
            component_dict.pop("updated")  # Not needed in the yaml repr
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
