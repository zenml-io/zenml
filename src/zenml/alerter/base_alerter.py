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

from abc import ABC
from typing import Any, ClassVar, Optional

from zenml.enums import StackComponentType
from zenml.stack import StackComponent
from zenml.steps.step_interfaces.base_alerter_step import BaseAlerterStepConfig


class BaseAlerter(StackComponent, ABC):
    """Base class for all ZenML alerters."""

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.ALERTER
    FLAVOR: ClassVar[str]

    def post(
        self, message: str, config: Optional[BaseAlerterStepConfig]
    ) -> bool:
        """Post a message to some ChatOps service.

        Args:
            message: Message to be posted.
            config: Optional runtime configuration of this function.

        Returns:
            True if operation succeeded, else False
        """
        return True

    def ask(
        self, question: str, config: Optional[BaseAlerterStepConfig]
    ) -> Any:
        """Ask a question and get a synchronous response.

        Args:
            question: Question to ask.
            config: Optional runtime configuration of this function.

        Returns:
            The response from the request.
        """
        return None
