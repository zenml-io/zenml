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
"""Models representing the link between model versions and artifacts."""

from typing import TYPE_CHECKING, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import ConfigDict, Field

from zenml.enums import GenericFilterOps
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.filter import BaseFilter, StrFilter

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


# ------------------ Request Model ------------------


class ModelVersionArtifactRequest(BaseRequest):
    """Request model for links between model versions and artifacts."""

    model_version: UUID
    artifact_version: UUID

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------

# There is no update model for links between model version and artifacts.

# ------------------ Response Model ------------------


class ModelVersionArtifactResponseBody(BaseDatedResponseBody):
    """Response body for links between model versions and artifacts."""

    model_version: UUID
    artifact_version: "ArtifactVersionResponse"

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class ModelVersionArtifactResponseResources(BaseResponseResources):
    """Class for all resource models associated with the model version artifact entity."""


class ModelVersionArtifactResponse(
    BaseIdentifiedResponse[
        ModelVersionArtifactResponseBody,
        BaseResponseMetadata,
        ModelVersionArtifactResponseResources,
    ]
):
    """Response model for links between model versions and artifacts."""

    @property
    def model_version(self) -> UUID:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model_version

    @property
    def artifact_version(self) -> "ArtifactVersionResponse":
        """The `artifact_version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().artifact_version


# ------------------ Filter Model ------------------


class ModelVersionArtifactFilter(BaseFilter):
    """Model version pipeline run links filter model."""

    # Artifact name and type are not DB fields and need to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "artifact_name",
        "only_data_artifacts",
        "only_model_artifacts",
        "only_deployment_artifacts",
        "has_custom_name",
        "user",
    ]
    CLI_EXCLUDE_FIELDS = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "only_data_artifacts",
        "only_model_artifacts",
        "only_deployment_artifacts",
        "has_custom_name",
        "model_version_id",
        "updated",
        "id",
    ]

    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Filter by model version ID",
        union_mode="left_to_right",
    )
    artifact_version_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Filter by artifact ID",
        union_mode="left_to_right",
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Name of the artifact",
    )
    only_data_artifacts: Optional[bool] = False
    only_model_artifacts: Optional[bool] = False
    only_deployment_artifacts: Optional[bool] = False
    has_custom_name: Optional[bool] = None
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the artifact.",
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
    ) -> List[Union["ColumnElement[bool]"]]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_, col

        from zenml.zen_stores.schemas import (
            ArtifactSchema,
            ArtifactVersionSchema,
            ModelVersionArtifactSchema,
            UserSchema,
        )

        if self.artifact_name:
            value, filter_operator = self._resolve_operator(self.artifact_name)
            filter_ = StrFilter(
                operation=GenericFilterOps(filter_operator),
                column="name",
                value=value,
            )
            artifact_name_filter = and_(
                ModelVersionArtifactSchema.artifact_version_id
                == ArtifactVersionSchema.id,
                ArtifactVersionSchema.artifact_id == ArtifactSchema.id,
                filter_.generate_query_conditions(ArtifactSchema),
            )
            custom_filters.append(artifact_name_filter)

        if self.only_data_artifacts:
            data_artifact_filter = and_(
                ModelVersionArtifactSchema.artifact_version_id
                == ArtifactVersionSchema.id,
                col(ArtifactVersionSchema.type).not_in(
                    ["ServiceArtifact", "ModelArtifact"]
                ),
            )
            custom_filters.append(data_artifact_filter)

        if self.only_model_artifacts:
            model_artifact_filter = and_(
                ModelVersionArtifactSchema.artifact_version_id
                == ArtifactVersionSchema.id,
                ArtifactVersionSchema.type == "ModelArtifact",
            )
            custom_filters.append(model_artifact_filter)

        if self.only_deployment_artifacts:
            deployment_artifact_filter = and_(
                ModelVersionArtifactSchema.artifact_version_id
                == ArtifactVersionSchema.id,
                ArtifactVersionSchema.type == "ServiceArtifact",
            )
            custom_filters.append(deployment_artifact_filter)

        if self.has_custom_name is not None:
            custom_name_filter = and_(
                ModelVersionArtifactSchema.artifact_version_id
                == ArtifactVersionSchema.id,
                ArtifactVersionSchema.artifact_id == ArtifactSchema.id,
                ArtifactSchema.has_custom_name == self.has_custom_name,
            )
            custom_filters.append(custom_name_filter)

        if self.user:
            user_filter = and_(
                ModelVersionArtifactSchema.artifact_version_id
                == ArtifactVersionSchema.id,
                ArtifactVersionSchema.user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user,
                    table=UserSchema,
                    additional_columns=["full_name"],
                ),
            )
            custom_filters.append(user_filter)

        return custom_filters
