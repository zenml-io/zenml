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
"""Base class for ZenML step operators."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Type, cast

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)


class BaseStepOperatorConfig(StackComponentConfig):
    """Base config for step operators."""


class BaseStepOperator(StackComponent, ABC):
    """Base class for all ZenML step operators."""

    @property
    def config(self) -> BaseStepOperatorConfig:
        """Returns the config of the step operator.

        Returns:
            The config of the step operator.
        """
        return cast(BaseStepOperatorConfig, self._config)

    @property
    def entrypoint_config_class(
        self,
    ) -> Type[StepOperatorEntrypointConfiguration]:
        """Returns the entrypoint configuration class for this step operator.

        Concrete step operator implementations may override this property
        to return a custom entrypoint configuration class if they need to
        customize the entrypoint configuration.

        Returns:
            The entrypoint configuration class for this step operator.
        """
        return StepOperatorEntrypointConfiguration

    @abstractmethod
    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Abstract method to execute a step.

        Subclasses must implement this method and launch a **synchronous**
        job that executes the `entrypoint_command`.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """


class BaseStepOperatorFlavor(Flavor):
    """Base class for all ZenML step operator flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The type of the flavor.
        """
        return StackComponentType.STEP_OPERATOR

    @property
    def config_class(self) -> Type[BaseStepOperatorConfig]:
        """Returns the config class for this flavor.

        Returns:
            The config class for this flavor.
        """
        return BaseStepOperatorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseStepOperator]:
        """Returns the implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
