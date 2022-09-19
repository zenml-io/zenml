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
"""MLFlow experiment tracker flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic import root_validator, validator

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


class MLFlowExperimentTrackerConfig(BaseExperimentTrackerConfig):
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
    tracking_username: Optional[str] = SecretField()
    tracking_password: Optional[str] = SecretField()
    tracking_token: Optional[str] = SecretField()
    tracking_insecure_tls: bool = False
    databricks_host: Optional[str] = None

    @validator("tracking_uri")
    def _ensure_valid_tracking_uri(
        cls, tracking_uri: Optional[str] = None
    ) -> Optional[str]:
        """Ensures that the tracking uri is a valid mlflow tracking uri.

        Args:
            tracking_uri: The tracking uri to validate.

        Returns:
            The tracking uri if it is valid.

        Raises:
            ValueError: If the tracking uri is not valid.
        """
        # TODO: refactor this into the actual implementation
        from mlflow.store.db.db_types import (
            DATABASE_ENGINES,  # type: ignore[import]
        )

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
        return tracking_uri

    @root_validator(skip_on_failure=True)
    def _ensure_authentication_if_necessary(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensures that credentials or a token for authentication exist.

        We make this check when running MLflow tracking with a remote backend.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ValueError: If neither credentials nor a token are provided.
        """
        tracking_uri = values.get("tracking_uri")

        if tracking_uri:
            if is_databricks_tracking_uri(tracking_uri):
                # If the tracking uri is "databricks", then we need the databricks
                # host to be set.
                databricks_host = values.get("databricks_host")

                if not databricks_host:
                    raise ValueError(
                        f"MLflow experiment tracking with a Databricks MLflow "
                        f"managed tracking server requires the `databricks_host` "
                        f"to be set in your stack component. To update your "
                        f"component, run `zenml experiment-tracker update "
                        f"{values['name']} --databricks_host=DATABRICKS_HOST` "
                        f"and specify the hostname of your Databricks workspace."
                    )

            if is_remote_mlflow_tracking_uri(tracking_uri):
                # we need either username + password or a token to authenticate to
                # the remote backend
                basic_auth = values.get("tracking_username") and values.get(
                    "tracking_password"
                )
                token_auth = values.get("tracking_token")

                if not (basic_auth or token_auth):
                    raise ValueError(
                        f"MLflow experiment tracking with a remote backend "
                        f"{tracking_uri} is only possible when specifying either "
                        f"username and password or an authentication token in your "
                        f"stack component. To update your component, run the "
                        f"following command: `zenml experiment-tracker update "
                        f"{values['name']} --tracking_username=MY_USERNAME "
                        f"--tracking_password=MY_PASSWORD "
                        f"--tracking_token=MY_TOKEN` and specify either your "
                        f"username and password or token."
                    )

        return values


class MLFlowExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    @property
    def name(self) -> str:
        return MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR

    @property
    def config_class(self) -> Type[MLFlowExperimentTrackerConfig]:
        return MLFlowExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["MLFlowExperimentTracker"]:
        from zenml.integrations.mlflow.experiment_trackers import (
            MLFlowExperimentTracker,
        )

        return MLFlowExperimentTracker
