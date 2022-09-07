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
"""SQL Model Implementations for Code Repositories."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.models import CodeRepositoryModel


class CodeRepositorySchema(SQLModel, table=True):
    """SQL Model for code repositories."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str
    project_id: UUID = Field(foreign_key="projectschema.id")
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_create_model(
        cls, model: CodeRepositoryModel, project_id: UUID
    ) -> "CodeRepositorySchema":
        return cls(name=model.name, project_id=project_id)

    def from_update_model(
        self, model: CodeRepositoryModel
    ) -> "CodeRepositorySchema":
        self.name = model.name
        return self

    def to_model(self) -> CodeRepositoryModel:
        return CodeRepositoryModel(
            id=self.id,
            name=self.name,
            project_id=self.project_id,
            created_at=self.created_at,
        )
