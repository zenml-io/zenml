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
from typing import TYPE_CHECKING, Any, List

from sqlmodel import Relationship

from zenml.models import (
    WorkspaceRequest,
    WorkspaceResponse,
    WorkspaceResponseBody,
    WorkspaceResponseMetadata,
    WorkspaceUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        ActionSchema,
        ArtifactVersionSchema,
        CodeRepositorySchema,
        EventSourceSchema,
        FlavorSchema,
        ModelSchema,
        ModelVersionPipelineRunSchema,
        ModelVersionSchema,
        PipelineBuildSchema,
        PipelineDeploymentSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunMetadataSchema,
        ScheduleSchema,
        SecretSchema,
        ServiceConnectorSchema,
        ServiceSchema,
        StackComponentSchema,
        StackSchema,
        StepRunSchema,
        TriggerSchema,
    )


class WorkspaceSchema(NamedSchema, table=True):
    """SQL Model for workspaces."""

    __tablename__ = "workspace"

    description: str

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
    artifact_versions: List["ArtifactVersionSchema"] = Relationship(
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
    actions: List["ActionSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    triggers: List["TriggerSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    event_sources: List["EventSourceSchema"] = Relationship(
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
    services: List["ServiceSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    service_connectors: List["ServiceConnectorSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    models: List["ModelSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    model_versions: List["ModelVersionSchema"] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    model_versions_pipeline_runs_links: List[
        "ModelVersionPipelineRunSchema"
    ] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(cls, workspace: WorkspaceRequest) -> "WorkspaceSchema":
        """Create a `WorkspaceSchema` from a `WorkspaceResponse`.

        Args:
            workspace: The `WorkspaceResponse` from which to create the schema.

        Returns:
            The created `WorkspaceSchema`.
        """
        return cls(name=workspace.name, description=workspace.description)

    def update(self, workspace_update: WorkspaceUpdate) -> "WorkspaceSchema":
        """Update a `WorkspaceSchema` from a `WorkspaceUpdate`.

        Args:
            workspace_update: The `WorkspaceUpdate` from which to update the
                schema.

        Returns:
            The updated `WorkspaceSchema`.
        """
        for field, value in workspace_update.model_dump(
            exclude_unset=True
        ).items():
            setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> WorkspaceResponse:
        """Convert a `WorkspaceSchema` to a `WorkspaceResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The converted `WorkspaceResponseModel`.
        """
        metadata = None
        if include_metadata:
            metadata = WorkspaceResponseMetadata(
                description=self.description,
            )
        return WorkspaceResponse(
            id=self.id,
            name=self.name,
            body=WorkspaceResponseBody(
                created=self.created,
                updated=self.updated,
            ),
            metadata=metadata,
        )
