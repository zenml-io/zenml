#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation for the Comet experiment tracker."""

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from comet_ml import Experiment  # type: ignore

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.comet.flavors.comet_experiment_tracker_flavor import (
    CometExperimentTrackerConfig,
    CometExperimentTrackerSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType


logger = get_logger(__name__)

COMET_API_KEY = "COMET_API_KEY"


class CometExperimentTracker(BaseExperimentTracker):
    """Track experiment using Comet."""

    @property
    def config(self) -> CometExperimentTrackerConfig:
        """Returns the `CometExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(CometExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Type[CometExperimentTrackerSettings]:
        """Settings class for the Comet experiment tracker.

        Returns:
            The settings class.
        """
        return CometExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Configures a Comet experiment.

        Args:
            info: Info about the step that will be executed.
        """
        os.environ[COMET_API_KEY] = self.config.api_key
        settings = cast(
            CometExperimentTrackerSettings, self.get_settings(info)
        )
        tags = settings.tags + [info.run_name, info.pipeline.name]
        comet_exp_name = (
            settings.run_name or f"{info.run_name}_{info.pipeline_step_name}"
        )
        self._initialize_comet(
            run_name=comet_exp_name, tags=tags, settings=settings.settings
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
        exp_url: Optional[str] = None
        exp_name: Optional[str] = None

        if self.experiment:
            exp_url = self.experiment.url
            exp_name = self.experiment.name

        # If the URL cannot be retrieved, use the default experiment URL
        default_exp_url = (
            f"https://www.comet.com/{self.config.workspace}/"
            f"{self.config.project_name}/experiments/"
        )
        exp_url = exp_url or default_exp_url

        # If the experiment name cannot be retrieved, use the default name
        default_exp_name = f"{info.run_name}_{info.pipeline_step_name}"
        settings = cast(
            CometExperimentTrackerSettings, self.get_settings(info)
        )
        exp_name = exp_name or settings.run_name or default_exp_name

        return {
            METADATA_EXPERIMENT_TRACKER_URL: Uri(exp_url),
            "comet_experiment_name": exp_name,
        }

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Stops the Comet experiment.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed or not.
        """
        if self.experiment:
            self.experiment.end()
        os.environ.pop(COMET_API_KEY, None)

    def log_metrics(
        self,
        metrics: Dict[str, Any],
        step: Optional[int] = None,
    ) -> None:
        """Logs metrics to the Comet experiment.

        Args:
            metrics: Dictionary of metrics to log.
            step: Optional step number associated with the metrics.
        """
        if self.experiment:
            self.experiment.log_metrics(metrics, step=step)

    def log_params(self, params: Dict[str, Any]) -> None:
        """Logs parameters to the Comet experiment.

        Args:
            params: Dictionary of parameters to log.
        """
        if self.experiment:
            self.experiment.log_parameters(params)

    def _initialize_comet(
        self,
        run_name: str,
        tags: List[str],
        settings: Union[Dict[str, Any], None] = None,
    ) -> None:
        """Initializes a Comet experiment.

        Args:
            run_name: Name of the Comet experiment.
            tags: Tags to attach to the Comet experiment.
            settings: Additional settings for the Comet experiment.
        """
        logger.info(
            f"Initializing Comet with workspace {self.config.workspace}, project "
            f"name: {self.config.project_name}, run_name: {run_name}."
        )
        self.experiment = Experiment(
            workspace=self.config.workspace,
            project_name=self.config.project_name,
            **settings or {},
        )
        self.experiment.set_name(run_name)
        self.experiment.add_tags(tags)
