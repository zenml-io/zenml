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
"""SQL Model Implementations."""
import base64
from datetime import datetime
from typing import List, Dict
from uuid import UUID, uuid4

from sqlmodel import Session, select
from sqlmodel import Field, Relationship, SQLModel

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.models.component_models import ComponentModel
from zenml.models.stack_model import StackModel
from zenml.models.code_models import CodeRepositoryModel
from zenml.models.pipeline_models import (
    PipelineModel, PipelineRunModel, StepModel, StepRunModel
)
from zenml.models.user_management_models import (
    ProjectModel, RoleModel, UserModel
)

def _sqlmodel_uuid() -> UUID:
    """Generates a UUID whose hex string does not start with a '0'.

    Returns:
        A UUID whose hex string does not start with a '0'.
    """
    # SQLModel crashes when a UUID hex string starts with '0'
    # (see: https://github.com/tiangolo/sqlmodel/issues/25)
    uuid = uuid4()
    while uuid.hex[0] == "0":
        uuid = uuid4()
    return uuid


# Projects, Repositories


class ProjectSchema(SQLModel, table=True):
    """SQL Model for projects."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    description: str = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_model(cls, model: ProjectModel) -> "ProjectSchema":
        return cls(name=model.name, description=model.description)

    def to_model(self) -> ProjectModel:
        return ProjectModel(id=self.id,
                            name=self.name,
                            description=self.description,
                            created_at=self.created_at)

class CodeRepositorySchema(SQLModel, table=True):
    """SQL Model for code repositories."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    project_id: UUID = Field(foreign_key="projectschema.id")
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_model(
        cls, model: CodeRepositoryModel, project_id: str
    ) -> "CodeRepositorySchema":
        return cls(name=model.name, project_id=project_id)

    def to_model(self) -> CodeRepositoryModel:
        return CodeRepositoryModel(**self.dict())

# Users, Teams, Roles


class UserSchema(SQLModel, table=True):
    """SQL Model for users."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_model(cls, model: UserModel) -> "UserSchema":
        return cls(name=model.name)

    def to_model(self) -> UserModel:
        return UserModel(id=self.id, name=self.name, created_at=self.created_at)


class TeamSchema(SQLModel, table=True):
    """SQL Model for teams."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)


class TeamAssignmentSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    user_id: UUID = Field(primary_key=True, foreign_key="userschema.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamschema.id")


class RoleSchema(SQLModel, table=True):
    """SQL Model for roles."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_model(cls, model: RoleModel) -> "RoleSchema":
        return cls(name=model.name)

    def to_model(self) -> RoleModel:
        return RoleModel(**self.dict())

class UserRoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for assigning roles to users for a given project."""

    role_id: UUID = Field(primary_key=True, foreign_key="roleschema.id")
    user_id: UUID = Field(primary_key=True, foreign_key="userschema.id")
    project_id: UUID = Field(primary_key=True, foreign_key="projectschema.id")


class TeamRoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for assigning roles to teams for a given project."""

    role_id: UUID = Field(primary_key=True, foreign_key="roleschema.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamschema.id")
    project_id: UUID = Field(primary_key=True, foreign_key="projectschema.id")


# Stacks, Stack Components, Flavors


class FlavorSchema(SQLModel, table=True):
    """SQL Model for flavors."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)

    name: str

    # project_id - redundant since repository has this
    repository_id: UUID = Field(foreign_key="coderepositoryschema.id")
    created_by: UUID = Field(foreign_key="userschema.id")

    type: StackComponentType
    source: str
    git_sha: str
    integration: str

    created_at: datetime = Field(default_factory=datetime.now)


