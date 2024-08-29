#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Models representing the link between model versions and pipeline runs."""

from typing import List, Optional, Union
from uuid import UUID

from pydantic import ConfigDict, Field
from sqlalchemy.sql.elements import ColumnElement

from zenml.enums import GenericFilterOps
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.filter import StrFilter
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
)
from zenml.models.v2.core.pipeline_run import PipelineRunResponse

# ------------------ Request Model ------------------


class ModelVersionPipelineRunRequest(WorkspaceScopedRequest):
    """Request model for links between model versions and pipeline runs."""

    model: UUID
    model_version: UUID
    pipeline_run: UUID

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------

# There is no update model for links between model version and pipeline runs.

# ------------------ Response Model ------------------


class ModelVersionPipelineRunResponseBody(BaseDatedResponseBody):
    """Response body for links between model versions and pipeline runs."""

    model: UUID
    model_version: UUID
    pipeline_run: PipelineRunResponse

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class ModelVersionPipelineRunResponseResources(BaseResponseResources):
    """Class for all resource models associated with the model version pipeline run entity."""


class ModelVersionPipelineRunResponse(
    BaseIdentifiedResponse[
        ModelVersionPipelineRunResponseBody,
        BaseResponseMetadata,
        ModelVersionPipelineRunResponseResources,
    ]
):
    """Response model for links between model versions and pipeline runs."""

    # Body and metadata properties
    @property
    def model(self) -> UUID:
        """The `model` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model

    @property
    def model_version(self) -> UUID:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model_version

    @property
    def pipeline_run(self) -> "PipelineRunResponse":
        """The `pipeline_run` property.

        Returns:
            the value of the property.
        """
        return self.get_body().pipeline_run


# ------------------ Filter Model ------------------


class ModelVersionPipelineRunFilter(WorkspaceScopedFilter):
    """Model version pipeline run links filter model."""

    FILTER_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_run_name",
        "user_name",
    ]
    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "model_id",
        "model_version_id",
        "user_id",
        "workspace_id",
        "updated",
        "id",
    ]

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="The workspace of the Model Version",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="The user of the Model Version",
        union_mode="left_to_right",
    )
    model_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Filter by model ID",
        union_mode="left_to_right",
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Filter by model version ID",
        union_mode="left_to_right",
    )
    pipeline_run_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Filter by pipeline run ID",
        union_mode="left_to_right",
    )
    pipeline_run_name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline run",
    )
    user_name: Optional[str] = Field(
        default=None,
        description="Name of the user that created the pipeline run.",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(self) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            ModelVersionPipelineRunSchema,
            PipelineRunSchema,
            UserSchema,
        )

        if self.pipeline_run_name:
            value, filter_operator = self._resolve_operator(
                self.pipeline_run_name
            )
            filter_ = StrFilter(
                operation=GenericFilterOps(filter_operator),
                column="name",
                value=value,
            )
            pipeline_run_name_filter = and_(
                ModelVersionPipelineRunSchema.pipeline_run_id
                == PipelineRunSchema.id,
                filter_.generate_query_conditions(PipelineRunSchema),
            )
            custom_filters.append(pipeline_run_name_filter)

        if self.user_name is not None:
            user_name_filter = and_(
                ModelVersionPipelineRunSchema.pipeline_run_id
                == PipelineRunSchema.id,
                PipelineRunSchema.user_id == UserSchema.id,
                self.generate_custom_query_conditions_for_column(
                    value=self.user_name, table=UserSchema, column="name"
                ),
            )
            custom_filters.append(user_name_filter)

        return custom_filters
