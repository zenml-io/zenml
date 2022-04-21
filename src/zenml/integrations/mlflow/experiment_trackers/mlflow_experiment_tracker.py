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
from typing import ClassVar, Optional

from mlflow import (  # type: ignore[import]
    ActiveRun,
    get_experiment_by_name,
    search_runs,
    set_experiment,
    set_tracking_uri,
    start_run,
)
from mlflow.entities import Experiment  # type: ignore[import]

from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.constants import MLFLOW
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"
MLFLOW_TRACKING_TOKEN = "MLFLOW_TRACKING_TOKEN"
MLFLOW_TRACKING_INSECURE_TLS = "MLFLOW_TRACKING_INSECURE_TLS"

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
    tracking_uri: Optional[str] = None
    tracking_username: Optional[str] = None
    tracking_password: Optional[str] = None
    tracking_token: Optional[str] = None
    tracking_insecure_tls: bool = False

    def get_tracking_uri(self) -> str:
        """Resolves and returns the tracking URI."""
        if self.tracking_uri is None:
            return _local_mlflow_backend()
        return self.tracking_uri

    def prepare_pipeline_run(self) -> None:
        """Prepares running the pipeline."""
        if self.tracking_username:
            os.environ[MLFLOW_TRACKING_USERNAME] = self.tracking_username
        if self.tracking_password:
            os.environ[MLFLOW_TRACKING_PASSWORD] = self.tracking_password
        if self.tracking_token:
            os.environ[MLFLOW_TRACKING_TOKEN] = self.tracking_token
        set_tracking_uri(self.get_tracking_uri())
        os.environ[MLFLOW_TRACKING_INSECURE_TLS] = (
            "true" if self.tracking_insecure_tls else "false"
        )

    def cleanup_pipeline_run(self) -> None:
        """Cleans up resources after the pipeline run is finished."""
        set_tracking_uri("")

    @property
    def validator(self) -> Optional["StackValidator"]:
        """The optional validator of the stack component.

        This validator will be called each time a stack with the stack
        component is initialized. Subclasses should override this property
        and return a `StackValidator` that makes sure they're not included in
        any stack that they're not compatible with.
        """
        return None

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run locally."""
        return True

    @property
    def is_running(self) -> bool:
        """If the component is running locally."""
        return True

    def provision(self) -> None:
        """Provisions resources to run the component locally."""
        raise NotImplementedError(
            f"Provisioning local resources not implemented for {self}."
        )

    def deprovision(self) -> None:
        """Deprovisions all local resources of the component."""
        raise NotImplementedError(
            f"Deprovisioning local resource not implemented for {self}."
        )
