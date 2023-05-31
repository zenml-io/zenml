#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Mixin classes for MLflow stack components."""


import os
from typing import Any, Dict, Optional, cast

import mlflow
from mlflow import MlflowClient
from mlflow.entities import Experiment, Run
from mlflow.store.db.db_types import DATABASE_ENGINES

from zenml.integrations.mlflow.mixins.mlflow_config_mixin import (
    MLFlowConfigMixin,
)
from zenml.integrations.mlflow.mlflow_utils import (
    is_databricks_tracking_uri,
    is_remote_mlflow_tracking_uri,
)
from zenml.logger import get_logger
from zenml.stack import StackValidator
from zenml.stack.stack_component import StackComponent

logger = get_logger(__name__)

MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"
MLFLOW_TRACKING_TOKEN = "MLFLOW_TRACKING_TOKEN"
MLFLOW_TRACKING_INSECURE_TLS = "MLFLOW_TRACKING_INSECURE_TLS"
MLFLOW_BACKEND_STORE_URI = "_MLFLOW_SERVER_FILE_STORE"

DATABRICKS_HOST = "DATABRICKS_HOST"
DATABRICKS_USERNAME = "DATABRICKS_USERNAME"
DATABRICKS_PASSWORD = "DATABRICKS_PASSWORD"
DATABRICKS_TOKEN = "DATABRICKS_TOKEN"

ZENML_TAG_KEY = "zenml"


