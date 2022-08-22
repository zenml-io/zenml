import datetime as dt
import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.enums import StackComponentType
from zenml.zen_stores.models import (
    Project,
    RoleAssignment,
    StackWrapper,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import (
    PipelineRunWrapper,
    PipelineWrapper,
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


class ZenUser(SQLModel, table=True):
    """SQL Model for users."""

    id: int = Field(primary_key=True)
    name: str


class ZenStack(SQLModel, table=True):
    """SQL Model for stacks."""

    name: str = Field(primary_key=True)
    created_by: int
    create_time: Optional[dt.datetime] = Field(default_factory=dt.datetime.now)


class ComponentSchema(SQLModel, table=True):
    """SQL Model for stack components."""

    id: int = Field(primary_key=True)
    type: StackComponentType
    flavor_id: int  # = Field(foreign_key="flavorschema.id")
    name: str
    component_flavor: str
    configuration: bytes  # e.g. base64 encoded json string
    create_time: dt.datetime
    user_id: int  # = Field(foreign_key="userschema.id")
    project_id: int  # = Field(foreign_key="projectschema.id")


class ZenFlavor(SQLModel, table=True):
    """SQL Model for flavors."""

    type: StackComponentType = Field(primary_key=True)
    name: str = Field(primary_key=True)
    source: str
    integration: Optional[str]


class ZenStackDefinition(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    stack_name: str = Field(primary_key=True, foreign_key="zenstack.name")
    component_type: StackComponentType = Field(
        primary_key=True, foreign_key="zenstackcomponent.component_type"
    )
    component_name: str = Field(
        primary_key=True, foreign_key="zenstackcomponent.name"
    )


class UserTable(User, SQLModel, table=True):
    """SQL Model for users."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)


class TeamTable(Team, SQLModel, table=True):
    """SQL Model for teams."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)


class ProjectTable(Project, SQLModel, table=True):
    """SQL Model for projects."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    creation_date: datetime = Field(default_factory=datetime.now)


class RoleTable(SQLModel, table=True):
    """SQL Model for roles."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    creation_date: datetime = Field(default_factory=datetime.now)
    name: str


class TeamAssignmentTable(SQLModel, table=True):
    """SQL Model for team assignments."""

    user_id: UUID = Field(primary_key=True, foreign_key="usertable.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamtable.id")


class RoleAssignmentTable(RoleAssignment, SQLModel, table=True):
    """SQL Model for role assignments."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    role_id: UUID = Field(foreign_key="roletable.id")
    user_id: Optional[UUID] = Field(default=None, foreign_key="usertable.id")
    team_id: Optional[UUID] = Field(default=None, foreign_key="teamtable.id")
    project_id: Optional[UUID] = Field(
        default=None, foreign_key="projecttable.id"
    )


class PipelineRunTable(SQLModel, table=True):
    """SQL Model for pipeline runs."""

    name: str = Field(primary_key=True)
    zenml_version: str
    git_sha: Optional[str]

    pipeline_name: str
    pipeline: str
    stack: str
    runtime_configuration: str

    user_id: UUID = Field(foreign_key="usertable.id")
    project_name: Optional[str] = Field(
        default=None, foreign_key="projecttable.name"
    )

    @classmethod
    def from_pipeline_run_wrapper(
        cls, wrapper: PipelineRunWrapper
    ) -> "PipelineRunTable":
        """Creates a PipelineRunTable from a PipelineRunWrapper.

        Args:
            wrapper: The PipelineRunWrapper to create the PipelineRunTable from.

        Returns:
            A PipelineRunTable.
        """
        return PipelineRunTable(
            name=wrapper.name,
            zenml_version=wrapper.zenml_version,
            git_sha=wrapper.git_sha,
            pipeline_name=wrapper.pipeline.name,
            pipeline=wrapper.pipeline.json(),
            stack=wrapper.stack.json(),
            runtime_configuration=json.dumps(wrapper.runtime_configuration),
            user_id=wrapper.user_id,
            project_name=wrapper.project_name,
        )

    def to_pipeline_run_wrapper(self) -> PipelineRunWrapper:
        """Creates a PipelineRunWrapper from a PipelineRunTable.

        Returns:
            A PipelineRunWrapper.
        """
        return PipelineRunWrapper(
            name=self.name,
            zenml_version=self.zenml_version,
            git_sha=self.git_sha,
            pipeline=PipelineWrapper.parse_raw(self.pipeline),
            stack=StackWrapper.parse_raw(self.stack),
            runtime_configuration=json.loads(self.runtime_configuration),
            user_id=self.user_id,
            project_name=self.project_name,
        )
