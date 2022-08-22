from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.enums import StackComponentType
from zenml.zen_stores.models.pipeline_models import PipelineRunWrapper


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


class UserSchema(SQLModel, table=True):
    """SQL Model for users."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)


class StackSchema(SQLModel, table=True):
    """SQL Model for stacks."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: UUID = Field(foreign_key="userschema.id")
    project_id: UUID = Field(foreign_key="projectschema.id")


class StackComponentSchema(SQLModel, table=True):
    """SQL Model for stack components."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    type: StackComponentType
    flavor_id: UUID = Field(foreign_key="flavorschema.id")
    name: str
    configuration: bytes  # e.g. base64 encoded json string
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: UUID = Field(foreign_key="userschema.id")
    project_id: UUID = Field(foreign_key="projectschema.id")


class RepositorySchema(SQLModel, table=True):
    """SQL Model for repositories."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    project_id: UUID = Field(foreign_key="projectschema.id")
    created_at: datetime = Field(default_factory=datetime.now)
    name: str


class FlavorSchema(SQLModel, table=True):
    """SQL Model for flavors."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    type: StackComponentType
    name: str
    source: str
    git_sha: str
    integration: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: UUID = Field(foreign_key="userschema.id")
    # project_id - redundant since repository has this
    repository_id: UUID = Field(foreign_key="repositoryschema.id")


class StackCompositionSchema(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    stack_id: UUID = Field(primary_key=True, foreign_key="stackschema.id")
    component_id: UUID = Field(
        primary_key=True, foreign_key="componentschema.id"
    )


class TeamSchema(SQLModel, table=True):
    """SQL Model for teams."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)


class ProjectSchema(SQLModel, table=True):
    """SQL Model for projects."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)


class RoleSchema(SQLModel, table=True):
    """SQL Model for roles."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    created_at: datetime = Field(default_factory=datetime.now)
    name: str


class TeamAssignmentSchema(SQLModel, table=True):
    """SQL Model for team assignments."""

    user_id: UUID = Field(primary_key=True, foreign_key="userschema.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamschema.id")


class RoleAssignmentSchema(SQLModel, table=True):
    """SQL Model for role assignments."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    created_at: datetime = Field(default_factory=datetime.now)
    role_id: UUID = Field(foreign_key="roleschema.id")
    user_id: UUID = Field(foreign_key="userschema.id")
    team_id: UUID = Field(foreign_key="teamschema.id")
    project_id: UUID = Field(foreign_key="projectschema.id")


class PipelineSchema(SQLModel, table=True):
    """SQL Model for pipelines."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    git_sha: str
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: UUID = Field(foreign_key="userschema.id")
    # project_id - redundant since repository has this
    repository_id: UUID = Field(foreign_key="repositoryschema.id")


class PipelineRunSchema(SQLModel, table=True):
    """SQL Model for pipeline runs."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    pipeline_id: UUID = Field(foreign_key="pipelineschema.id")
    # context_id - TODO ?
    stack_id: UUID = Field(foreign_key="stackschema.id")
    runtime_configuration: str
    name: str
    git_sha: str
    zenml_version: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: UUID = Field(foreign_key="userschema.id")
    # project_id - redundant since stack/pipeline has this

    @classmethod
    def from_pipeline_run_wrapper(
        cls, wrapper: PipelineRunWrapper
    ) -> "PipelineRunSchema":
        """Creates a PipelineRunTable from a PipelineRunWrapper.

        Args:
            wrapper: The PipelineRunWrapper to create the PipelineRunTable from.

        Returns:
            A PipelineRunTable.
        """
        pass  # TODO

    def to_pipeline_run_wrapper(self) -> PipelineRunWrapper:
        """Creates a PipelineRunWrapper from a PipelineRunTable.

        Returns:
            A PipelineRunWrapper.
        """
        pass  # TODO


class PipelineRunStepSchema(SQLModel, table=True):
    """SQL Model for pipeline run steps."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    # created_by - redundant since run has this
    # created_at - redundant since run has this
    pipeline_run_id: UUID = Field(foreign_key="pipelinerunschema.id")
    runtime_configuration: str


class MLMDSchema(SQLModel, table=True):
    """SQL Model for MLMD."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    type: str
    project_id: UUID = Field(foreign_key="projectschema.id")


class MLMDPropertySchema(SQLModel, table=True):
    """SQL Model for MLMD Properties."""

    mlmd_id: UUID = Field(primary_key=True, foreign_key="mlmdschema.id")
    name: str
    value: str
