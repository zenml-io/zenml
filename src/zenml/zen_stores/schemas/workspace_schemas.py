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
"""SQL Model Implementations for Workspaces."""
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlmodel import Relationship

from zenml.models import (
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        CodeRepositorySchema,
        FlavorSchema,
        PipelineBuildSchema,
        PipelineDeploymentSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunMetadataSchema,
        ScheduleSchema,
        SecretSchema,
        ServiceConnectorSchema,
        StackComponentSchema,
        StackSchema,
        StepRunSchema,
        TeamRoleAssignmentSchema,
        UserRoleAssignmentSchema,
    )


class WorkspaceSchema(NamedSchema, table=True):
    """SQL Model for workspaces."""

    __tablename__ = "workspace"

    description: str

    user_role_assignments: List["UserRoleAssignmentSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    team_role_assignments: List["TeamRoleAssignmentSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "all, delete"},
    )
    stacks: List["StackSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    components: List["StackComponentSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    flavors: List["FlavorSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    pipelines: List["PipelineSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    step_runs: List["StepRunSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    builds: List["PipelineBuildSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    artifacts: List["ArtifactSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    secrets: List["SecretSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    code_repositories: List["CodeRepositorySchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    service_connectors: List["ServiceConnectorSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(
        cls, workspace: WorkspaceRequestModel
    ) -> "WorkspaceSchema":
        """Create a `WorkspaceSchema` from a `WorkspaceResponseModel`.

        Args:
            workspace: The `WorkspaceResponseModel` from which to create the schema.

        Returns:
            The created `WorkspaceSchema`.
        """
        return cls(name=workspace.name, description=workspace.description)

    def update(
        self, workspace_update: WorkspaceUpdateModel
    ) -> "WorkspaceSchema":
        """Update a `WorkspaceSchema` from a `WorkspaceUpdateModel`.

        Args:
            workspace_update: The `WorkspaceUpdateModel` from which to update the
                schema.

        Returns:
            The updated `WorkspaceSchema`.
        """
        for field, value in workspace_update.dict(exclude_unset=True).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self) -> WorkspaceResponseModel:
        """Convert a `WorkspaceSchema` to a `WorkspaceResponseModel`.

        Returns:
            The converted `WorkspaceResponseModel`.
        """
        return WorkspaceResponseModel(
            id=self.id,
            name=self.name,
            description=self.description,
            created=self.created,
            updated=self.updated,
        )
