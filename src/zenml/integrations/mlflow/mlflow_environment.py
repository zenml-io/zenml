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
from typing import Optional

from mlflow import (  # type: ignore [import]
    ActiveRun,
    get_experiment_by_name,
    search_runs,
    set_experiment,
    set_tracking_uri,
    start_run,
)
from mlflow.entities import Experiment  # type: ignore [import]

from zenml.environment import BaseEnvironmentComponent
from zenml.logger import get_logger
from zenml.repository import Repository

logger = get_logger(__name__)

MLFLOW_ENVIRONMENT_NAME = "mlflow"
MLFLOW_STEP_ENVIRONMENT_NAME = "mlflow_step"


class MLFlowEnvironment(BaseEnvironmentComponent):
    """Manages the global MLflow environment in the form of an Environment
    component. To access it inside your step function or in the post-execution
    workflow:

    ```python
    from zenml.environment import Environment
    from zenml.integrations.mlflow.mlflow_environment import MLFLOW_ENVIRONMENT_NAME


    @step
    def my_step(...)
        env = Environment[MLFLOW_ENVIRONMENT_NAME]
        do_something_with(env.mlflow_tracking_uri)
    ```

    """

    NAME = MLFLOW_ENVIRONMENT_NAME

    def __init__(self) -> None:
        """Initialize a MLflow environment component."""
        super().__init__()
        # TODO [ENG-316]: Implement a way to get the mlflow token and set
        #  it as env variable at MLFLOW_TRACKING_TOKEN
        self._mlflow_tracking_uri = self._local_mlflow_backend()

    @staticmethod
    def _local_mlflow_backend() -> str:
        """Returns the local mlflow backend inside the zenml artifact
        repository directory

        Returns:
            The MLflow tracking URI for the local mlflow backend.
        """
        repo = Repository()
        artifact_store = repo.active_stack.artifact_store
        local_mlflow_backend_uri = os.path.join(artifact_store.path, "mlruns")
        if not os.path.exists(local_mlflow_backend_uri):
            os.makedirs(local_mlflow_backend_uri)
            # TODO [medium]: safely access (possibly non-existent) artifact stores
        return "file:" + local_mlflow_backend_uri

    def activate(self) -> None:
        """Activate the MLflow environment for the current stack."""
        logger.debug(
            "Setting the MLflow tracking uri to %s", self._mlflow_tracking_uri
        )
        set_tracking_uri(self._mlflow_tracking_uri)
        return super().activate()

    def deactivate(self) -> None:
        logger.debug("Resetting the MLflow tracking uri to local")
        set_tracking_uri("")
        return super().deactivate()

    @property
    def tracking_uri(self) -> str:
        """Returns the MLflow tracking URI for the current stack."""
        return self._mlflow_tracking_uri


class MLFlowStepEnvironment(BaseEnvironmentComponent):
    """Provides information about an MLflow step environment.
    To access it inside your step function:

    ```python
    from zenml.environment import Environment
    from zenml.integrations.mlflow.mlflow_environment import MLFLOW_STEP_ENVIRONMENT_NAME


    @step
    def my_step(...)
        env = Environment[MLFLOW_STEP_ENVIRONMENT_NAME]
        do_something_with(env.mlflow_tracking_uri)
    ```

    """

    NAME = MLFLOW_STEP_ENVIRONMENT_NAME

    def __init__(self, experiment_name: str, run_name: str):
        """Initialize a MLflow step environment component.

        Args:
            experiment_name: the experiment name under which all MLflow
                artifacts logged under the current step will be tracked.
                If no MLflow experiment with this name exists, one will
                be created when the environment component is activated.
            run_name: the name of the MLflow run associated with the current
                step. If a run with this name does not exist, one will be
                created when the environment component is activated,
                otherwise the existing run will be reused.
        """
        super().__init__()
        self._experiment_name = experiment_name
        self._experiment = None
        self._run_name = run_name
        self._run = None

    def _create_or_reuse_mlflow_run(self) -> None:
        """Create or reuse an MLflow run for the current step.

        IMPORTANT: this function might cause a race condition. If two or more
        processes call it at the same time and with the same arguments, it could
        lead to a situation where two or more MLflow runs with the same name
        and different IDs are created.
        """
        # Set which experiment is used within mlflow
        logger.debug(
            "Setting the MLflow experiment name to %s", self._experiment_name
        )
        set_experiment(self._experiment_name)
        self._experiment = get_experiment_by_name(self._experiment_name)
        if self._experiment is None:
            raise RuntimeError(
                f"Failed to create or reuse MLflow "
                f"experiment {self._experiment_name}"
            )
        experiment_id = self._experiment.experiment_id

        # TODO [ENG-458]: find a solution to avoid race-conditions while creating
        #   the same MLflow run from parallel steps
        runs = search_runs(
            experiment_ids=[experiment_id],
            filter_string=f'tags.mlflow.runName = "{self._run_name}"',
            output_format="list",
        )
        if runs:
            run_id = runs[0].info.run_id
            self._run = start_run(run_id=run_id, experiment_id=experiment_id)
        else:
            self._run = start_run(
                run_name=self._run_name, experiment_id=experiment_id
            )
        if self._run is None:
            raise RuntimeError(
                f"Failed to create or reuse MLflow "
                f"run {self._run_name} for experiment {self._experiment_name}"
            )

    def activate(self) -> None:
        """Activate the MLflow environment for the current step."""

        self._create_or_reuse_mlflow_run()
        return super().activate()

    def deactivate(self) -> None:
        return super().deactivate()

    @property
    def mlflow_experiment_name(self) -> str:
        """Returns the MLflow experiment name for the current step."""
        return self._experiment_name

    @property
    def mlflow_run_name(self) -> str:
        """Returns the MLflow run name for the current step."""
        return self._run_name

    @property
    def mlflow_experiment(self) -> Optional[Experiment]:
        """Returns the MLflow experiment object for the current step."""
        return self._experiment

    @property
    def mlflow_run(self) -> Optional[ActiveRun]:
        """Returns the MLflow run for the current step."""
        return self._run
