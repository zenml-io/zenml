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
"""Trackio experiment tracker flavor."""

"""Trackio experiment tracker flavor."""

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
        None,
        description="The Trackio run name to use for tracking experiments.",
    )

    tags: List[str] = Field(
        default_factory=list,
        description=(
            "Tags to attach to the Trackio run for categorization "
            "and filtering."
        ),
    )

    notes: Optional[str] = Field(
        None,
        description="Optional notes to associate with the run.",
    )

    group: Optional[str] = Field(
        None,
        description="Optional group name used to organize runs.",
    )

    resume: str = Field(
        "allow",
        description=(
            "Run resume behavior. Supported values are "
            "'allow', 'must', and 'never'."
        ),
    )

    auto_sync: bool = Field(
        False,
        description=(
            "Whether to automatically sync runs to a configured "
            "remote backend after completion."
        ),
    )

    auto_freeze: bool = Field(
        False,
        description=(
            "Whether to automatically freeze the Trackio dashboard "
            "after the run completes."
        ),
    )

    log_system_metrics: bool = Field(
        True,
        description="Whether to log system metrics automatically.",
    )

    log_gpu_metrics: bool = Field(
        True,
        description="Whether to log GPU telemetry automatically.",
    )

    @field_validator("settings", mode="before")
    @classmethod
    def _convert_settings(cls, value: Any) -> Any:
        """Converts Trackio settings objects to dictionaries.

        Args:
            value: The settings value.

        Returns:
            Dict representation of the settings.
        """
        try:
            import trackio
        except ImportError:
            return value

        # Future-proof conversion logic in case Trackio
        # introduces structured settings/config objects.
        if isinstance(value, BaseModel):
            return value.model_dump()

        if hasattr(value, "to_dict"):
            return cast(Dict[str, Any], value.to_dict())

        return value


class TrackioExperimentTrackerConfig(
    BaseExperimentTrackerConfig,
    TrackioExperimentTrackerSettings,
):
    """Config for the Trackio experiment tracker."""

    run_name: Optional[str] = Field(
            None,
            description="Trackio run name."
        )

    tracking_uri: Optional[str] = Field(
        None,
        description=(
            "Optional Trackio backend URI. Can point to "
            "a local backend, Hugging Face Space backend, "
            "or self-hosted HTTP server."
        ),
    )

    backend: str = Field(
        default="sqlite",
        description=(
            "Trackio backend type. Supported values include "
            "'sqlite', 'space', 'http', and 'static'."
        ),
    )

    local_dir: str = Field(
        default="./trackio",
        description="Local directory used for Trackio storage.",
    )

    hf_token: Optional[str] = SecretField(
        default=None,
        description=(
            "Optional Hugging Face token used for syncing "
            "runs, datasets, buckets, or Spaces."
        ),
    )

    hf_space: Optional[str] = Field(
        None,
        description=(
            "Optional Hugging Face Space used as the "
            "Trackio dashboard backend."
        ),
    )

    hf_dataset_repo: Optional[str] = Field(
        None,
        description=(
            "Optional Hugging Face Dataset repository "
            "used for publishing experiment logs."
        ),
    )

    hf_bucket_uri: Optional[str] = Field(
        None,
        description=(
            "Optional Hugging Face bucket URI used for "
            "artifact and static dashboard storage."
        ),
    )

    publish_to_space: bool = Field(
        False,
        description=(
            "Whether Trackio dashboards should automatically "
            "be published to a Hugging Face Space."
        ),
    )

    publish_to_dataset: bool = Field(
        False,
        description=(
            "Whether Trackio logs should automatically "
            "be published to a Hugging Face Dataset repository."
        ),
    )

    static_space_mode: bool = Field(
        False,
        description=(
            "Whether Trackio should use static Space deployment "
            "mode backed by Hugging Face buckets."
        ),
    )


class TrackioExperimentTrackerFlavor(
    BaseExperimentTrackerFlavor
):
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
        return (
            "https://github.com/gradio-app/trackio/blob/main/trackio/assets/trackio_logo_light.png"
        )

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