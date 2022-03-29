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

from collections import defaultdict
from typing import DefaultDict, Dict

from pydantic import BaseModel, validator

from zenml.enums import StackComponentType


class StackStoreModel(BaseModel):
    """Pydantic object used for serializing a ZenML Stack Store.

    Attributes:
        stacks: Maps stack names to a configuration object containing the
            names and flavors of all stack components.
        stack_components: Contains names and flavors of all registered stack
            components.
    """

    stacks: Dict[str, Dict[StackComponentType, str]]
    stack_components: DefaultDict[StackComponentType, Dict[str, str]]

    @validator("stack_components")
    def _construct_defaultdict(
        cls, stack_components: Dict[StackComponentType, Dict[str, str]]
    ) -> DefaultDict[StackComponentType, Dict[str, str]]:
        """Ensures that `stack_components` is a defaultdict so stack
        components of a new component type can be added without issues."""
        return defaultdict(dict, stack_components)

    @classmethod
    def empty_store(cls) -> "StackStoreModel":
        """Initialize a new empty stack store with current zen version."""
        return cls(stacks={}, stack_components={})

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
