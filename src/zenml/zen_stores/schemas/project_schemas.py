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
"""SQL Model Implementations for projects."""

from typing import TYPE_CHECKING, Any, List

from sqlalchemy import UniqueConstraint
from sqlmodel import Relationship

from zenml.models import (
    ProjectRequest,
    ProjectResponse,
    ProjectResponseBody,
    ProjectResponseMetadata,
    ProjectUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        ActionSchema,
        ArtifactVersionSchema,
        CodeRepositorySchema,
        EventSourceSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineBuildSchema,
        PipelineDeploymentSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunMetadataSchema,
        ScheduleSchema,
        ServiceSchema,
        StepRunSchema,
        TriggerSchema,
    )


class ProjectSchema(NamedSchema, table=True):
    """SQL Model for projects."""

    __tablename__ = "project"
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="unique_project_name",
        ),
    )

    display_name: str
    description: str

    pipelines: List["PipelineSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    schedules: List["ScheduleSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    step_runs: List["StepRunSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    builds: List["PipelineBuildSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    artifact_versions: List["ArtifactVersionSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    run_metadata: List["RunMetadataSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    actions: List["ActionSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    triggers: List["TriggerSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    event_sources: List["EventSourceSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    code_repositories: List["CodeRepositorySchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    services: List["ServiceSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    models: List["ModelSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )
    model_versions: List["ModelVersionSchema"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(cls, project: ProjectRequest) -> "ProjectSchema":
        """Create a `ProjectSchema` from a `ProjectResponse`.

        Args:
            project: The `ProjectResponse` from which to create the schema.

        Returns:
            The created `ProjectSchema`.
        """
        return cls(
            name=project.name,
            description=project.description,
            display_name=project.display_name,
        )

    def update(self, project_update: ProjectUpdate) -> "ProjectSchema":
        """Update a `ProjectSchema` from a `ProjectUpdate`.

        Args:
            project_update: The `ProjectUpdate` from which to update the
                schema.

        Returns:
            The updated `ProjectSchema`.
        """
        for field, value in project_update.model_dump(
            exclude_unset=True
        ).items():
            setattr(self, field, value)

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ProjectResponse:
        """Convert a `ProjectSchema` to a `ProjectResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The converted `ProjectResponseModel`.
        """
        metadata = None
        if include_metadata:
            metadata = ProjectResponseMetadata(
                description=self.description,
            )
        return ProjectResponse(
            id=self.id,
            name=self.name,
            body=ProjectResponseBody(
                display_name=self.display_name,
                created=self.created,
                updated=self.updated,
            ),
            metadata=metadata,
        )
