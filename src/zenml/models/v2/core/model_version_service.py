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
"""Models representing the link between model versions and services."""

from typing import Any, List, Optional, Union
from uuid import UUID

from pydantic import Field
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

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
from zenml.models.v2.core.service import ServiceResponse

# ------------------ Request Model ------------------


class ModelVersionServiceRequest(WorkspaceScopedRequest):
    """Request model for links between model versions and services."""

    model: UUID
    model_version: UUID
    service: UUID


# ------------------ Update Model ------------------

# There is no update model for links between model version and services.

# ------------------ Response Model ------------------


class ModelVersionServiceResponseBody(BaseDatedResponseBody):
    """Response body for links between model versions and services."""

    model: UUID
    model_version: UUID
    service: ServiceResponse


class ModelVersionServiceResponseResources(BaseResponseResources):
    """Class for all resource models associated with the model version service entity."""


class ModelVersionServiceResponse(
    BaseIdentifiedResponse[
        ModelVersionServiceResponseBody,
        BaseResponseMetadata,
        ModelVersionServiceResponseResources,
    ]
):
    """Response model for links between model versions and services."""

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
    def service(self) -> "ServiceResponse":
        """The `service` property.

        Returns:
            the value of the property.
        """
        return self.get_body().service


# ------------------ Filter Model ------------------


class ModelVersionServiceFilter(WorkspaceScopedFilter):
    """Model version pipeline run links filter model."""

    # Pipeline run name is not a DB field and needs to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "service_name",
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
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    model_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model ID"
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model version ID"
    )
    service_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by service ID"
    )
    service_name: Optional[str] = Field(
        default=None,
        description="Name of the service to filter by",
    )

    def get_custom_filters(
        self,
    ) -> List[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlalchemy import and_

        from zenml.zen_stores.schemas.model_schemas import (
            ModelVersionServiceSchema,
        )
        from zenml.zen_stores.schemas.service_schemas import (
            ServiceSchema,
        )

        if self.service_name:
            value, filter_operator = self._resolve_operator(self.service_name)
            filter_ = StrFilter(
                operation=GenericFilterOps(filter_operator),
                column="name",
                value=value,
            )
            service_name_filter = and_(  # type: ignore[type-var]
                ModelVersionServiceSchema.service_id == ServiceSchema.id,
                filter_.generate_query_conditions(ServiceSchema),
            )
            custom_filters.append(service_name_filter)

        return custom_filters
