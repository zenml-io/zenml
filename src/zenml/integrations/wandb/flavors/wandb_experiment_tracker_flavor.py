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

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from pydantic import validator

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.wandb import WANDB_EXPERIMENT_TRACKER_FLAVOR
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from wandb import Settings

    from zenml.integrations.wandb.experiment_trackers import (
        WandbExperimentTracker,
    )


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
        cls,
        value: Union[Dict[str, Any], "Settings"],
    ) -> Dict[str, Any]:
        """Converts settings to a dictionary.

        Args:
            value: The settings.

        Returns:
            Dict representation of the settings.
        """
        import wandb

        if isinstance(value, wandb.Settings):
            # Depending on the wandb version, either `make_static` or `to_dict`
            # is available to convert the settings to a dictionary
            if hasattr(value, "make_static"):
                return cast(Dict[str, Any], value.make_static())
            else:
                return value.to_dict()
        else:
            return value


class WandbExperimentTrackerConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseExperimentTrackerConfig, WandbExperimentTrackerSettings
):
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
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return WANDB_EXPERIMENT_TRACKER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/experiment_tracker/wandb.png"

    @property
    def config_class(self) -> Type[WandbExperimentTrackerConfig]:
        """Returns `WandbExperimentTrackerConfig` config class.

        Returns:
                The config class.
        """
        return WandbExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["WandbExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.wandb.experiment_trackers import (
            WandbExperimentTracker,
        )

        return WandbExperimentTracker