class MLFlowStackComponentMixin(StackComponent):
    """Mixin class for MLflow stack components."""

    _client: Optional[MlflowClient] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the experiment tracker and validate the tracking uri.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self._ensure_valid_tracking_uri()

    @property
    def config(self) -> MLFlowConfigMixin:
        """Returns the config mixin that this stack component requires.

        Returns:
            The configuration.
        """
        return cast(MLFlowConfigMixin, self._config)

    # ================
    # Public interface
    # ================

    @property
    def tracking_uri(self) -> str:
        """Returns the configured tracking URI or a local fallback.

        Returns:
            The tracking URI.
        """
        return self.config.tracking_uri or self._get_local_mlflow_backend()

    @property
    def local_path(self) -> Optional[str]:
        """Path to the local directory where the MLflow artifacts are stored.

        Returns:
            None if configured with a remote tracking URI, otherwise the
            path to the local MLflow artifact store directory.
        """
        tracking_uri = self.tracking_uri
        if is_remote_mlflow_tracking_uri(tracking_uri):
            return None
        else:
            assert tracking_uri.startswith("file:")
            return tracking_uri[5:]

    @property
    def mlflow_client(self) -> MlflowClient:
        """Get the MLflow client. Also configures MLflow if necessary.

        Returns:
            The MLFlowClient.
        """
        if not self._client:
            self._configure_mlflow()
            self._client = mlflow.tracking.MlflowClient()
        return self._client

    def start_mlflow_run(
        self,
        experiment_name: str,
        run_name: str,
        nested_run_name: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Starts a new MLflow run.

        Args:
            experiment_name: Name of the experiment to start the run in. If no
                experiment with this name exists, it is created.
            run_name: Name of the run to start.
            nested_run_name: Optional name of a nested run to start.
            tags: Optional tags to add to the runs.
        """
        self.mlflow_client  # configure mlflow if necessary
        experiment = self._set_active_experiment(experiment_name)
        run_id = self.get_mlflow_run_id(
            experiment_name=experiment_name, run_name=run_name
        )

        tags = tags.copy() if tags else {}
        tags.update(self._get_internal_tags())

        mlflow.start_run(
            run_id=run_id,
            run_name=run_name,
            experiment_id=experiment.experiment_id,
            tags=tags,
        )

        if nested_run_name:
            mlflow.start_run(run_name=nested_run_name, nested=True, tags=tags)

    def get_mlflow_run_id(
        self, experiment_name: str, run_name: str
    ) -> Optional[str]:
        """Gets the id of a run with the given name and experiment.

        Args:
            experiment_name: Name of the experiment in which to search for the
                run.
            run_name: Name of the run to search.

        Returns:
            The id of the run if it exists and is a ZenML run, else None.
        """
        self.mlflow_client  # configure mlflow if necessary

        experiment_name = self._adjust_experiment_name(
            experiment_name=experiment_name,
            in_databricks=is_databricks_tracking_uri(self.tracking_uri),
        )

        runs = mlflow.search_runs(
            experiment_names=[experiment_name],
            filter_string=f'tags.mlflow.runName = "{run_name}"',
            run_view_type=3,
            output_format="list",
        )
        if not runs:
            return None

        run: Run = runs[0]
        if self._is_zenml_run(run):
            return cast(str, run.info.run_id)
        else:
            return None

    def end_mlflow_runs(self, status: str) -> None:
        """Ends all active MLflow runs.

        Args:
            status: The status to end the runs with.
        """
        self.mlflow_client  # configure mlflow if necessary
        self._disable_autologging()
        self._stop_zenml_mlflow_runs(status)
        mlflow.set_tracking_uri("")
        mlflow.set_registry_uri("")

    # ================
    # Internal Methods
    # ================

    @property
    def validator(self) -> Optional["StackValidator"]:
        """Checks the stack has a `LocalArtifactStore` if no tracking uri was specified.

        Returns:
            An optional `StackValidator`.
        """
        from zenml.artifact_stores import LocalArtifactStore

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

    def _ensure_valid_tracking_uri(self) -> None:
        """Ensures that the tracking uri is a valid mlflow tracking uri.

        Raises:
            ValueError: If the tracking uri is not valid.
        """
        tracking_uri = self.config.tracking_uri
        if tracking_uri:
            valid_schemes = DATABASE_ENGINES + ["http", "https", "file"]
            if not any(
                tracking_uri.startswith(scheme) for scheme in valid_schemes
            ) and not is_databricks_tracking_uri(tracking_uri):
                raise ValueError(
                    f"MLflow tracking uri does not start with one of the valid "
                    f"schemes {valid_schemes} or its value is not set to "
                    f"'databricks'. See "
                    f"https://www.mlflow.org/docs/latest/tracking.html#where-runs-are-recorded "
                    f"for more information."
                )

    @staticmethod
    def _get_local_mlflow_backend() -> str:
        """Gets the local MLflow backend inside the ZenML artifact store.

        Returns:
            The MLflow tracking URI for the local MLflow backend.
        """
        import os

        from zenml.client import Client

        client = Client()
        artifact_store = client.active_stack.artifact_store
        local_mlflow_tracking_uri = os.path.join(artifact_store.path, "mlruns")
        if not os.path.exists(local_mlflow_tracking_uri):
            os.makedirs(local_mlflow_tracking_uri)
        return "file:" + local_mlflow_tracking_uri

    def _configure_mlflow(self) -> None:
        """Configures the MLflow tracking URI and any additional credentials."""
        tracking_uri = self.tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_registry_uri(tracking_uri)

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

    def _set_active_experiment(self, experiment_name: str) -> "Experiment":
        """Sets the active MLflow experiment.

        If no experiment with this name exists, it is created and then
        activated.

        Args:
            experiment_name: Name of the experiment to activate.

        Raises:
            RuntimeError: If the experiment creation or activation failed.

        Returns:
            The experiment.
        """
        self.mlflow_client  # configure mlflow if necessary
        experiment_name = self._adjust_experiment_name(
            experiment_name=experiment_name,
            in_databricks=is_databricks_tracking_uri(self.tracking_uri),
        )
        mlflow.set_experiment(experiment_name=experiment_name)
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            raise RuntimeError("Failed to set active mlflow experiment.")
        return experiment

    @staticmethod
    def _adjust_experiment_name(
        experiment_name: str, in_databricks: bool
    ) -> str:
        """Prepends a slash to the experiment name if using Databricks.

        Databricks requires the experiment name to be an absolute path within
        the Databricks workspace.

        Args:
            experiment_name: The experiment name.
            in_databricks: Whether the code is running in Databricks or not.

        Returns:
            The potentially adjusted experiment name.
        """
        if in_databricks and not experiment_name.startswith("/"):
            return f"/{experiment_name}"
        else:
            return experiment_name

    @staticmethod
    def _get_internal_tags() -> Dict[str, Any]:
        """Gets ZenML internal tags for MLflow runs.

        Returns:
            Internal tags.
        """
        from zenml import __version__ as zenml_version

        return {ZENML_TAG_KEY: zenml_version}

    @staticmethod
    def _is_zenml_run(run: "Run") -> bool:
        """Checks if a MLflow run is a ZenML run or not.

        Args:
            run: The run to check.

        Returns:
            If the run is a ZenML run.
        """
        return ZENML_TAG_KEY in run.data.tags

    @staticmethod
    def _disable_autologging() -> None:
        """Disables MLflow autologging."""
        from mlflow import (
            fastai,
            gluon,
            lightgbm,
            pytorch,
            sklearn,
            spark,
            statsmodels,
            tensorflow,
            xgboost,
        )

        # There is no way to disable auto-logging for all frameworks at once.
        # If auto-logging is explicitly enabled for a framework by calling its
        # autolog() method, it cannot be disabled by calling
        # `mlflow.autolog(disable=True)`. Therefore, we need to disable
        # auto-logging for all frameworks explicitly.

        tensorflow.autolog(disable=True)
        gluon.autolog(disable=True)
        xgboost.autolog(disable=True)
        lightgbm.autolog(disable=True)
        statsmodels.autolog(disable=True)
        spark.autolog(disable=True)
        sklearn.autolog(disable=True)
        fastai.autolog(disable=True)
        pytorch.autolog(disable=True)

    @staticmethod
    def _stop_zenml_mlflow_runs(status: str) -> None:
        """Stops active ZenML Mlflow runs.

        This function stops all MLflow active runs until no active run exists or
        a non-ZenML run is active.

        Args:
            status: The status to set the run to.
        """
        import mlflow

        active_run = mlflow.active_run()
        while active_run:
            if MLFlowStackComponentMixin._is_zenml_run(active_run):
                logger.debug("Stopping mlflow run %s.", active_run.info.run_id)
                mlflow.end_run(status=status)
                active_run = mlflow.active_run()
            else:
                break
