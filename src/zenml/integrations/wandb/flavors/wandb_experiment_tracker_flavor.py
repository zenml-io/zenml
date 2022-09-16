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
"""Weights & Biases experiment tracker flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.wandb import WANDB_EXPERIMENT_TRACKER_FLAVOR
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.wandb.experiment_trackers import (
        WandbExperimentTracker,
    )


class WandbExperimentTrackerConfig(BaseExperimentTrackerConfig):
    """Config for the Wandb experiment tracker.

    Attributes:
        entity: Name of an existing wandb entity.
        project_name: Name of an existing wandb project to log to.
        api_key: API key to should be authorized to log to the configured wandb
            entity and project.
    """

    api_key: str = SecretField()
    entity: Optional[str] = None
    project_name: Optional[str] = None


class WandbExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Flavor for the Wandb experiment tracker."""

    @property
    def name(self) -> str:
        return WANDB_EXPERIMENT_TRACKER_FLAVOR

    @property
    def config_class(self) -> Type[WandbExperimentTrackerConfig]:
        return WandbExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["WandbExperimentTracker"]:
        from zenml.integrations.wandb.experiment_trackers import (
            WandbExperimentTracker,
        )

        return WandbExperimentTracker