class StackCompositionSchema(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    stack_id: UUID = Field(primary_key=True, foreign_key="stackschema.id")
    component_id: UUID = Field(
        primary_key=True, foreign_key="stackcomponentschema.id"
    )


class StackSchema(SQLModel, table=True):
    """SQL Model for stacks."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    created_at: datetime = Field(default_factory=datetime.now)

    name: str
    is_shared: bool
    project_id: UUID = Field(
        foreign_key="projectschema.id", nullable=True
    )  # TODO: Unnullableify this
    owner: UUID = Field(
        foreign_key="userschema.id", nullable=True
    )  # TODO: Unnullableify this

    components: List["StackComponentSchema"] = Relationship(
        back_populates="stacks", link_model=StackCompositionSchema
    )

    @classmethod
    def from_create_model(cls,
                          user_id: UUID,
                          project_id: str,
                          defined_components: List["StackComponentSchema"],
                          stack: StackModel) -> "StackSchema":
        """Create an incomplete StackSchema with `id` and `created_at` missing.

        Returns:
            A StackComponentSchema
        """

        return cls(
            name=stack.name,
            project_id=project_id,
            owner=user_id,
            is_shared=stack.is_shared,
            components=defined_components,
            )

    def to_model(self) -> "StackModel":
        """Creates a ComponentModel from an instance of a StackSchema.

        Returns:
            a ComponentModel
        """

        return StackModel(
            id=self.id,
            name=self.name,
            owner=self.owner,
            project_id=self.project_id,
            is_shared=self.is_shared,
            components={c.type: c.to_model() for c in self.components}
        )


class StackComponentSchema(SQLModel, table=True):
    """SQL Model for stack components."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)

    name: str
    is_shared: bool

    # project_id - redundant since repository of flavor has this
    type: StackComponentType
    flavor_id: UUID = Field(
        foreign_key="flavorschema.id", nullable=True
    )  # TODO: Prefill flavors
    owner: UUID = Field(foreign_key="userschema.id", nullable=True)
    project_id: UUID = Field(
        foreign_key="projectschema.id", nullable=True
    )  # TODO: Unnullableify this

    configuration: bytes

    created_at: datetime = Field(default_factory=datetime.now)

    stacks: List["StackSchema"] = Relationship(
        back_populates="components", link_model=StackCompositionSchema
    )

    @classmethod
    def from_create_model(cls,
                          user_id: str,
                          project_id: str,
                          component: ComponentModel) -> "StackComponentSchema":
        """Create a StackComponentSchema with `id` and `created_at` missing.


        Returns:
            A StackComponentSchema
        """

        return cls(
            name=component.name,
            project_id=project_id,
            owner=user_id,
            is_shared=component.is_shared,
            type=component.type,
            flavor_id=component.flavor_id,
            configuration=component.configuration
        )

    def to_model(self) -> "ComponentModel":
        """Creates a ComponentModel from an instance of a StackSchema.

        Returns:
            A ComponentModel
        """
        return ComponentModel(
            id=self.id,
            name=self.name,
            type=self.type,
            flavor_id=self.flavor_id,
            owner=self.owner,
            project_id=self.project_id,
            is_shared=self.is_shared,
            configuration=self.configuration
        )


class PipelineSchema(SQLModel, table=True):
    """SQL Model for pipelines."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)

    name: str

    # project_id - redundant since repository has this
    repository_id: UUID = Field(foreign_key="coderepositoryschema.id")
    created_by: UUID = Field(foreign_key="userschema.id")

    docstring: str  # TODO: how to get this?
    configuration: str
    git_sha: str

    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_model(cls, model: PipelineModel) -> "PipelineSchema":
        pass  # TODO

    def to_model(self) -> "PipelineModel":
        with Session(self.engine) as session:
            steps = session.exec(
                select(StepSchema)
                .where(StepSchema.pipeline_id == self.id)
            ).all()

        return PipelineModel(
            id=self.id,
            name=self.name,
            docstring=self.docstring,
            steps=[step.to_model() for step in steps],
        )


class StepSchema(SQLModel, table=True):
    """SQL Model for steps of a pipeline."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    pipeline_id: UUID = Field(foreign_key="pipelineschema.id")
    source: str  # TODO: how to get this?

    @classmethod
    def from_model(cls, model: StepModel) -> "StepSchema":
        pass  # TODO

    def to_model(self) -> "StepModel":
        return StepModel(
            id=self.id,
            name=self.name,
            source=self.source,
        )


class PipelineRunSchema(SQLModel, table=True):
    """SQL Model for pipeline runs."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)

    name: str

    # project_id - redundant since stack/pipeline has this
    stack_id: UUID = Field(foreign_key="stackschema.id")
    pipeline_id: UUID = Field(foreign_key="pipelineschema.id")
    # context_id - TODO ?
    created_by: UUID = Field(foreign_key="userschema.id")

    runtime_configuration: str
    git_sha: str
    zenml_version: str

    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_model(cls, model: PipelineRunModel) -> "PipelineRunSchema":
        pass  # TODO

    def to_model(self) -> PipelineRunModel:
        pass  # TODO


class PipelineRunStepSchema(SQLModel, table=True):
    """SQL Model for pipeline run steps."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)

    name: str

    pipeline_run_id: UUID = Field(foreign_key="pipelinerunschema.id")
    # created_by - redundant since run has this

    status: ExecutionStatus
    docstring: str
    runtime_configuration: str

    # created_at - redundant since run has this

    @classmethod
    def from_model(cls, model: StepRunModel) -> "PipelineRunStepSchema":
        pass  # TODO

    def to_model(self) -> "StepRunModel":
        pass  # TODO


# MLMD


class MLMDSchema(SQLModel, table=True):
    """SQL Model for MLMD."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    project_id: UUID = Field(foreign_key="projectschema.id")
    type: str


class MLMDPropertySchema(SQLModel, table=True):
    """SQL Model for MLMD Properties."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    mlmd_id: UUID = Field(foreign_key="mlmdschema.id")
    value: str
