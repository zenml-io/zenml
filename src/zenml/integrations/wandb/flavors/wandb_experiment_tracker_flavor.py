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
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    cast,
)

from pydantic import BaseModel, Field, field_validator, model_validator

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

    _MANAGED_INIT_KWARGS: ClassVar[set[str]] = {
        "config",
        "entity",
        "group",
        "id",
        "job_type",
        "name",
        "project",
        "project_name",
        "resume",
        "settings",
        "tags",
    }

    run_name: Optional[str] = Field(
        None, description="The Wandb run name to use for tracking experiments."
    )
    run_id: Optional[str] = Field(
        None,
        description="Explicit Wandb run ID to use for advanced resume flows.",
    )
    run_id_strategy: Literal[
        "wandb_generated", "new_on_retry", "reuse_on_retry"
    ] = Field(
        "wandb_generated",
        description=(
            "Strategy used to derive Wandb run IDs. The default leaves IDs "
            "to Wandb, 'reuse_on_retry' resumes the same run for retries, "
            "and 'new_on_retry' creates a new deterministic run for retries."
        ),
    )
    resume: Optional[Literal["allow", "must", "never", "auto"]] = Field(
        None,
        description="Wandb resume policy. Defaults to 'allow' when ZenML sets a run ID.",
    )
    group: Optional[str] = Field(
        None, description="Wandb group to use for the run."
    )
    job_type: Optional[str] = Field(
        None, description="Optional Wandb job type for the run."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags to attach to the Wandb run for categorization and filtering.",
    )
    run_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="User-provided Wandb config values to attach to the run.",
    )
    init_kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Advanced Wandb init keyword arguments not managed by ZenML.",
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional settings for the Wandb run configuration.",
    )
    enable_zenml_metadata: bool = Field(
        True,
        description="Whether to add ZenML context to Wandb tags and config.",
    )
    enable_zenml_dashboard_links: bool = Field(
        True,
        description="Whether to add ZenML dashboard links to Wandb config when available.",
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
                return value.model_dump()  # type: ignore[no-untyped-call, unused-ignore]
            elif hasattr(value, "make_static"):
                return cast(Dict[str, Any], value.make_static())
            elif hasattr(value, "to_dict"):
                return value.to_dict()
            else:
                raise ValueError("Unable to convert wandb settings to dict.")
        else:
            return value

    @model_validator(mode="after")
    def _validate_wandb_init_settings(
        self,
    ) -> "WandbExperimentTrackerSettings":
        """Validate Wandb identity and config settings."""
        if self.run_id and self.run_id_strategy != "wandb_generated":
            raise ValueError(
                "The 'run_id' setting cannot be combined with a "
                "non-default 'run_id_strategy'."
            )

        if self.run_id_strategy == "reuse_on_retry" and self.resume == "never":
            raise ValueError(
                "The 'reuse_on_retry' run ID strategy is incompatible with "
                "resume='never'."
            )

        if (
            self.resume == "must"
            and not self.run_id
            and self.run_id_strategy == "wandb_generated"
        ):
            raise ValueError(
                "The resume='must' setting requires either an explicit "
                "'run_id' or a deterministic 'run_id_strategy'."
            )

        reserved_config_keys = [
            key for key in self.run_config if key.startswith("zenml_")
        ]
        if reserved_config_keys:
            raise ValueError(
                "The 'run_config' setting cannot contain ZenML-reserved "
                f"config keys: {reserved_config_keys}."
            )

        managed_init_keys = sorted(
            self._MANAGED_INIT_KWARGS.intersection(self.init_kwargs)
        )
        if managed_init_keys:
            raise ValueError(
                "The 'init_kwargs' setting cannot contain Wandb init keys "
                f"managed by ZenML: {managed_init_keys}."
            )

        return self


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
