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
"""Models representing full stack requests."""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import StackComponentType
from zenml.models.v2.base.scoped import WorkspaceScopedRequest


class ServiceConnectorInfo(BaseModel):
    """Information about the service connector when creating a full stack."""

    type: str
    auth_method: str
    configuration: Dict[str, Any] = {}


class ComponentInfo(BaseModel):
    """Information about each stack components when creating a full stack."""

    flavor: str
    service_connector_index: Optional[int] = Field(
        default=None,
        title="The id of the service connector from the list "
        "`service_connectors`.",
        description="The id of the service connector from the list "
        "`service_connectors` from `FullStackRequest`.",
    )
    service_connector_resource_id: Optional[str] = None
    configuration: Dict[str, Any] = {}


class FullStackRequest(WorkspaceScopedRequest):
    """Request model for a full-stack."""

    name: str = Field(
        title="The name of the stack.", max_length=STR_FIELD_MAX_LENGTH
    )
    description: Optional[str] = Field(
        default="",
        title="The description of the stack",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    service_connectors: List[Union[UUID, ServiceConnectorInfo]] = Field(
        default=[],
        title="The service connectors dictionary for the full stack "
        "registration.",
        description="The UUID of an already existing service connector or "
        "request information to create a service connector from "
        "scratch.",
    )
    components: Dict[StackComponentType, Union[UUID, ComponentInfo]] = Field(
        title="The mapping for the components of the full stack registration.",
        description="The mapping from component types to either UUIDs of "
        "existing components or request information for brand new "
        "components.",
    )

    @model_validator(mode="after")
    def _validate_indexes_in_components(self) -> "FullStackRequest":
        for component in self.components.values():
            if isinstance(component, ComponentInfo):
                if component.service_connector_index is not None:
                    if (
                        component.service_connector_index < 0
                        or component.service_connector_index
                        >= len(self.service_connectors)
                    ):
                        raise ValueError(
                            f"Service connector index {component.service_connector_index} "
                            "is out of range. Please provide a valid index referring to "
                            "the position in the list of service connectors."
                        )
        return self
