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
"""Base class for all ZenML alerters."""

from abc import ABC
from typing import Optional, Type

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig
from zenml.steps.step_interfaces.base_alerter_step import BaseAlerterStepConfig


class BaseAlerterConfig(StackComponentConfig):
    """Base config for alerters."""


class BaseAlerter(StackComponent, ABC):
    """Base class for all ZenML alerters."""

    def post(
        self, message: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a chat service.

        Args:
            message (str): Message to be posted.
            config (Optional[BaseAlerterStepConfig]): Optional runtime
                configuration of this function.

        Returns:
            bool: True if operation succeeded, else False.
        """
        return True

    def ask(
        self, question: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to a chat service and wait for approval.

        This can be useful to easily get a human in the loop, e.g., when
        deploying models.

        Args:
            question (str): Question to ask (message to be posted).
            config (Optional[BaseAlerterStepConfig]): Optional runtime
                configuration of this function.

        Returns:
            bool: True if operation succeeded and was approved, else False.
        """
        return True


class BaseAlerterFlavor(Flavor):
    """Base class for all ZenML alerter flavors."""

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.ALERTER

    @property
    def config_class(self) -> Type[BaseAlerterConfig]:
        return BaseAlerterConfig

    @property
    def implementation_class(self) -> Type[BaseAlerter]:
        return BaseAlerter
