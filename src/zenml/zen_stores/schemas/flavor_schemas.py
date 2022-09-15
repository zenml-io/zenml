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
"""SQL Model Implementations for Flavors."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.enums import StackComponentType
from zenml.models import FlavorModel


class FlavorSchema(SQLModel, table=True):
    """SQL Model for flavors."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)

    name: str

    type: StackComponentType
    source: str
    integration: Optional[str] = Field(default="")

    config_schema: str

    project_id: UUID = Field(foreign_key="projectschema.id")
    user_id: UUID = Field(foreign_key="userschema.id")
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_create_model(
        cls,
        flavor: FlavorModel,
        user_id: UUID,
        project_id: UUID,
    ):
        return cls(
            name=flavor.name,
            type=flavor.type,
            source=flavor.source,
            config_schema=flavor.config_schema,
            integration=flavor.integration,
            user_id=user_id,
            project_id=project_id,
        )

    def from_update_model(
        self,
        flavor: FlavorModel,
    ):
        return flavor

    def to_model(self):
        return FlavorModel(
            id=self.id,
            name=self.name,
            type=self.type,
            source=self.source,
            config_schema=self.config_schema,
            integration=self.integration,
            user_id=self.user_id,
            project_id=self.project_id,
            created_at=self.created_at,
        )
