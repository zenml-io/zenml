#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import List

from zenml.integrations.mlflow.experiment_trackers import (
    MLFlowExperimentTracker,
)
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.stack import Stack, StackComponent

logger = get_logger(__name__)


class ExampleConfiguration(ABC):
    """Configuration options for testing a ZenML example.

    Attributes:
        name: The name (=directory name) of the example
    """

    name: str
    runs_on_windows: bool
    required_stack_components: List[StackComponent] = list()
    pipeline_name: str
    step_count: int

    def duplicate_and_update_stack(self) -> None:
        repo = Repository()
        components = repo.active_stack.components

        for component in self.required_stack_components:
            components[component.TYPE] = component
        stack = Stack.from_components(
            name=f"{self.name}_stack", components=components
        )
        repo.register_stack(stack)
        repo.activate_stack(stack.name)


class XGBoostExample(ExampleConfiguration):
    name = "xgboost"
    runs_on_windows = False
    pipeline_path = "xgboost/pipelines/training_pipeline/training_pipeline"
    pipeline_name = "xgboost_pipeline"
    step_count = 3


class MLflowTrackingExample(ExampleConfiguration):
    name = "mlflow_tracking"
    runs_on_windows = True
    required_stack_components = [MLFlowExperimentTracker(name="mlflow_tracker")]


EXAMPLES = [XGBoostExample, MLflowTrackingExample]
