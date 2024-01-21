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
"""Base implementation of the event source configuration."""
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from pydantic import BaseModel, Extra


class ActionPlanConfig(BaseModel, ABC):
    """Allows configuring the action configuration."""

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
        # prevent extra attributes during model initialization
        extra = Extra.forbid


class ActionFlavorResponse(BaseModel):
    """Response model for Action Plans."""
    name: str
    config_schema: Dict[str, Any]


class BaseActionFlavor:
    """Base Action Flavor to register Action Plan Configurations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """

    @property
    @abstractmethod
    def config_class(self) -> Type[ActionPlanConfig]:
        """Returns `StackComponentConfig` config class.

        Returns:
            The config class.
        """

    @property
    def config_schema(self) -> Dict[str, Any]:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        config_schema: Dict[str, Any] = json.loads(
            self.config_class.schema_json()
        )
        return config_schema

    def to_model(self) -> ActionFlavorResponse:
        """Convert the Flavor into a Response Model."""
        return ActionFlavorResponse(name=self.name, config_schema=self.config_schema)