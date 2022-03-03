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

from abc import ABC, abstractmethod
from typing import Dict, List

from zenml.enums import StackComponentType
from zenml.stack import Stack, StackComponent
from zenml.stack_stores.models import StackConfiguration


class BaseStackStore(ABC):
    """Base class for accessing data in ZenML Repository and new Service."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Get the ZenML version."""

    @property
    @abstractmethod
    def stacks(self) -> List[Stack]:
        """All stacks registered in this repository."""

    @property
    @abstractmethod
    def stack_configurations(self) -> Dict[str, StackConfiguration]:
        """Configuration for all stacks registered in this repository."""

    @property
    @abstractmethod
    def active_stack_name(self) -> str:
        """The name of the active stack for this repository."""

    @property
    def active_stack(self) -> Stack:
        """The active stack for this repository."""

    @abstractmethod
    def activate_stack(self, name: str) -> None:
        """Activates the stack for the given name."""

    @abstractmethod
    def get_stack(self, name: str) -> Stack:
        """Fetches a stack."""

    @abstractmethod
    def register_stack(self, stack: Stack) -> Dict[str, str]:
        """Registers a stack and it's components, returning metadata."""

    @abstractmethod
    def deregister_stack(self, name: str) -> None:
        """Deregisters a stack."""

    @abstractmethod
    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponent]:
        """Fetches all registered stack components of the given type."""

    @abstractmethod
    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> StackComponent:
        """Fetches a registered stack component."""

    @abstractmethod
    def register_stack_component(
        self,
        component: StackComponent,
    ) -> None:
        """Registers a stack component."""

    @abstractmethod
    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component."""
