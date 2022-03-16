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

from typing import Optional

from pydantic import BaseModel

from zenml.enums import StackComponentType


class StackConfiguration(BaseModel):
    """Pydantic object used for serializing stack configuration options."""

    orchestrator: str
    metadata_store: str
    artifact_store: str
    container_registry: Optional[str]
    step_operator: Optional[str]

    def contains_component(
        self, component_type: StackComponentType, name: str
    ) -> bool:
        """Checks if the stack contains a specific component."""
        return self.dict().get(component_type.value) == name

    class Config:
        """Pydantic configuration class."""

        allow_mutation = False
