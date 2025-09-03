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
    cast,
)

from pydantic import BaseModel, Field, field_validator

from zenml.config.base_settings import BaseSettings
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


class WandbExperimentTrackerSettings(BaseSettings):
    """Settings for the Wandb experiment tracker."""

    run_name: Optional[str] = Field(
        None, description="The Wandb run name to use for tracking experiments."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags to attach to the Wandb run for categorization and filtering.",
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional settings for the Wandb run configuration.",
    )
    enable_weave: bool = Field(
        False,
        description="Whether to enable Weave integration for enhanced experiment tracking.",
    )

    @field_validator("settings", mode="before")
    @classmethod
    def _convert_settings(cls, value: Any) -> Any:
        """Converts settings to a dictionary.

        Args:
            value: The settings.

        Raises:
            ValueError: If converting the settings failed.

        Returns:
            Dict representation of the settings.
        """
        try:
            import wandb
        except ImportError:
            return value

        if isinstance(value, wandb.Settings):
            # Depending on the wandb version, either `model_dump`,
            # `make_static` or `to_dict` is available to convert the settings
            # to a dictionary
            if isinstance(value, BaseModel):
                return value.model_dump()  # type: ignore[no-untyped-call]
            elif hasattr(value, "make_static"):
                return cast(Dict[str, Any], value.make_static())
            elif hasattr(value, "to_dict"):
                return value.to_dict()
            else:
                raise ValueError("Unable to convert wandb settings to dict.")
        else:
            return value


class WandbExperimentTrackerConfig(
    BaseExperimentTrackerConfig, WandbExperimentTrackerSettings
):
    """Config for the Wandb experiment tracker."""

    api_key: str = SecretField(
        description="API key that should be authorized to log to the configured "
        "Wandb entity and project. Required for authentication."
    )
    entity: Optional[str] = Field(
        None,
        description="Name of an existing Wandb entity (team or user account) "
        "to log experiments to.",
    )
    project_name: Optional[str] = Field(
        None,
        description="Name of an existing Wandb project to log experiments to. "
        "If not specified, a default project will be used.",
    )


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
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

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
