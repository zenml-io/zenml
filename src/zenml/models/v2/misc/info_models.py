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

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.models.v2.core.component import ComponentResponse


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


class ResourcesInfo(BaseModel):
    """Information about the resources needed for CLI and UI."""

    flavor: str
    flavor_display_name: str
    required_configuration: Dict[str, str] = {}
    use_resource_value_as_fixed_config: bool = False

    accessible_by_service_connector: List[str]
    connected_through_service_connector: List["ComponentResponse"]

    @model_validator(mode="after")
    def _validate_resource_info(self) -> "ResourcesInfo":
        if (
            self.use_resource_value_as_fixed_config
            and len(self.required_configuration) > 1
        ):
            raise ValueError(
                "Cannot use resource value as fixed config if more than "
                "one required configuration key is provided."
            )
        return self


class ServiceConnectorResourcesInfo(BaseModel):
    """Information about the service connector resources needed for CLI and UI."""

    connector_type: str

    components_resources_info: Dict[StackComponentType, List[ResourcesInfo]]
