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
"""Base class for all ZenML experiment trackers."""

from abc import ABC, abstractmethod
from typing import Type, cast

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseExperimentTrackerConfig(StackComponentConfig):
    """Base config for experiment trackers."""


class BaseExperimentTracker(StackComponent, ABC):
    """Base class for all ZenML experiment trackers."""

    @property
    def config(self) -> BaseExperimentTrackerConfig:
        """Returns the config of the experiment tracker.

        Returns:
            The config of the experiment tracker.
        """
        return cast(BaseExperimentTrackerConfig, self._config)


class BaseExperimentTrackerFlavor(Flavor):
    """Base class for all ZenML experiment tracker flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            StackComponentType: The type of the flavor.
        """
        return StackComponentType.EXPERIMENT_TRACKER

    @property
    def config_class(self) -> Type[BaseExperimentTrackerConfig]:
        """Config class for this flavor.

        Returns:
            The config class for this flavor.
        """
        return BaseExperimentTrackerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[StackComponent]:
        """Returns the implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return BaseExperimentTracker
