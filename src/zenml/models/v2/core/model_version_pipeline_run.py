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

from typing import TYPE_CHECKING, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import ConfigDict, Field
from sqlalchemy.sql.elements import ColumnElement

from zenml.enums import GenericFilterOps
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.filter import BaseFilter, StrFilter
from zenml.models.v2.core.pipeline_run import PipelineRunResponse

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class ModelVersionPipelineRunRequest(BaseRequest):
    """Request model for links between model versions and pipeline runs."""

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


class ModelVersionPipelineRunFilter(BaseFilter):
    """Model version pipeline run links filter model."""

    FILTER_EXCLUDE_FIELDS = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_run_name",
        "user",
    ]
    CLI_EXCLUDE_FIELDS = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "model_version_id",
        "updated",
        "id",
    ]

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
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the pipeline run.",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

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

        if self.user:
            user_filter = and_(
                ModelVersionPipelineRunSchema.pipeline_run_id
                == PipelineRunSchema.id,
                PipelineRunSchema.user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user,
                    table=UserSchema,
                    additional_columns=["full_name"],
                ),
            )
            custom_filters.append(user_filter)

        return custom_filters
