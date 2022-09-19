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
from uuid import UUID

from sqlmodel import Field, SQLModel

from zenml.enums import StackComponentType
from zenml.models import FlavorModel


class FlavorSchema(SQLModel, table=True):
    """SQL Model for flavors."""

    id: UUID = Field(primary_key=True)
    type: StackComponentType
    source: str
    name: str
    integration: Optional[str] = Field(default="")
    config_schema: str

    project: UUID = Field(foreign_key="projectschema.id")
    user: UUID = Field(foreign_key="userschema.id")

    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_create_model(cls, flavor: FlavorModel) -> "FlavorSchema":
        return cls(
            id=flavor.id,
            name=flavor.name,
            type=flavor.type,
            source=flavor.source,
            config_schema=flavor.config_schema,
            integration=flavor.integration,
            user=flavor.user,
            project=flavor.project,
        )

    def from_update_model(
        self,
        flavor: FlavorModel,
    ) -> "FlavorSchema":
        return self

    def to_model(self) -> FlavorModel:
        return FlavorModel(
            id=self.id,
            name=self.name,
            type=self.type,
            source=self.source,
            config_schema=self.config_schema,
            integration=self.integration,
            user=self.user,
            project=self.project,
            created=self.created,
            updated=self.updated,
        )
