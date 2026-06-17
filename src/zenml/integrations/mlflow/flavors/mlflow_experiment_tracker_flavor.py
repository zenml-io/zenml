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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import Field, model_validator

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


def is_databricks_tracking_uri(tracking_uri: Optional[str]) -> bool:
    """Checks whether the given tracking uri is a Databricks tracking uri.

    Args:
        tracking_uri: The tracking uri to check.

    Returns:
        `True` if the tracking uri is a Databricks tracking uri, `False`
        otherwise.
    """
    return tracking_uri == "databricks"


class MLFlowExperimentTrackerSettings(BaseSettings):
    """Settings for the MLflow experiment tracker."""

    experiment_name: Optional[str] = Field(
        None,
        description="The MLflow experiment name to use for tracking runs.",
    )
    nested: bool = Field(
        False,
        description="If `True`, will create a nested sub-run for the step.",
    )
    tags: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tags to attach to the MLflow run for categorization and filtering.",
    )


class MLFlowExperimentTrackerConfig(
    BaseExperimentTrackerConfig, MLFlowExperimentTrackerSettings
):
    """Config for the MLflow experiment tracker."""

    tracking_uri: Optional[str] = Field(
        None,
        description="The URI of the MLflow tracking server. If no URI is set, "
        "your stack must contain a LocalArtifactStore and ZenML will point "
        "MLflow to a subdirectory of your artifact store instead.",
    )
    tracking_username: Optional[str] = SecretField(
        default=None,
        description="Username for authenticating with the MLflow tracking server. "
        "Required when using a remote tracking URI along with tracking_password.",
    )
    tracking_password: Optional[str] = SecretField(
        default=None,
        description="Password for authenticating with the MLflow tracking server. "
        "Required when using a remote tracking URI along with tracking_username.",
    )
    tracking_token: Optional[str] = SecretField(
        default=None,
        description="Token for authenticating with the MLflow tracking server. "
        "Alternative to username/password authentication for remote tracking URIs.",
    )
    databricks_client_id: Optional[str] = SecretField(
        default=None,
        description="Client ID of the Databricks service principal to use for "
        "OAuth M2M authentication. Only applies when tracking_uri is set to "
        "'databricks'.",
    )
    databricks_client_secret: Optional[str] = SecretField(
        default=None,
        description="Client secret of the Databricks service principal to use "
        "for OAuth M2M authentication. Only applies when tracking_uri is set "
        "to 'databricks'.",
    )
    tracking_insecure_tls: bool = Field(
        False,
        description="Skips verification of TLS connection to the MLflow tracking "
        "server if set to `True`. Use with caution in production environments.",
    )
    databricks_host: Optional[str] = Field(
        None,
        description="The host of the Databricks workspace with the MLflow managed "
        "server to connect to. Required when tracking_uri is set to 'databricks'.",
    )
    enable_unity_catalog: bool = Field(
        False,
        description="If `True`, will enable the Databricks Unity Catalog for "
        "logging and registering models.",
    )

    @model_validator(mode="after")
    def _ensure_complete_credential_pairs(
        self,
    ) -> "MLFlowExperimentTrackerConfig":
        """Ensures that credential pair authentication is complete.

        Returns:
            The validated values.

        Raises:
             ValueError: If only one value of a credential pair is configured.
        """
        if bool(self.tracking_username) != bool(self.tracking_password):
            raise ValueError(
                "MLflow username/password authentication requires both "
                "`tracking_username` and `tracking_password` to be "
                "configured."
            )

        if bool(self.databricks_client_id) != bool(
            self.databricks_client_secret
        ):
            raise ValueError(
                "Databricks OAuth M2M authentication requires both "
                "`databricks_client_id` and `databricks_client_secret` to be "
                "configured."
            )

        return self

    @model_validator(mode="after")
    def _ensure_databricks_tracking_uri(
        self,
    ) -> "MLFlowExperimentTrackerConfig":
        """Ensures that Databricks-specific options only target Databricks.

        Returns:
            The validated values.

        Raises:
             ValueError: If a Databricks option is configured for another URI.
        """
        if is_databricks_tracking_uri(self.tracking_uri):
            return self

        databricks_options = []
        if self.databricks_host:
            databricks_options.append("databricks_host")
        if self.databricks_client_id:
            databricks_options.append("databricks_client_id")
        if self.databricks_client_secret:
            databricks_options.append("databricks_client_secret")
        if self.enable_unity_catalog:
            databricks_options.append("enable_unity_catalog")

        if databricks_options:
            formatted_options = ", ".join(
                f"`{option}`" for option in databricks_options
            )
            raise ValueError(
                f"Databricks options {formatted_options} require "
                "`tracking_uri` to be set to `databricks`."
            )

        return self

    @model_validator(mode="after")
    def _ensure_databricks_host_if_necessary(
        self,
    ) -> "MLFlowExperimentTrackerConfig":
        """Ensures that Databricks tracking has a workspace host.

        Returns:
            The validated values.

        Raises:
             ValueError: If Databricks tracking is missing a host.
        """
        if (
            is_databricks_tracking_uri(self.tracking_uri)
            and not self.databricks_host
        ):
            raise ValueError(
                "MLflow experiment tracking with a Databricks MLflow "
                "managed tracking server requires the `databricks_host` to "
                "be set in your stack component. To update your component, "
                "run `zenml experiment-tracker update <NAME> "
                "--databricks_host=DATABRICKS_HOST` and specify the hostname "
                "of your Databricks workspace."
            )

        return self

    @model_validator(mode="after")
    def _ensure_exactly_one_authentication_method_if_necessary(
        self,
    ) -> "MLFlowExperimentTrackerConfig":
        """Ensures that remote tracking uses one authentication method.

        Returns:
            The validated values.

        Raises:
             ValueError: If remote tracking has zero or multiple auth methods.
        """
        if not self.tracking_uri or not is_remote_mlflow_tracking_uri(
            self.tracking_uri
        ):
            return self

        auth_methods = self._configured_authentication_methods()
        if len(auth_methods) == 1:
            return self

        valid_options = (
            "`tracking_token`, `tracking_username` with `tracking_password`"
        )
        if is_databricks_tracking_uri(self.tracking_uri):
            valid_options = (
                f"{valid_options}, or `databricks_client_id` with "
                "`databricks_client_secret`"
            )

        if not auth_methods:
            raise ValueError(
                f"MLflow experiment tracking with remote backend "
                f"`{self.tracking_uri}` requires exactly one authentication "
                f"method. Valid options are {valid_options}."
            )

        raise ValueError(
            f"MLflow experiment tracking with remote backend "
            f"`{self.tracking_uri}` requires exactly one authentication "
            f"method, but received multiple authentication methods: "
            f"{', '.join(auth_methods)}. Valid options are {valid_options}."
        )

    def _configured_authentication_methods(self) -> List[str]:
        """Returns the authentication methods configured on the component.

        Returns:
            The configured authentication method names.
        """
        auth_methods = []
        if self.tracking_username and self.tracking_password:
            auth_methods.append("username/password")
        if self.tracking_token:
            auth_methods.append("token")
        if self.databricks_client_id and self.databricks_client_secret:
            auth_methods.append("Databricks OAuth M2M")
        return auth_methods

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
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "MLflow"

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
