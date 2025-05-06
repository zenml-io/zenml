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
from typing import TYPE_CHECKING, Dict, List, Optional, Type, cast

import wandb

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.wandb.flavors.wandb_experiment_tracker_flavor import (
    WandbExperimentTrackerConfig,
    WandbExperimentTrackerSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import Uri

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.metadata.metadata_types import MetadataType


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
    def settings_class(self) -> Type[WandbExperimentTrackerSettings]:
        """Settings class for the Wandb experiment tracker.

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
        settings = cast(
            WandbExperimentTrackerSettings, self.get_settings(info)
        )
        tags = settings.tags + [info.run_name, info.pipeline.name]
        wandb_run_name = (
            settings.run_name or f"{info.run_name}_{info.pipeline_step_name}"
        )
        self._initialize_wandb(run_name=wandb_run_name, tags=tags, info=info)

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        run_url: Optional[str] = None
        run_name: Optional[str] = None

        # Try to get the run name and URL from WandB directly
        current_wandb_run = wandb.run
        if current_wandb_run:
            run_url = current_wandb_run.get_url()
            run_name = current_wandb_run.name

        # If the URL cannot be retrieved, use the default run URL
        default_run_url = (
            f"https://wandb.ai/{self.config.entity}/"
            f"{self.config.project_name}/runs/"
        )
        run_url = run_url or default_run_url

        # If the run name cannot be retrieved, use the default run name
        default_run_name = f"{info.run_name}_{info.pipeline_step_name}"
        settings = cast(
            WandbExperimentTrackerSettings, self.get_settings(info)
        )
        run_name = run_name or settings.run_name or default_run_name

        return {
            METADATA_EXPERIMENT_TRACKER_URL: Uri(run_url),
            "wandb_run_name": run_name,
        }

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
        info: "StepRunInfo",
        run_name: str,
        tags: List[str],
    ) -> None:
        """Initializes a wandb run.

        Args:
            info: Step run information.
            run_name: Name of the wandb run to create.
            tags: Tags to attach to the wandb run.
        """
        logger.info(
            f"Initializing wandb with entity {self.config.entity}, project "
            f"name: {self.config.project_name}, run_name: {run_name}."
        )
        settings = cast(
            WandbExperimentTrackerSettings, self.get_settings(info)
        )
        wandb.init(
            entity=self.config.entity,
            project=self.config.project_name,
            name=run_name,
            tags=tags,
            settings=settings.settings,
        )

        if settings.enable_weave:
            import weave

            if self.config.project_name:
                logger.info("Initializing weave")
                weave.init(project_name=self.config.project_name)
            else:
                logger.info(
                    "Weave enabled but no project_name specified. "
                    "Skipping weave initialization."
                )
        else:
            import weave

            if self.config.project_name:
                logger.info("Disabling weave")
                weave.init(
                    project_name=self.config.project_name,
                    settings={"disabled": True},
                )
