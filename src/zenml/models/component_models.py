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
"""Models representing stack components."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field, validator

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import ShareableWorkspaceScopedFilterModel
from zenml.models.service_connector_models import ServiceConnectorResponseModel
from zenml.utils import secret_utils

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
    from sqlmodel import SQLModel

logger = get_logger(__name__)


# ---- #
# BASE #
# ---- #
class ComponentBaseModel(BaseModel):
    """Base model for stack components."""

    name: str = Field(
        title="The name of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    type: StackComponentType = Field(
        title="The type of the stack component.",
    )

    flavor: str = Field(
        title="The flavor of the stack component.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )

    connector_resource_id: Optional[str] = Field(
        default=None,
        description="The ID of a specific resource instance to "
        "gain access to through the connector",
    )

    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The stack component labels.",
    )

    component_spec_path: Optional[str] = Field(
        default=None,
        title="The path to the component spec used for mlstacks deployments.",
    )


# -------- #
# RESPONSE #
# -------- #


class ComponentResponseModel(ComponentBaseModel, ShareableResponseModel):
    """Response model for stack components."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["type", "flavor"]

    connector: Optional["ServiceConnectorResponseModel"] = Field(
        default=None,
        title="The service connector linked to this stack component.",
    )


# ------ #
# FILTER #
# ------ #


class ComponentFilterModel(ShareableWorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all ComponentModels.

    The Component Model needs additional scoping. As such the `_scope_user`
    field can be set to the user that is doing the filtering. The
    `generate_filter()` method of the baseclass is overwritten to include the
    scoping.
    """

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ShareableWorkspaceScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "scope_type",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ShareableWorkspaceScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "scope_type",
    ]
    scope_type: Optional[str] = Field(
        default=None,
        description="The type to scope this query to.",
    )

    is_shared: Optional[Union[bool, str]] = Field(
        default=None, description="If the stack is shared or private"
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the stack component",
    )
    flavor: Optional[str] = Field(
        default=None,
        description="Flavor of the stack component",
    )
    type: Optional[str] = Field(
        default=None,
        description="Type of the stack component",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the stack component"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User of the stack"
    )
    connector_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Connector linked to the stack component"
    )

    def set_scope_type(self, component_type: str) -> None:
        """Set the type of component on which to perform the filtering to scope the response.

        Args:
            component_type: The type of component to scope the query to.
        """
        self.scope_type = component_type

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the filter for the query.

        Stack components can be scoped by type to narrow the search.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlalchemy import and_

        base_filter = super().generate_filter(table)
        if self.scope_type:
            type_filter = getattr(table, "type") == self.scope_type
            return and_(base_filter, type_filter)
        return base_filter


# ------- #
# REQUEST #
# ------- #


class ComponentRequestModel(ComponentBaseModel, ShareableRequestModel):
    """Request model for stack components."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["type", "flavor"]

    connector: Optional[UUID] = Field(
        default=None,
        title="The service connector linked to this stack component.",
    )

    @validator("name")
    def name_cant_be_a_secret_reference(cls, name: str) -> str:
        """Validator to ensure that the given name is not a secret reference.

        Args:
            name: The name to validate.

        Returns:
            The name if it is not a secret reference.

        Raises:
            ValueError: If the name is a secret reference.
        """
        if secret_utils.is_secret_reference(name):
            raise ValueError(
                "Passing the `name` attribute of a stack component as a "
                "secret reference is not allowed."
            )
        return name


# ------ #
# UPDATE #
# ------ #


@update_model
class ComponentUpdateModel(ComponentRequestModel):
    """Update model for stack components."""
