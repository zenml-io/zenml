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
from typing import Optional, Type, Union, cast

from pydantic import BaseModel

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.models.v2.misc.alerter_models import AlerterMessage
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig

logger = get_logger(__name__)


class BaseAlerterStepParameters(BaseModel):
    """Step parameters definition for all alerters."""


class BaseAlerterConfig(StackComponentConfig):
    """Base config for alerters."""


class BaseAlerter(StackComponent, ABC):
    """Base class for all ZenML alerters."""

    @property
    def config(self) -> BaseAlerterConfig:
        """Returns the `BaseAlerterConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseAlerterConfig, self._config)

    def post(
        self,
        message: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a chat service.

        This method can handle either a plain string or an AlerterMessage object.
        Subclasses should parse and format the message if it's an AlerterMessage,
        then send it to the respective service.

        Args:
            message: A string or an AlerterMessage containing alert info.
            params: Optional parameters of this function.

        Returns:
            bool: True if operation succeeded, else False.
        """
        if isinstance(message, str):
            logger.warning(
                "Passing string messages to alerter.post() is deprecated. "
                "Please use AlerterMessage objects instead for better structured alerts. "
                "Example: AlerterMessage(title='Alert Title', body='Alert body', metadata={...})"
            )
        return True

    def ask(
        self,
        question: Union[str, AlerterMessage],
        params: Optional[BaseAlerterStepParameters] = None,
    ) -> bool:
        """Post a message to a chat service and wait for approval.

        This can be useful to easily get a human in the loop, e.g., when
        deploying models.

        Args:
            question: Question to ask (either a string message or AlerterMessage to be posted).
            params: Optional parameters of this function.

        Returns:
            bool: True if operation succeeded and was approved, else False.
        """
        if isinstance(question, str):
            logger.warning(
                "Passing string messages to alerter.ask() is deprecated. "
                "Please use AlerterMessage objects instead for better structured alerts. "
                "Example: AlerterMessage(title='Question Title', body='Question body', metadata={...})"
            )
        return True


class BaseAlerterFlavor(Flavor, ABC):
    """Base class for all ZenML alerter flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.ALERTER

    @property
    def config_class(self) -> Type[BaseAlerterConfig]:
        """Returns BaseAlerterConfig class.

        Returns:
            The BaseAlerterConfig class.
        """
        return BaseAlerterConfig

    @property
    def implementation_class(self) -> Type[BaseAlerter]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return BaseAlerter
