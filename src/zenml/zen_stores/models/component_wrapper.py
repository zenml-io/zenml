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
from zenml.logger import get_logger
from zenml.stack import StackComponent

logger = get_logger(__name__)


class ComponentWrapper(BaseModel):
    """Serializable Configuration of a StackComponent"""

    type: StackComponentType
    flavor: str
    name: str
    uuid: UUID
    config: bytes  # b64 encoded yaml config

    @classmethod
    def from_component(cls, component: StackComponent) -> "ComponentWrapper":
        """Creates a ComponentWrapper from an actual instance of a Stack
        Component.

        Args:
            component: the instance of a StackComponent
        """
        return cls(
            type=component.TYPE,
            flavor=component.FLAVOR,
            name=component.name,
            uuid=component.uuid,
            config=base64.b64encode(
                yaml.dump(json.loads(component.json())).encode()
            ),
        )

    def to_component(self) -> StackComponent:
        """Converts the ComponentWrapper into an actual instance of a Stack
        Component."""
        from zenml.repository import Repository
        from zenml.stack.registry import flavor_registry

        zenml_flavors = flavor_registry.get_flavors_by_type(
            component_type=self.type
        )

        try:
            # Try to find if there are any custom flavor implementations
            flavor_wrapper = Repository().zen_store.get_flavor_by_name_and_type(
                flavor_name=self.flavor,
                component_type=self.type,
            )

            # If there is one, check whether the same flavor exists as a default
            # flavor to give out a warning
            if self.flavor in zenml_flavors:
                logger.warning(
                    f"There is a custom implementation for the flavor "
                    f"'{self.flavor}' of a {self.type}, which is currently "
                    f"overwriting the same flavor provided by ZenML."
                )

        except KeyError:
            if self.flavor in zenml_flavors:
                flavor_wrapper = zenml_flavors[self.flavor]
            else:
                raise KeyError(
                    f"There is no flavor '{self.flavor}' for the type "
                    f"{self.type}"
                )

        flavor_class = flavor_wrapper.to_flavor()
        config = yaml.safe_load(base64.b64decode(self.config).decode())

        return flavor_class.parse_obj(config)
