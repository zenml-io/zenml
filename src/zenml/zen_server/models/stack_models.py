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
"""Stack Models for the API endpoint definitions."""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from zenml.enums import StackComponentType
from zenml.models import StackModel
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)
from zenml.zen_server.models.base_models import (
    ProjectScopedCreateRequest,
    UpdateRequest,
)


class CreateStackRequest(ProjectScopedCreateRequest[StackModel]):
    """Stack model for create requests."""

    _MODEL_TYPE = StackModel

    name: str = Field(
        title="The stack name.", max_length=MODEL_NAME_FIELD_MAX_LENGTH
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the stack",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )
    components: Dict[StackComponentType, List[UUID]] = Field(
        default=None,
        title=(
            "A mapping of stack component types to the id's of"
            "instances of components of this type."
        ),
    )
    is_shared: bool = Field(
        default=False,
        title="Flag describing if this stack is shared.",
    )


class UpdateStackRequest(UpdateRequest[StackModel]):
    """Stack model for update requests."""

    _MODEL_TYPE = StackModel

    name: Optional[str] = Field(
        default=None,
        title="The stack name.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The updated description of the stack",
        max_length=300,
    )
    components: Optional[Dict[StackComponentType, List[UUID]]] = Field(
        default=None,
        title=(
            "An updated mapping of stack component types to the id's of"
            "instances of components of this type."
        ),
    )
    is_shared: Optional[bool] = Field(
        default=None,
        title="Updated flag describing if this stack is shared.",
    )
