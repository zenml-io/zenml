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
from typing import TYPE_CHECKING, Any, List, Optional

from zenml.enums import StackComponentType, TrainingResourceFlavor
from zenml.stack import StackComponent

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack


class BaseTrainingResource(StackComponent, ABC):
    """Base class for all ZenML training resources."""

    _pipeline: Optional["BasePipeline"] = None
    _runtime_configuration: Optional["RuntimeConfiguration"] = None

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.TRAINING_RESOURCE

    @property
    @abstractmethod
    def flavor(self) -> TrainingResourceFlavor:
        """The training resource flavor."""

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        self._pipeline = pipeline
        self._runtime_configuration = runtime_configuration

    @abstractmethod
    def launch(
        self, pipeline_name: str, run_name: str, entrypoint_command: List[str], requirements: List[str]
    ) -> Any:
        """Launches a step on the training resource."""
        raise NotImplementedError
