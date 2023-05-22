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
from typing import Any, Optional, cast

import mlflow
from mlflow import MlflowClient
from mlflow.entities import Run
from mlflow.store.db.db_types import DATABASE_ENGINES

from zenml.integrations.mlflow.mixins.mlflow_config_mixin import (
    MLFlowConfigMixin,
)
from zenml.integrations.mlflow.mlflow_utils import (
    adjust_experiment_name,
    get_local_mlflow_backend,
    is_databricks_tracking_uri,
    is_remote_mlflow_tracking_uri,
    is_zenml_run,
)
from zenml.stack import StackValidator
from zenml.stack.stack_component import StackComponent

MLFLOW_TRACKING_USERNAME = "MLFLOW_TRACKING_USERNAME"
MLFLOW_TRACKING_PASSWORD = "MLFLOW_TRACKING_PASSWORD"
MLFLOW_TRACKING_TOKEN = "MLFLOW_TRACKING_TOKEN"
MLFLOW_TRACKING_INSECURE_TLS = "MLFLOW_TRACKING_INSECURE_TLS"
MLFLOW_BACKEND_STORE_URI = "_MLFLOW_SERVER_FILE_STORE"

DATABRICKS_HOST = "DATABRICKS_HOST"
DATABRICKS_USERNAME = "DATABRICKS_USERNAME"
DATABRICKS_PASSWORD = "DATABRICKS_PASSWORD"
DATABRICKS_TOKEN = "DATABRICKS_TOKEN"


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

    @property
    def config(self) -> MLFlowConfigMixin:
        """Returns the config mixin that this stack component requires.

        Returns:
            The configuration.
        """
        return cast(MLFlowConfigMixin, self._config)

    def get_tracking_uri(self) -> str:
        """Returns the configured tracking URI or a local fallback.

        Returns:
            The tracking URI.
        """
        return self.config.tracking_uri or get_local_mlflow_backend()

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

    def configure_mlflow(self) -> None:
        """Configures the MLflow tracking URI and any additional credentials."""
        tracking_uri = self.get_tracking_uri()
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

    def get_run_id(self, experiment_name: str, run_name: str) -> Optional[str]:
        """Gets the id of a run with the given name and experiment.

        Args:
            experiment_name: Name of the experiment in which to search for the
                run.
            run_name: Name of the run to search.

        Returns:
            The id of the run if it exists.
        """
        self.configure_mlflow()
        experiment_name = adjust_experiment_name(
            experiment_name=experiment_name,
            in_databricks=is_databricks_tracking_uri(self.get_tracking_uri()),
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
        if is_zenml_run(run):
            return cast(str, run.info.run_id)
        else:
            return None

    @property
    def mlflow_client(self) -> MlflowClient:
        """Get the MLflow client.

        Returns:
            The MLFlowClient.
        """
        if not self._client:
            self.configure_mlflow()
            self._client = mlflow.tracking.MlflowClient()
        return self._client
