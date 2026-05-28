#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

from typing import (
    TYPE_CHECKING,
    List,
    Literal,
    Optional,
    Type,
)

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.experiment_trackers.base_experiment_tracker import (
    BaseExperimentTrackerConfig,
    BaseExperimentTrackerFlavor,
)
from zenml.integrations.trackio import (
    TRACKIO_EXPERIMENT_TRACKER_FLAVOR,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.trackio.experiment_trackers import (
        TrackioExperimentTracker,
    )


class TrackioExperimentTrackerSettings(BaseSettings):
    """Settings for the Trackio experiment tracker."""

    run_name: Optional[str] = Field(
        default=None,
        description="Trackio run name.",
    )

    tags: List[str] = Field(
        default_factory=list,
        description=("Tags associated with the Trackio run."),
    )

    resume: Literal["allow", "must", "never"] = Field(
        default="allow",
        description=(
            "Run resume behavior. "
            "Supported values are "
            "'allow', 'must', and 'never'."
        ),
    )

    auto_sync: bool = Field(
        default=False,
        description=("Automatically sync Trackio runs after completion."),
    )

    auto_freeze: bool = Field(
        default=False,
        description=(
            "Automatically freeze Trackio dashboards after completion."
        ),
    )

    log_system_metrics: bool = Field(
        default=True,
        description=("Whether system metrics should be logged automatically."),
    )

    log_gpu_metrics: bool = Field(
        default=True,
        description=("Whether GPU telemetry should be logged automatically."),
    )


class TrackioExperimentTrackerConfig(
    BaseExperimentTrackerConfig,
    TrackioExperimentTrackerSettings,
):
    """Config for the Trackio experiment tracker."""

    project_name: str = Field(
        default="zenml",
        description=("Trackio project name."),
    )

    tracking_uri: Optional[str] = Field(
        default=None,
        description=(
            "Optional Trackio backend URI. "
            "Can point to a local backend, "
            "HF Space backend, or self-hosted server."
        ),
    )

    backend: str = Field(
        default="sqlite",
        description=(
            "Trackio backend type. "
            "Supported values include "
            "'sqlite', 'space', 'http', and 'static'."
        ),
    )

    local_dir: str = Field(
        default="./trackio",
        description=("Local directory used for Trackio storage."),
    )

    hf_token: Optional[str] = SecretField(
        default=None,
        description=(
            "Optional Hugging Face token used for "
            "syncing runs, datasets, buckets, or Spaces."
        ),
    )

    hf_space: Optional[str] = Field(
        default=None,
        description=(
            "Optional Hugging Face Space used as "
            "the Trackio dashboard backend."
        ),
    )

    hf_dataset_repo: Optional[str] = Field(
        default=None,
        description=(
            "Optional Hugging Face Dataset repository "
            "used for publishing experiment logs."
        ),
    )

    hf_bucket_uri: Optional[str] = Field(
        default=None,
        description=(
            "Optional Hugging Face bucket URI used "
            "for artifact and static dashboard storage."
        ),
    )

    publish_to_space: bool = Field(
        default=False,
        description=(
            "Whether Trackio dashboards should "
            "automatically be published to a "
            "Hugging Face Space."
        ),
    )

    publish_to_dataset: bool = Field(
        default=False,
        description=(
            "Whether Trackio logs should "
            "automatically be published to a "
            "Hugging Face Dataset repository."
        ),
    )

    static_space_mode: bool = Field(
        default=False,
        description=(
            "Whether Trackio should use static "
            "Space deployment mode backed by "
            "Hugging Face buckets."
        ),
    )


class TrackioExperimentTrackerFlavor(BaseExperimentTrackerFlavor):
    """Flavor for the Trackio experiment tracker."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The flavor name.
        """
        return TRACKIO_EXPERIMENT_TRACKER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL pointing to flavor documentation.

        Returns:
            Flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL pointing to SDK documentation.

        Returns:
            Flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """URL for the Trackio logo.

        Returns:
            Logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/experiment_tracker/trackio.png"

    @property
    def config_class(
        self,
    ) -> Type[TrackioExperimentTrackerConfig]:
        """Returns Trackio config class.

        Returns:
            The Trackio config class.
        """
        return TrackioExperimentTrackerConfig

    @property
    def implementation_class(
        self,
    ) -> Type["TrackioExperimentTracker"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.trackio.experiment_trackers import (
            TrackioExperimentTracker,
        )

        return TrackioExperimentTracker
