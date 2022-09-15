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

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models.project_models import ProjectModel
from zenml.models.user_management_models import UserModel
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

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
        title="The unique id of the component.")

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
    user: Optional[UUID] = Field(
        default=None,
        title="The id of the user that owns this component.",
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this component is shared.",
    )
    project: Optional[UUID] = Field(
        default=None, title="The project that contains this component."
    )
    creation_date: datetime = Field(
        default_factory=datetime.now,
        title="The time at which the component was registered.",
    )

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


class HydratedComponentModel(ComponentModel):
    """Component model with User and Project fully hydrated."""

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
