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
"""SQL Model Implementations for MLMD Databases."""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MLMDSchema(SQLModel, table=True):
    """SQL Model for MLMD."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    project_id: UUID = Field(foreign_key="projectschema.id")
    type: str


class MLMDPropertySchema(SQLModel, table=True):
    """SQL Model for MLMD Properties."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    name: str
    mlmd_id: UUID = Field(foreign_key="mlmdschema.id")
    value: str
