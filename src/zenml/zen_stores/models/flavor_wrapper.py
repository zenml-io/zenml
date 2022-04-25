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
from typing import Type

from pydantic import BaseModel

from zenml.enums import StackComponentType
from zenml.stack.stack_component import StackComponent


class FlavorWrapper(BaseModel):
    """Pydantic object representing the custom implementation of a stack
    component."""

    name: str
    integration: str = ""
    type: StackComponentType
    source: str

    @classmethod
    def from_flavor(cls, flavor: Type[StackComponent]) -> "FlavorWrapper":
        return FlavorWrapper(
            name=flavor.FLAVOR,
            type=flavor.TYPE,
            source=flavor.__module__ + "." + flavor.__name__,
        )

    def to_flavor(self):
        from zenml.utils.source_utils import load_source_path_class

        return load_source_path_class(source=self.source)
