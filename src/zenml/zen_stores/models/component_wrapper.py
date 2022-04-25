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

import base64
import json
from uuid import UUID

import yaml
from pydantic import BaseModel

from zenml.enums import StackComponentType
from zenml.stack import StackComponent
from zenml.zen_stores.models.flavor_wrapper import FlavorWrapper
from zenml.repository import Repository

class StackComponentWrapper(BaseModel):
    """Serializable Configuration of a StackComponent"""

    type: StackComponentType
    flavor: str
    name: str
    uuid: UUID
    config: bytes  # b64 encoded yaml config

    @classmethod
    def from_component(
        cls, component: StackComponent
    ) -> "StackComponentWrapper":
        return cls(
            type=component.TYPE,
            flavor=component.FLAVOR,
            name=component.name,
            uuid=component.uuid,
            config=base64.b64encode(
                yaml.dump(json.loads(component.json())).encode()
            ),
        )

    def to_component(self):
        flavor_wrapper = Repository().zen_store.get_flavor_by_name_and_type(
            flavor_name=self.flavor,
            component_type=self.type,
        )
        component_class = flavor.to_
        component_config = yaml.safe_load(
            base64.b64decode(wrapper.config).decode()
        )

        return component_class.parse_obj(component_config)
