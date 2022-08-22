import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.enums import StackComponentType
from zenml.zen_stores.models import StackWrapper
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


class ComponentSchema(SQLModel, table=True):
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
    # project_id: UUID = Field(foreign_key="projectschema.id")  # redundant since repository has this
    repository_id: UUID = Field(foreign_key="repositoryschema.id")


class CompositionSchema(SQLModel, table=True):
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
    # project_id: UUID = Field(foreign_key="projectschema.id")  # redundant since repository has this
    repository_id: UUID = Field(foreign_key="repositoryschema.id")


class PipelineRunSchema(SQLModel, table=True):
    """SQL Model for pipeline runs."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    pipeline_id: UUID = Field(foreign_key="pipelineschema.id")
    # context_id  TODO ?
    stack_id: UUID = Field(foreign_key="stackschema.id")
    runtime_configuration: str
    name: str
    git_sha: str
    zenml_version: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: UUID = Field(foreign_key="userschema.id")
    # project_id: UUID = Field(foreign_key="projectschema.id")  # redundant since stack/pipeline has this

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
        # TODO: update
        return PipelineRunSchema(
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
        # TODO: update
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


class StepSchema(SQLModel, table=True):
    """SQL Model for pipeline run steps."""

    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    name: str
    # created_by: UUID = Field(foreign_key="userschema.id")  # redundant since stack/pipeline has this
    # created_at: datetime = Field(default_factory=datetime.now)  # redundant since run has this
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
