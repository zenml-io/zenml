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
"""Implementation of the MLflow experiment tracker for ZenML."""

import os
from typing import Optional, Tuple

import mlflow  # type: ignore[import]
from mlflow.entities import Experiment  # type: ignore[import]

from zenml.artifact_stores import LocalArtifactStore
from zenml.environment import Environment
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor import (
    is_databricks_tracking_uri,
    is_remote_mlflow_tracking_uri,
)
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.stack import StackValidator

logger = get_logger(__name__)


MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"
MLFLOW_TRACKING_TOKEN = "MLFLOW_TRACKING_TOKEN"
MLFLOW_TRACKING_INSECURE_TLS = "MLFLOW_TRACKING_INSECURE_TLS"

DATABRICKS_HOST = "DATABRICKS_HOST"
DATABRICKS_USERNAME = "DATABRICKS_USERNAME"
DATABRICKS_PASSWORD = "DATABRICKS_PASSWORD"
DATABRICKS_TOKEN = "DATABRICKS_TOKEN"


class MLFlowExperimentTracker(BaseExperimentTracker):
    """Stores Mlflow configuration options.

    ZenML should take care of configuring MLflow for you, but should you still
    need access to the configuration inside your step you can do it using a
    step context:
    ```python
    from zenml.steps import StepContext

    @enable_mlflow
    @step
    def my_step(context: StepContext, ...)
        context.stack.experiment_tracker  # get the tracking_uri etc. from here
    ```
    """

    @staticmethod
    def _local_mlflow_backend() -> str:
        """Gets the local MLflow backend inside the ZenML artifact repository directory.

        Returns:
            The MLflow tracking URI for the local MLflow backend.
        """
        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        artifact_store = repo.active_stack.artifact_store
        local_mlflow_backend_uri = os.path.join(artifact_store.path, "mlruns")
        if not os.path.exists(local_mlflow_backend_uri):
            os.makedirs(local_mlflow_backend_uri)
        return "file:" + local_mlflow_backend_uri

    def get_tracking_uri(self) -> str:
        """Returns the configured tracking URI or a local fallback.

        Returns:
            The tracking URI.
        """
        return self.config.tracking_uri or self._local_mlflow_backend()

    def configure_mlflow(self) -> None:
        """Configures the MLflow tracking URI and any additional credentials."""
        tracking_uri = self.get_tracking_uri()
        mlflow.set_tracking_uri(tracking_uri)

        if is_databricks_tracking_uri(tracking_uri):
            if self.config.databricks_host:
                os.environ[DATABRICKS_HOST] = self.config.databricks_host
            if self.config.tracking_username:
                os.environ[DATABRICKS_USERNAME] = self.config.tracking_username
            if self.config.tracking_password:
                os.environ[DATABRICKS_PASSWORD] = self.config.tracking_password
            if self.config.tracking_token:
                os.environ[DATABRICKS_TOKEN] = self.config.tracking_token
        else:
            if self.config.tracking_username:
                os.environ[
                    MLFLOW_TRACKING_USERNAME
                ] = self.config.tracking_username
            if self.config.tracking_password:
                os.environ[
                    MLFLOW_TRACKING_PASSWORD
                ] = self.config.tracking_password
            if self.config.tracking_token:
                os.environ[MLFLOW_TRACKING_TOKEN] = self.config.tracking_token

        os.environ[MLFLOW_TRACKING_INSECURE_TLS] = (
            "true" if self.config.tracking_insecure_tls else "false"
        )

    def prepare_step_run(self) -> None:
        """Sets the MLflow tracking uri and credentials."""
        self.configure_mlflow()

    def cleanup_step_run(self) -> None:
        """Resets the MLflow tracking uri."""
        mlflow.set_tracking_uri("")

    @property
    def local_path(self) -> Optional[str]:
        """Path to the local directory where the MLflow artifacts are stored.

        Returns:
            None if configured with a remote tracking URI, otherwise the
            path to the local MLflow artifact store directory.
        """
        tracking_uri = self.get_tracking_uri()
        if is_remote_mlflow_tracking_uri(tracking_uri):
            return None
        else:
            assert tracking_uri.startswith("file:")
            return tracking_uri[5:]

    @property
    def validator(self) -> Optional["StackValidator"]:
        """Checks the stack has a `LocalArtifactStore` if no tracking uri was specified.

        Returns:
            An optional `StackValidator`.
        """
        if self.config.tracking_uri:
            # user specified a tracking uri, do nothing
            return None
        else:
            # try to fall back to a tracking uri inside the zenml artifact
            # store. this only works in case of a local artifact store, so we
            # make sure to prevent stack with other artifact stores for now
            return StackValidator(
                custom_validation_function=lambda stack: (
                    isinstance(stack.artifact_store, LocalArtifactStore),
                    "MLflow experiment tracker without a specified tracking "
                    "uri only works with a local artifact store.",
                )
            )

    @property
    def active_experiment(self) -> Optional[Experiment]:
        """Returns the currently active MLflow experiment.

        Returns:
            The active experiment or `None` if no experiment is active.
        """
        step_env = Environment().step_environment

        if not step_env:
            # we're not inside a step
            return None

        # If using Databricks, then we need to append an slash to the name of
        # the experiment because Databricks needs it to be an absolute path
        # within the Databricks workspace.
        experiment_name = (
            f"/{step_env.pipeline_name}"
            if self.config.tracking_uri
            and is_databricks_tracking_uri(self.config.tracking_uri)
            else step_env.pipeline_name
        )

        mlflow.set_experiment(experiment_name=experiment_name)
        return mlflow.get_experiment_by_name(experiment_name)

    def _find_active_run(
        self,
    ) -> Tuple[Optional[mlflow.ActiveRun], Optional[str], Optional[str]]:
        """Find the currently active MLflow run.

        Returns:
            The active MLflow run, the experiment id and the run id
        """
        step_env = Environment().step_environment

        if not self.active_experiment or not step_env:
            return None, None, None

        experiment_id = self.active_experiment.experiment_id

        # TODO [ENG-458]: find a solution to avoid race-conditions while
        #  creating the same MLflow run from parallel steps
        runs = mlflow.search_runs(
            experiment_ids=[experiment_id],
            filter_string=f'tags.mlflow.runName = "{step_env.pipeline_run_id}"',
            output_format="list",
        )

        run_id = runs[0].info.run_id if runs else None

        current_active_run = mlflow.active_run()
        if not (
            current_active_run and current_active_run.info.run_id == run_id
        ):
            current_active_run = None

        return current_active_run, experiment_id, run_id

    @property
    def active_run(self) -> Optional[mlflow.ActiveRun]:
        """Returns the currently active MLflow run.

        Returns:
            The active MLflow run.
        """
        step_env = Environment().step_environment
        current_active_run, experiment_id, run_id = self._find_active_run()
        if current_active_run:
            return current_active_run
        else:
            return mlflow.start_run(
                run_id=run_id,
                run_name=step_env.pipeline_run_id,
                experiment_id=experiment_id,
            )

    @property
    def active_nested_run(self) -> Optional[mlflow.ActiveRun]:
        """Returns a nested run in the currently active MLflow run.

        Returns:
            The nested MLflow run.
        """
        step_env = Environment().step_environment
        current_active_run, _, _ = self._find_active_run()
        if current_active_run:
            return mlflow.start_run(run_name=step_env.step_name, nested=True)
        else:
            # Return None
            return current_active_run
