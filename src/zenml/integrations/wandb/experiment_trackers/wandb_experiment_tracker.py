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
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast

import wandb

from zenml.constants import METADATA_EXPERIMENT_TRACKER_URL
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.wandb.experiment_trackers.run_initialization import (
    build_wandb_initialization,
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
        init_kwargs = build_wandb_initialization(
            config=self.config,
            settings=settings,
            info=info,
        )
        self._initialize_wandb(info=info, **init_kwargs)

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[str, "MetadataType"]:
        """Get component- and step-specific metadata after a step ran.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary of metadata.
        """
        run_id: Optional[str] = None
        run_path: Optional[str] = None
        run_url: Optional[str] = None
        run_name: Optional[str] = None
        run_group: Optional[str] = None
        run_project: Optional[str] = None
        run_entity: Optional[str] = None
        run_job_type: Optional[str] = None

        # Try to get the run name and URL from WandB directly
        current_wandb_run = wandb.run
        if current_wandb_run:
            run_id = getattr(current_wandb_run, "id", None)
            run_path = getattr(current_wandb_run, "path", None)
            run_url = current_wandb_run.url
            run_name = getattr(current_wandb_run, "name", None)
            run_group = getattr(current_wandb_run, "group", None)
            run_project = getattr(current_wandb_run, "project", None)
            run_entity = getattr(current_wandb_run, "entity", None)
            run_job_type = getattr(current_wandb_run, "job_type", None)

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
        default_group = (
            info.run_name if settings.enable_zenml_metadata else None
        )

        metadata: Dict[str, "MetadataType"] = {
            METADATA_EXPERIMENT_TRACKER_URL: Uri(run_url),
            "wandb_run_name": run_name,
        }
        optional_metadata = {
            "wandb_run_id": run_id,
            "wandb_run_path": run_path,
            "wandb_project": run_project or self.config.project_name,
            "wandb_entity": run_entity or self.config.entity,
            "wandb_group": run_group or settings.group or default_group,
            "wandb_job_type": run_job_type or settings.job_type,
            "wandb_url": run_url,
        }
        metadata.update(
            {
                key: value
                for key, value in optional_metadata.items()
                if value is not None
            }
        )

        return metadata

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
        **init_kwargs: Any,
    ) -> None:
        """Initializes a wandb run.

        Args:
            info: Step run information.
            init_kwargs: Keyword arguments passed to `wandb.init`.
        """
        logger.info(
            f"Initializing wandb with entity {self.config.entity}, project "
            f"name: {self.config.project_name}, run_name: "
            f"{init_kwargs.get('name')}."
        )
        wandb.init(**init_kwargs)

        settings = cast(
            WandbExperimentTrackerSettings, self.get_settings(info)
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
