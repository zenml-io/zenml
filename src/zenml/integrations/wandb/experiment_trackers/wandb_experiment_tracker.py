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
"""Implementation for the wandb experiment tracker."""

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

import wandb

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
    WandbExperimentTrackerConfig,
    WandbExperimentTrackerSettings,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)


WANDB_API_KEY = "WANDB_API_KEY"


class WandbExperimentTracker(BaseExperimentTracker):
    """Track experiment using Wandb."""

    @property
    def config(self) -> WandbExperimentTrackerConfig:
        """Returns the `WandbExperimentTrackerConfig` config.

        Returns:
            The configuration.
        """
        return cast(WandbExperimentTrackerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """settings class for the Wandb experiment tracker.

        Returns:
            The settings class.
        """
        return WandbExperimentTrackerSettings

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Configures a Wandb run.

        Args:
            info: Info about the step that will be executed.
        """
        os.environ[WANDB_API_KEY] = self.config.api_key
        settings = cast(WandbExperimentTrackerSettings, self.get_settings(info))

        tags = settings.tags + [info.run_name, info.pipeline.name]
        wandb_run_name = (
            settings.run_name or f"{info.run_name}_{info.config.name}"
        )
        self._initialize_wandb(
            run_name=wandb_run_name, tags=tags, settings=settings.settings
        )

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Stops the Wandb run.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed or not.
        """
        wandb.finish(exit_code=1) if step_failed else wandb.finish()
        os.environ.pop(WANDB_API_KEY, None)

    def _initialize_wandb(
        self,
        run_name: str,
        tags: List[str],
        settings: Union[wandb.Settings, Dict[str, Any], None] = None,
    ) -> None:
        """Initializes a wandb run.

        Args:
            run_name: Name of the wandb run to create.
            tags: Tags to attach to the wandb run.
            settings: Additional settings for the wandb run.
        """
        logger.info(
            f"Initializing wandb with entity {self.config.entity}, project "
            f"name: {self.config.project_name}, run_name: {run_name}."
        )
        wandb.init(
            entity=self.config.entity,
            project=self.config.project_name,
            name=run_name,
            tags=tags,
            settings=settings,
        )
