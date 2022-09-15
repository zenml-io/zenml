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
"""Model definition for stack components."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.models.project_models import ProjectModel
from zenml.models.user_management_models import UserModel
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

if TYPE_CHECKING:
    from zenml.stack import StackComponent

logger = get_logger(__name__)


class ComponentModel(AnalyticsTrackedModelMixin):
    """Network Serializable Model describing the StackComponent.

    name, type, flavor and config are specified explicitly by the user
    through the user interface. These values + owner can be updated.

    owner, created_by, created_at are added implicitly set within domain logic

    id is set when the database entry is created
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "type",
        "flavor",
        "project",
        "user",
        "is_shared",
    ]

    id: UUID = Field(
        default_factory=uuid4,
        title="The unique id of the stack component.",
    )
    name: str = Field(
        title="The name of the stack component.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(
        title="The type of the stack component.",
    )
    flavor: str = Field(
        title="The flavor of the stack component.",
    )
    configuration: Dict[
        str, Any
    ] = Field(  # Json representation of the configuration
        title="The stack component configuration.",
    )
    project: UUID = Field(
        title="The project that contains this stack component."
    )
    user: UUID = Field(
        title="The id of the user that created this stack component.",
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this component is shared.",
    )

    creation_date: Optional[datetime] = Field(
        default=None,
        title="The time at which the component was registered.",
    )

    class Config:
        """Example of a json-serialized instance."""

        schema_extra = {
            "example": {
                "id": "5e4286b5-51f4-4286-b1f8-b0143e9a27ce",
                "name": "vertex_prd_orchestrator",
                "type": "orchestrator",
                "flavor": "vertex",
                "configuration": {"location": "europe-west3"},
                "project": "da63ad01-9117-4082-8a99-557ca5a7d324",
                "user": "43d73159-04fe-418b-b604-b769dd5b771b",
                "created_at": "2022-08-12T07:12:44.931Z",
            }
        }

    def to_hydrated_model(self) -> "HydratedComponentModel":
        """Converts the `ComponentModel` into a `HydratedComponentModel`.

        Returns:
            The hydrated component model.
        """
        zen_store = GlobalConfiguration().zen_store

        project = zen_store.get_project(self.project)
        user = zen_store.get_user(self.user)

        return HydratedComponentModel(
            id=self.id,
            name=self.name,
            type=self.type,
            flavor=self.flavor,
            configuration=self.configuration,
            project=project,
            user=user,
            is_shared=self.is_shared,
            creation_date=self.creation_date,
        )

    @classmethod
    def from_component(cls, component: "StackComponent") -> "ComponentModel":
        """Creates a ComponentModel from an instance of a stack component.

        Args:
            component: the instance of a StackComponent

        Returns:
            a ComponentModel
        """
        from zenml.repository import Repository

        repo = Repository()

        return cls(
            type=component.TYPE,
            flavor=component.FLAVOR,
            name=component.name,
            id=component.uuid,
            project=repo.active_project.id,
            user=repo.active_user.id,
            configuration=json.loads(component.json()),
        )

    def to_component(self) -> "StackComponent":
        """Converts the ComponentModel into an instance of a stack component.

        Returns:
            a StackComponent
        """
        from zenml.repository import Repository

        flavor = Repository(skip_repository_check=True).get_flavor(  # type: ignore[call-arg]
            name=self.flavor, component_type=self.type
        )

        config = self.configuration
        config["uuid"] = self.id
        config["name"] = self.name
        return flavor.parse_obj(config)


class HydratedComponentModel(ComponentModel):
    """Component model with User and Project fully hydrated."""

    project: ProjectModel = Field(title="The project that contains this stack.")
    user: UserModel = Field(
        title="The user that created this stack.",
    )

    class Config:
        """Example of a json-serialized instance."""

        schema_extra = {
            "example": {
                "id": "5e4286b5-51f4-4286-b1f8-b0143e9a27ce",
                "name": "vertex_prd_orchestrator",
                "type": "orchestrator",
                "flavor": "vertex",
                "configuration": {"location": "europe-west3"},
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
                "created_at": "2022-08-12T07:12:44.931Z",
            }
        }
