#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Models representing pipeline templates."""

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.config.pipeline_spec import PipelineSpec
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
    WorkspaceScopedTaggableFilter,
)
from zenml.models.v2.core.code_reference import (
    CodeReferenceResponse,
)
from zenml.models.v2.core.pipeline import PipelineResponse
from zenml.models.v2.core.pipeline_build import (
    PipelineBuildResponse,
)
from zenml.models.v2.core.pipeline_deployment import (
    PipelineDeploymentResponse,
)
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

# ------------------ Request Model ------------------


class RunTemplateRequest(WorkspaceScopedRequest):
    """Request model for run templates."""

    name: str = Field(
        title="The name of the run template.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the run template.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    source_deployment_id: UUID = Field(
        title="The deployment that should be the base of the created template."
    )
    tags: Optional[List[str]] = Field(
        default=None,
        title="Tags of the run template.",
    )


# ------------------ Update Model ------------------


class RunTemplateUpdate(BaseUpdate):
    """Run template update model."""

    name: Optional[str] = Field(
        default=None,
        title="The name of the run template.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the run template.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the run template."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the run template."
    )


# ------------------ Response Model ------------------


class RunTemplateResponseBody(WorkspaceScopedResponseBody):
    """Response body for run templates."""

    runnable: bool = Field(
        title="If a run can be started from the template.",
    )
    latest_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the latest run of the run template.",
    )
    latest_run_status: Optional[ExecutionStatus] = Field(
        default=None,
        title="The status of the latest run of the run template.",
    )


class RunTemplateResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for run templates."""

    description: Optional[str] = Field(
        default=None,
        title="The description of the run template.",
    )
    pipeline_spec: Optional[PipelineSpec] = Field(
        default=None, title="The spec of the pipeline."
    )
    config_template: Optional[Dict[str, Any]] = Field(
        default=None, title="Run configuration template."
    )
    config_schema: Optional[Dict[str, Any]] = Field(
        default=None, title="Run configuration schema."
    )


class RunTemplateResponseResources(WorkspaceScopedResponseResources):
    """All resource models associated with the run template."""

    source_deployment: Optional[PipelineDeploymentResponse] = Field(
        default=None,
        title="The deployment that is the source of the template.",
    )
    pipeline: Optional[PipelineResponse] = Field(
        default=None, title="The pipeline associated with the template."
    )
    build: Optional[PipelineBuildResponse] = Field(
        default=None,
        title="The pipeline build associated with the template.",
    )
    code_reference: Optional[CodeReferenceResponse] = Field(
        default=None,
        title="The code reference associated with the template.",
    )
    tags: List[TagResponse] = Field(
        title="Tags associated with the run template.",
    )


class RunTemplateResponse(
    WorkspaceScopedResponse[
        RunTemplateResponseBody,
        RunTemplateResponseMetadata,
        RunTemplateResponseResources,
    ]
):
    """Response model for run templates."""

    name: str = Field(
        title="The name of the run template.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "RunTemplateResponse":
        """Return the hydrated version of this run template.

        Returns:
            The hydrated run template.
        """
        from zenml.client import Client

        return Client().zen_store.get_run_template(
            template_id=self.id, hydrate=True
        )

    # Body and metadata properties
    @property
    def runnable(self) -> bool:
        """The `runnable` property.

        Returns:
            the value of the property.
        """
        return self.get_body().runnable

    @property
    def latest_run_id(self) -> Optional[UUID]:
        """The `latest_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_run_id

    @property
    def latest_run_status(self) -> Optional[ExecutionStatus]:
        """The `latest_run_status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_run_status

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def pipeline_spec(self) -> Optional[PipelineSpec]:
        """The `pipeline_spec` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline_spec

    @property
    def config_template(self) -> Optional[Dict[str, Any]]:
        """The `config_template` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config_template

    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        """The `config_schema` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config_schema

    @property
    def source_deployment(self) -> Optional[PipelineDeploymentResponse]:
        """The `source_deployment` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().source_deployment

    @property
    def pipeline(self) -> Optional[PipelineResponse]:
        """The `pipeline` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pipeline

    @property
    def build(self) -> Optional[PipelineBuildResponse]:
        """The `build` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().build

    @property
    def code_reference(self) -> Optional[CodeReferenceResponse]:
        """The `code_reference` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().code_reference

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags


# ------------------ Filter Model ------------------


class RunTemplateFilter(WorkspaceScopedTaggableFilter):
    """Model for filtering of run templates."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.FILTER_EXCLUDE_FIELDS,
        "code_repository_id",
        "stack_id",
        "build_id",
        "pipeline_id",
        "user",
        "pipeline",
        "stack",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the run template.",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace associated with the template.",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User that created the template.",
        union_mode="left_to_right",
    )
    pipeline_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Pipeline associated with the template.",
        union_mode="left_to_right",
    )
    build_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Build associated with the template.",
        union_mode="left_to_right",
    )
    stack_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Stack associated with the template.",
        union_mode="left_to_right",
    )
    code_repository_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Code repository associated with the template.",
        union_mode="left_to_right",
    )
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the template.",
    )
    pipeline: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the pipeline associated with the template.",
    )
    stack: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the stack associated with the template.",
    )

    def get_custom_filters(
        self,
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            CodeReferenceSchema,
            PipelineDeploymentSchema,
            PipelineSchema,
            RunTemplateSchema,
            StackSchema,
            UserSchema,
        )

        if self.code_repository_id:
            code_repo_filter = and_(
                RunTemplateSchema.source_deployment_id
                == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.code_reference_id
                == CodeReferenceSchema.id,
                CodeReferenceSchema.code_repository_id
                == self.code_repository_id,
            )
            custom_filters.append(code_repo_filter)

        if self.stack_id:
            stack_filter = and_(
                RunTemplateSchema.source_deployment_id
                == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.stack_id == self.stack_id,
            )
            custom_filters.append(stack_filter)

        if self.build_id:
            build_filter = and_(
                RunTemplateSchema.source_deployment_id
                == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.build_id == self.build_id,
            )
            custom_filters.append(build_filter)

        if self.pipeline_id:
            pipeline_filter = and_(
                RunTemplateSchema.source_deployment_id
                == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.pipeline_id == self.pipeline_id,
            )
            custom_filters.append(pipeline_filter)

        if self.user is not None:
            user_filter = and_(
                RunTemplateSchema.user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user, table=UserSchema
                ),
            )
            custom_filters.append(user_filter)

        if self.pipeline is not None:
            pipeline_filter = and_(
                RunTemplateSchema.source_deployment_id
                == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.pipeline_id == PipelineSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.pipeline,
                    table=PipelineSchema,
                ),
            )
            custom_filters.append(pipeline_filter)

        if self.stack:
            stack_filter = and_(
                RunTemplateSchema.source_deployment_id
                == PipelineDeploymentSchema.id,
                PipelineDeploymentSchema.stack_id == StackSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.stack,
                    table=StackSchema,
                ),
            )
            custom_filters.append(stack_filter)

        return custom_filters
