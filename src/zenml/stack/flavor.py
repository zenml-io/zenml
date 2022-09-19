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
"""Base ZenML Flavor implementation"""

from abc import abstractmethod
from typing import Optional, Type

from zenml.models import FlavorModel
from zenml.stack.stack_component import (
    StackComponent,
    StackComponentConfig,
    StackComponentType,
)
from zenml.utils.source_utils import load_source_path_class, resolve_class


class Flavor:
    @property
    @abstractmethod
    def name(self) -> str:
        """"""

    @property
    @abstractmethod
    def type(self) -> StackComponentType:
        """"""

    @property
    @abstractmethod
    def implementation_class(self) -> Type[StackComponent]:
        """"""

    @property
    @abstractmethod
    def config_class(self) -> Type[StackComponentConfig]:
        """"""

    @property
    def config_schema(self) -> str:
        """"""
        return self.config_class.schema_json()

    @classmethod
    def from_model(cls, flavor_model: FlavorModel) -> "Flavor":
        return load_source_path_class(flavor_model.source)()  # noqa

    def to_model(self, integration: Optional[str] = None) -> FlavorModel:
        from zenml.repository import Repository

        repo = Repository()

        model = FlavorModel(
            user=repo.active_user.id,
            project=repo.active_project.id,
            name=self.name,
            type=self.type,
            source=resolve_class(self.__class__),  # noqa
            config_schema=self.config_schema,
        )
        if integration:
            model.integration = integration

        return model
