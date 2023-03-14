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
"""Models representing stack component flavors."""

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel

if TYPE_CHECKING:
    from zenml.models import UserResponseModel, WorkspaceResponseModel


# ---- #
# BASE #
# ---- #


class FlavorBaseModel(BaseModel):
    """Base model for stack component flavors."""

    name: str = Field(
        title="The name of the Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(title="The type of the Flavor.")
    config_schema: Dict[str, Any] = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
    )
    source: str = Field(
        title="The path to the module which contains this Flavor.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    logo_url: Optional[str] = Field(
        title="Optionally, a url pointing to a png,"
        "svg or jpg can be attached."
    )
    docs_url: Optional[str] = Field(
        title="Optionally, a url pointing to docs," "within docs.zenml.io."
    )
    sdk_docs_url: Optional[str] = Field(
        title="Optionally, a url pointing to SDK docs,"
        "within apidocs.zenml.io."
    )
    is_custom: bool = Field(
        title="Whether or not this flavor is a custom, user created flavor.",
        default=True,
    )


# -------- #
# RESPONSE #
# -------- #


class FlavorResponseModel(FlavorBaseModel, BaseResponseModel):
    """Response model for stack component flavors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
        "type",
        "integration",
    ]

    user: Union["UserResponseModel", None] = Field(
        title="The user that created this resource.", nullable=True
    )

    workspace: Optional["WorkspaceResponseModel"] = Field(
        title="The project of this resource."
    )


# ------ #
# FILTER #
# ------ #


class FlavorFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Flavors."""

    name: str = Field(
        default=None,
        description="Name of the flavor",
    )
    type: str = Field(
        default=None,
        description="Stack Component Type of the stack flavor",
    )
    integration: str = Field(
        default=None,
        description="Integration associated with the flavor",
    )
    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace of the stack"
    )
    user_id: Union[UUID, str] = Field(None, description="User of the stack")


# ------- #
# REQUEST #
# ------- #


class FlavorRequestModel(FlavorBaseModel, BaseRequestModel):
    """Request model for stack component flavors."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "type",
        "integration",
    ]

    user: Optional[UUID] = Field(
        title="The id of the user that created this resource."
    )

    workspace: Optional[UUID] = Field(
        title="The workspace to which this resource belongs."
    )


# ------- #
# Update #
# ------- #


@update_model
class FlavorUpdateModel(FlavorRequestModel):
    """Update model for flavors."""
