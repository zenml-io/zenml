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

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Type, cast

from zenml.client import Client
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import StepRunResponse
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

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submit a step run.

        This method should submit the step run and return without waiting for
        it to finish.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.

        Raises:
            NotImplementedError: If the step operator does not implement this
                method.
        """
        raise NotImplementedError(
            "Submitting step runs is not implemented for "
            f"the {self.__class__.__name__} step operator."
        )

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Get the status of a step run.

        Args:
            step_run: The step run to get the status of.

        Raises:
            NotImplementedError: If the step operator does not implement this
                method.
        """
        raise NotImplementedError(
            "Getting the status of step runs is not implemented for "
            f"the {self.__class__.__name__} step operator."
        )

    def wait(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Wait for a step run to finish.

        Args:
            step_run: The step run to wait for.

        Returns:
            The final status of the step run.
        """
        sleep_interval = 1
        max_sleep_interval = 16

        while True:
            try:
                status = self.get_status(step_run)
            except Exception as e:
                logger.error(
                    "Failed to get status of step run `%s`: %s",
                    step_run.id,
                    e,
                )
                # Fall back to the status of the ZenML server
                status = (
                    Client().get_run_step(step_run.id, hydrate=False).status
                )

            if status.is_finished or status == ExecutionStatus.RETRYING:
                return status

            logger.debug(
                "Waiting for step run with ID %s to finish (current "
                "status: %s)",
                step_run.id,
                status,
            )
            time.sleep(sleep_interval)
            if sleep_interval < max_sleep_interval:
                sleep_interval *= 2

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancel a step run.

        Args:
            step_run: The step run to cancel.

        Raises:
            NotImplementedError: If the step operator does not implement this
                method.
        """
        raise NotImplementedError(
            "Canceling step runs is not implemented for "
            f"the {self.__class__.__name__} step operator."
        )


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
