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
"""MLflow experiment tracker flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic import model_validator

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.mlflow import MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.mlflow.experiment_trackers import (
        MLFlowExperimentTracker,
    )


def is_remote_mlflow_tracking_uri(tracking_uri: str) -> bool:
    """Checks whether the given tracking uri is remote or not.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is remote, `False` otherwise.
    """
    return any(
        tracking_uri.startswith(prefix) for prefix in ["http://", "https://"]
    ) or is_databricks_tracking_uri(tracking_uri)


def is_databricks_tracking_uri(tracking_uri: str) -> bool:
    """Checks whether the given tracking uri is a Databricks tracking uri.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is a Databricks tracking uri, `False`
        otherwise.
    """
    return tracking_uri == "databricks"


class MLFlowExperimentTrackerSettings(BaseSettings):
    """Settings for the MLflow experiment tracker.

    Attributes:
        experiment_name: The MLflow experiment name.
        nested: If `True`, will create a nested sub-run for the step.
        tags: Tags for the Mlflow run.
    """

    experiment_name: Optional[str] = None
    nested: bool = False
    tags: Dict[str, Any] = {}


class MLFlowExperimentTrackerConfig(
    BaseExperimentTrackerConfig, MLFlowExperimentTrackerSettings
):
    """Config for the MLflow experiment tracker.

    Attributes:
        tracking_uri: The uri of the mlflow tracking server. If no uri is set,
            your stack must contain a `LocalArtifactStore` and ZenML will
            point MLflow to a subdirectory of your artifact store instead.
        tracking_username: Username for authenticating with the MLflow
            tracking server. When a remote tracking uri is specified,
            either `tracking_token` or `tracking_username` and
            `tracking_password` must be specified.
        tracking_password: Password for authenticating with the MLflow
            tracking server. When a remote tracking uri is specified,
            either `tracking_token` or `tracking_username` and
            `tracking_password` must be specified.
        tracking_token: Token for authenticating with the MLflow
            tracking server. When a remote tracking uri is specified,
            either `tracking_token` or `tracking_username` and
            `tracking_password` must be specified.
        tracking_insecure_tls: Skips verification of TLS connection to the
            MLflow tracking server if set to `True`.
        databricks_host: The host of the Databricks workspace with the MLflow
            managed server to connect to. This is only required if
            `tracking_uri` value is set to `"databricks"`.
    """

    tracking_uri: Optional[str] = None
    tracking_username: Optional[str] = SecretField(default=None)
    tracking_password: Optional[str] = SecretField(default=None)
    tracking_token: Optional[str] = SecretField(default=None)
    tracking_insecure_tls: bool = False
    databricks_host: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_authentication_if_necessary(
        self,
    ) -> "MLFlowExperimentTrackerConfig":
        """Ensures that credentials or a token for authentication exist.

        We make this check when running MLflow tracking with a remote backend.

        Returns:
            The validated values.

        Raises:
             ValueError: If neither credentials nor a token are provided.
        """
        if self.tracking_uri:
            if is_databricks_tracking_uri(self.tracking_uri):
                # If the tracking uri is "databricks", then we need the
                # databricks host to be set.
                if not self.databricks_host:
                    raise ValueError(
                        "MLflow experiment tracking with a Databricks MLflow "
                        "managed tracking server requires the "
                        "`databricks_host` to be set in your stack component. "
                        "To update your component, run "
                        "`zenml experiment-tracker update "
                        "<NAME> --databricks_host=DATABRICKS_HOST` "
                        "and specify the hostname of your Databricks workspace."
                    )

            if is_remote_mlflow_tracking_uri(self.tracking_uri):
                # we need either username + password or a token to authenticate
                # to the remote backend
                basic_auth = self.tracking_username and self.tracking_password

                if not (basic_auth or self.tracking_token):
                    raise ValueError(
                        f"MLflow experiment tracking with a remote backend "
                        f"{self.tracking_uri} is only possible when specifying "
                        f"either username and password or an authentication "
                        f"token in your stack component. To update your "
                        f"component, run the following command: "
                        f"`zenml experiment-tracker update "
                        f"<NAME> --tracking_username=MY_USERNAME "
                        f"--tracking_password=MY_PASSWORD "
                        f"--tracking_token=MY_TOKEN` and specify either your "
                        f"username and password or token."
                    )

        return self

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        if not self.tracking_uri or not is_remote_mlflow_tracking_uri(
            self.tracking_uri
        ):
            return True
        return False


class MLFlowExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Class for the `MLFlowExperimentTrackerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/experiment_tracker/mlflow.png"

    @property
    def config_class(self) -> Type[MLFlowExperimentTrackerConfig]:
        """Returns `MLFlowExperimentTrackerConfig` config class.

        Returns:
                The config class.
        """
        return MLFlowExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["MLFlowExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.mlflow.experiment_trackers import (
            MLFlowExperimentTracker,
        )

        return MLFlowExperimentTracker
