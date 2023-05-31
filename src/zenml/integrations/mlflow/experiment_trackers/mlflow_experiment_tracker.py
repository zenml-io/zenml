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

from typing import TYPE_CHECKING, Dict, Optional, Type, cast

import mlflow

from zenml.config.base_settings import BaseSettings
from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.mlflow.flavors.mlflow_experiment_tracker_flavor import (
    MLFlowExperimentTrackerConfig,
    MLFlowExperimentTrackerSettings,
)
from zenml.integrations.mlflow.mixins.mlflow_stack_component_mixin import (
    MLFlowStackComponentMixin,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)


class MLFlowExperimentTracker(
    BaseExperimentTracker, MLFlowStackComponentMixin
):
    """Track experiments using MLflow."""

    @property
    def config(self) -> MLFlowExperimentTrackerConfig:
        """Returns the `MLFlowExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(MLFlowExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Mlflow experiment tracker.

        Returns:
            The settings class.
        """
        return MLFlowExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Sets the MLflow tracking uri and credentials.

        Args:
            info: Info about the step that will be executed.
        """
        settings = cast(
            MLFlowExperimentTrackerSettings,
            self.get_settings(info),
        )

        nested_run_name = info.pipeline_step_name if settings.nested else None
        self.start_mlflow_run(
            experiment_name=settings.experiment_name or info.pipeline.name,
            run_name=info.run_name,
            nested_run_name=nested_run_name,
            tags=settings.tags,
        )

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        metadata: Dict[str, "MetadataType"] = {
            METADATA_EXPERIMENT_TRACKER_URL: Uri(self.tracking_uri),
        }
        active_run = mlflow.active_run()
        if active_run:
            metadata["mlflow_run_id"] = active_run.info.run_id
            metadata["mlflow_experiment_id"] = active_run.info.experiment_id
        return metadata

    def cleanup_step_run(
        self,
        info: "StepRunInfo",
        step_failed: bool,
    ) -> None:
        """Stops active MLflow runs and resets the MLflow tracking uri.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed or not.
        """
        status = "FAILED" if step_failed else "FINISHED"
        self.end_mlflow_runs(status=status)
