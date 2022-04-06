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
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, root_validator

from zenml.logger import get_logger

logger = get_logger(__name__)


# This probably makes more sense to be a resource?
class Operation(BaseModel):
    """Pydantic object representing an operation that requires permission.

    Attributes:
        id: Operation id.
        name: Operation name.
    """

    id: int
    name: str


class PermissionType(Enum):
    """All permission types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class Permission(BaseModel):
    """Pydantic object representing permissions on a specific resource.

    Attributes:
        operation: The operation for which the permissions are.
        types: Types of permissions.
    """

    operation: Operation
    types: Set[PermissionType]

    class Config:
        # similar to non-mutable but also makes the object hashable
        frozen = True


class Role(BaseModel):
    """Pydantic object representing a role.

    Attributes:
        id: Id of the role.
        creation_date: Date when the role was created.
        name: Name of the role.
        permissions: Set of permissions allowed by this role.
    """

    id: UUID = Field(default_factory=uuid4)
    creation_date: datetime = Field(default_factory=datetime.now)
    name: str
    permissions: Set[Permission] = set()


class User(BaseModel):
    """Pydantic object representing a user.

    Attributes:
        id: Id of the user.
        creation_date: Date when the user was created.
        name: Name of the user.
    """

    id: UUID = Field(default_factory=uuid4)
    creation_date: datetime = Field(default_factory=datetime.now)
    name: str
    # email: str
    # password: str


class Team(BaseModel):
    """Pydantic object representing a team.

    Attributes:
        id: Id of the team.
        creation_date: Date when the team was created.
        name: Name of the team.
    """

    id: UUID = Field(default_factory=uuid4)
    creation_date: datetime = Field(default_factory=datetime.now)
    name: str


class Project(BaseModel):
    """Pydantic object representing a project.

    Attributes:
        id: Id of the project.
        creation_date: Date when the project was created.
        name: Name of the project.
        description: Optional project description.
    """

    id: UUID = Field(default_factory=uuid4)
    creation_date: datetime = Field(default_factory=datetime.now)
    name: str
    description: Optional[str] = None


class RoleAssignment(BaseModel):
    """Pydantic object representing a role assignment.

    Attributes:
        id: Id of the role assignment.
        creation_date: Date when the role was assigned.
        role_id: Id of the role.
        project_id: Optional ID of a project that the role is limited to.
        team_id: Id of a team to which the role is assigned.
        user_id: Id of a user to which the role is assigned.
    """

    id: UUID = Field(default_factory=uuid4)
    creation_date: datetime = Field(default_factory=datetime.now)
    role_id: UUID
    project_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    @root_validator
    def ensure_single_entity(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that either `user_id` or `team_id` is set."""

        user_id = values.get("user_id", None)
        team_id = values.get("team_id", None)
        if user_id and team_id:
            raise ValueError("Only `user_id` or `team_id` is allowed.")

        if not (user_id or team_id):
            raise ValueError(
                "Missing `user_id` or `team_id` for role assignment."
            )

        return values
