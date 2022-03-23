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
from typing import List

from pydantic import BaseModel

from zenml.stack import Stack
from zenml.stack_stores.models import StackComponentWrapper


class StackWrapper(BaseModel):
    """Network Serializable Wrapper describing a Stack."""

    name: str
    components: List[StackComponentWrapper]

    @classmethod
    def from_stack(cls, stack: Stack) -> "StackWrapper":
        return cls(
            name=stack.name,
            components=[
                StackComponentWrapper.from_component(component)
                for t, component in stack.components.items()
            ],
        )
