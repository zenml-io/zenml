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

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.mlflow import MLFLOW_MODEL_EXPERIMENT_TRACKER_FLAVOR
from zenml.integrations.mlflow.mixins.mlflow_config_mixin import (
    MLFlowConfigMixin,
)

if TYPE_CHECKING:
    from zenml.integrations.mlflow.experiment_trackers import (
        MLFlowExperimentTracker,
    )


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


class MLFlowExperimentTrackerConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseExperimentTrackerConfig,
    MLFlowExperimentTrackerSettings,
    MLFlowConfigMixin,
):
    """Config for the MLflow experiment tracker."""


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
