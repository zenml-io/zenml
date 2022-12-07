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
"""Models representing stacks."""

import json
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Type, Union
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field, PrivateAttr

from zenml.enums import StackComponentType
from zenml.models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update_model,
)
from zenml.models.component_models import ComponentResponseModel
from zenml.models.filter_models import FilterBaseModel

from zenml.models.constants import STR_FIELD_MAX_LENGTH
if TYPE_CHECKING:
    from sqlmodel import SQLModel


# ---- #
# BASE #
# ---- #


class StackBaseModel(BaseModel):
    """Base model for stacks."""

    name: str = Field(
        title="The name of the stack.", max_length=STR_FIELD_MAX_LENGTH
    )
    description: str = Field(
        default="",
        title="The description of the stack",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class StackResponseModel(StackBaseModel, ShareableResponseModel):
    """Stack model with Components, User and Project fully hydrated."""

    components: Dict[StackComponentType, List[ComponentResponseModel]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Add the stack components to the stack analytics metadata.

        Returns:
            Dict of analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata.update({ct: c[0].flavor for ct, c in self.components.items()})
        return metadata

    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.

        Returns:
            True if the stack is valid, False otherwise.
        """
        return (
            StackComponentType.ARTIFACT_STORE in self.components
            and StackComponentType.ORCHESTRATOR in self.components
        )

    def to_yaml(self) -> Dict[str, Any]:
        """Create yaml representation of the Stack Model.

        Returns:
            The yaml representation of the Stack Model.
        """
        component_data = {}
        for component_type, components_list in self.components.items():
            component = components_list[0]
            component_dict = json.loads(
                component.json(
                    include={"name", "type", "flavor", "configuration"}
                )
            )
            component_data[component_type.value] = component_dict

        # write zenml version and stack dict to YAML
        yaml_data = {
            "stack_name": self.name,
            "components": component_data,
        }

        return yaml_data


# ------ #
# FILTER #
# ------ #


class StackFilterModel(FilterBaseModel):
    """Model to enable advanced filtering of all StackModels.

    The Stack Model needs additional scoping. As such the `_scope_user` field
    can be set to the user that is doing the filtering. The
    `generate_filter()` method of the baseclass is overwritten to include the
    scoping.
    """

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        "sort_by",
        "list_of_filters",
        "_scope_user",
        "page",
        "size",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = ["list_of_filters", "_scope_user"]

    _scope_user: UUID = PrivateAttr(None)

    is_shared: Union[bool, str] = Query(
        None, description="If the stack is shared or private"
    )
    name: str = Query(
        None,
        description="Name of the stack",
    )
    description: str = Query(None, description="Description of the stack")
    project_id: Union[UUID, str] = Query(
        None, description="Project of the stack"
    )
    user_id: Union[UUID, str] = Query(None, description="User of the stack")
    component_id: Union[UUID, str] = Query(
        None, description="Component in the stack"
    )

    def set_scope_user(self, user_id: UUID):
        """Set the user that is performing the filtering to scope the response."""
        self._scope_user = user_id

    def generate_filter(self, table: Type["SQLModel"]):
        """A User is only allowed to list the stacks that either belong to them or that are shared.

        The resulting filter from this method will be the union of the scoping
        filter (owned by user OR shared) with the user provided filters.

        Args:
            table: The Table that is being queried from.

        Returns:
            A list of all filters to use for the query
        """
        from sqlmodel import or_

        ands = []
        for column_filter in self.list_of_filters:
            ands.append(column_filter.generate_query_conditions(table=table))

        if self._scope_user:
            ands.append(
                or_(
                    getattr(table, "user_id") == self._scope_user,
                    getattr(table, "is_shared") is True,
                )
            )
            return ands
        else:
            return ands


# ------- #
# REQUEST #
# ------- #


class StackRequestModel(StackBaseModel, ShareableRequestModel):
    """Stack model with components, user and project as UUIDs."""

    components: Dict[StackComponentType, List[UUID]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )

    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.

        Returns:
            True if the stack is valid, False otherwise.
        """
        return (
            StackComponentType.ARTIFACT_STORE in self.components
            and StackComponentType.ORCHESTRATOR in self.components
        )


# ------ #
# UPDATE #
# ------ #


@update_model
class StackUpdateModel(StackRequestModel):
    """The update model for stacks."""
