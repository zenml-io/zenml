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
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.enums import StackComponentType


class FlavorSchema(SQLModel, table=True):
    """SQL Model for flavors."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)

    name: str

    # project_id - redundant since repository has this
    repository_id: UUID = Field(foreign_key="coderepositoryschema.id")
    created_by: UUID = Field(foreign_key="userschema.id")

    type: StackComponentType
    source: str
    git_sha: str
    integration: str

    created_at: datetime = Field(default_factory=datetime.now)
