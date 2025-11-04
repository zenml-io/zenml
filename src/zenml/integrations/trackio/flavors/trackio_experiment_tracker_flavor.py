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
"""Trackio experiment tracker flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.trackio import TRACKIO_EXPERIMENT_TRACKER_FLAVOR
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.trackio.experiment_trackers import (
        TrackioExperimentTracker,
    )

__all__ = [
    "TrackioExperimentTrackerConfig",
    "TrackioExperimentTrackerFlavor",
    "TrackioExperimentTrackerSettings",
]


class TrackioExperimentTrackerConfig(BaseExperimentTrackerConfig):
    """Configuration for the Trackio experiment tracker."""

    workspace: Optional[str] = Field(
        default=None,
        description=(
            "Optional workspace or organization to use for the Trackio run."
        ),
    )
    project: Optional[str] = Field(
        default=None,
        description="Trackio project slug where new runs should be created.",
    )
    api_key: Optional[str] = SecretField(
        default=None,
        description="API key used to authenticate with the Trackio service.",
    )
    base_url: Optional[str] = Field(
        default=None,
        description=(
            "Override the default Trackio service base URL (e.g. for a "
            "self-hosted deployment)."
        ),
    )


class TrackioExperimentTrackerSettings(BaseSettings):
    """Runtime settings for the Trackio experiment tracker."""

    run_name: Optional[str] = Field(
        default=None,
        description="Explicit name to assign to the Trackio run.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags to attach to the Trackio run.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Static metadata to log to Trackio as soon as the run is created."
        ),
    )


class TrackioExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Flavor for the Trackio experiment tracker component."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The flavor name.
        """

        return TRACKIO_EXPERIMENT_TRACKER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """URL pointing to the user documentation for this flavor."""

        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """URL pointing to the SDK documentation for this flavor."""

        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """URL of an image that represents the flavor in the dashboard."""

        return (
            "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/"
            "experiment_tracker/trackio.png"
        )

    @property
    def config_class(self) -> Type[TrackioExperimentTrackerConfig]:
        """Return the configuration class associated with this flavor."""

        return TrackioExperimentTrackerConfig

    @property
    def implementation_class(self) -> Type["TrackioExperimentTracker"]:
        """Implementation class for the Trackio experiment tracker flavor."""

        from zenml.integrations.trackio.experiment_trackers import (
            TrackioExperimentTracker,
        )

        return TrackioExperimentTracker
