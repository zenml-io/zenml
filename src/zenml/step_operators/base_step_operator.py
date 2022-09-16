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
from typing import TYPE_CHECKING, List, Type

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig

if TYPE_CHECKING:
    from zenml.config.docker_configuration import DockerConfiguration
    from zenml.config.resource_configuration import ResourceConfiguration


class BaseStepOperatorConfig(StackComponentConfig):
    """Base config for step operators."""


class BaseStepOperator(StackComponent, ABC):
    """Base class for all ZenML step operators."""

    @abstractmethod
    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        docker_configuration: "DockerConfiguration",
        entrypoint_command: List[str],
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Abstract method to execute a step.

        Concrete step operator subclasses must implement the following
        functionality in this method:
        - Prepare the execution environment by copying user files and installing
          requirements as specified in the `docker_configuration`.
        - Launch a **synchronous** job that executes the `entrypoint_command`

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            docker_configuration: The Docker configuration for this step.
            entrypoint_command: Command that executes the step.
            resource_configuration: The resource configuration for this step.
        """


class BaseStepOperatorFlavor(Flavor):
    """Base class for all ZenML step operator flavors."""

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.STEP_OPERATOR

    @property
    def config_class(self) -> Type[BaseStepOperatorConfig]:
        return BaseStepOperatorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseStepOperator]:
        """Returns the implementation class for this flavor."""
