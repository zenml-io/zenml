#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from zenml.enums import OrchestratorFlavor, StackComponentType
from zenml.new_core.stack_component import StackComponent

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all ZenML orchestrators."""

    @property
    def type(self) -> StackComponentType:
        """The component type."""
        return StackComponentType.ORCHESTRATOR

    @property
    @abstractmethod
    def flavor(self) -> OrchestratorFlavor:
        """The orchestrator flavor."""

    @abstractmethod
    def run(
        self, pipeline: "BasePipeline", run_name: str, **kwargs: Any
    ) -> Any:
        """Abstract method to run a pipeline. Overwrite this in subclasses
        with a concrete implementation on how to run the given pipeline.

        Args:
            pipeline: The pipeline to run.
            run_name: Name of the pipeline run.
            **kwargs: Potential additional parameters used in subclass
                implementations.
        """

    def pre_run(self, pipeline: "BasePipeline", caller_filepath: str) -> None:
        """Should be run before the `run()` function to prepare orchestrator.

        Args:
            pipeline: Pipeline that will be run.
            caller_filepath: Path to the file in which `pipeline.run()` was
                called. This is necessary for airflow so we know the file in
                which the DAG is defined.
        """

    def post_run(self) -> None:
        """Should be run after the `run()` to clean up."""
