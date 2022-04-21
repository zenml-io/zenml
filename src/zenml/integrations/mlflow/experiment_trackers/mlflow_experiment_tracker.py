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
import os
from typing import ClassVar

from pydantic import Field

from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.constants import MLFLOW
from zenml.logger import get_logger
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)


# Add validation
def _local_mlflow_backend() -> str:
    """Returns the local mlflow backend inside the zenml artifact
    repository directory

    Returns:
        The MLflow tracking URI for the local mlflow backend.
    """
    repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
    artifact_store = repo.active_stack.artifact_store
    local_mlflow_backend_uri = os.path.join(artifact_store.path, "mlruns")
    if not os.path.exists(local_mlflow_backend_uri):
        os.makedirs(local_mlflow_backend_uri)
        # TODO [MEDIUM]: safely access (possibly non-existent) artifact stores
    return "file:" + local_mlflow_backend_uri


@register_stack_component_class
class MLFlowExperimentTracker(BaseExperimentTracker):
    """Configure the MLFlow Experiment Tracker.

    Manages the global MLflow environment in the form of a Stack
    component. To access it inside your step function or in the post-execution
    workflow:

    ```python
    from zenml.steps import StepContext

    @enable_mlflow
    @step
    def my_step(context: StepContext, ...)
        context.stack.experiment_tracker  # This is the MLFlowExperimentTracker object
    ```
    """

    # Class Configuration
    FLAVOR: ClassVar[str] = MLFLOW
    tracking_uri: str = Field(default_factory=_local_mlflow_backend)
