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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
    cast,
)

import wandb
from pydantic import validator

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTracker,
)
from zenml.integrations.wandb import WANDB_EXPERIMENT_TRACKER_FLAVOR
from zenml.logger import get_logger
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)


WANDB_API_KEY = "WANDB_API_KEY"


class WandbExperimentTrackerSettings(BaseSettings):
    """Settings for the Wandb experiment tracker.

    Attributes:
        run_name: The Wandb run name.
        tags: Tags for the Wandb run.
        settings: Settings for the Wandb run.
    """

    run_name: Optional[str] = None
    tags: List[str] = []
    settings: Dict[str, Any] = {}

    @validator("settings", pre=True)
    def _convert_settings(
        cls, value: Union[Dict[str, Any], wandb.Settings]
    ) -> Dict[str, Any]:
        """Converts settings to a dictionary.

        Args:
            value: The settings.

        Returns:
            Dict representation of the settings.
        """
        if isinstance(value, wandb.Settings):
            return cast(Dict[str, Any], value.make_static())
        else:
            return value


class WandbExperimentTracker(BaseExperimentTracker):
    """Stores wandb configuration options.

    Attributes:
        entity: Name of an existing wandb entity.
        project_name: Name of an existing wandb project to log to.
        api_key: API key to should be authorized to log to the configured wandb
            entity and project.
    """

    api_key: str = SecretField()
    entity: Optional[str] = None
    project_name: Optional[str] = None

    # Class Configuration
    FLAVOR: ClassVar[str] = WANDB_EXPERIMENT_TRACKER_FLAVOR

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
        os.environ[WANDB_API_KEY] = self.api_key
        settings = cast(
            WandbExperimentTrackerSettings,
            self.get_settings(info) or WandbExperimentTrackerSettings(),
        )

        tags = settings.tags + [info.run_name, info.pipeline.name]
        wandb_run_name = (
            settings.run_name or f"{info.run_name}_{info.config.name}"
        )
        self._initialize_wandb(
            run_name=wandb_run_name, tags=tags, settings=settings.settings
        )

    def cleanup_step_run(self, info: "StepRunInfo") -> None:
        """Stops the Wandb run.

        Args:
            info: Info about the step that was executed.
        """
        wandb.finish()
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
            f"Initializing wandb with entity {self.entity}, project name: "
            f"{self.project_name}, run_name: {run_name}."
        )
        wandb.init(
            entity=self.entity,
            project=self.project_name,
            name=run_name,
            tags=tags,
            settings=settings,
        )
