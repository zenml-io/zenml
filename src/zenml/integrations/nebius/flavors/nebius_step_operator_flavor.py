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
"""Configuration for the Nebius Serverless Jobs step operator."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.nebius import NEBIUS_STEP_OPERATOR_FLAVOR
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.nebius.step_operators import NebiusStepOperator


class NebiusStepOperatorSettings(BaseSettings):
    """Workload settings for a single, non-preemptible GPU Job.

    Native secret references map environment names to existing secret version
    IDs. The payload key must match the environment name. They may not override
    the environment supplied by ZenML.
    """

    platform: Optional[str] = Field(default=None, pattern=r"^gpu-[a-z0-9-]+$")
    preset: Optional[str] = Field(
        default=None, pattern=r"^1gpu-[1-9][0-9]*vcpu-[1-9][0-9]*gb$"
    )
    disk_size_gib: int = Field(default=100, ge=1)
    shm_size_gib: int = Field(default=16, ge=0)
    timeout_seconds: int = Field(default=3600, ge=3600, le=604800)
    provisioning_timeout_seconds: int = Field(default=1800, ge=1)
    total_timeout_seconds: int = Field(default=7200, ge=1)
    cancel_timeout_seconds: int = Field(default=120, ge=1)
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)
    poll_interval_seconds: int = Field(default=5, ge=1, le=60)
    publication_grace_seconds: int = Field(default=30, ge=1, le=300)
    public_ip: bool = False
    environment_secret_versions: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_supported_settings(self) -> "NebiusStepOperatorSettings":
        """Reject unsupported options while allowing inherited component fields.

        Returns:
            The validated settings.

        Raises:
            ValueError: If any unknown setting was supplied.
        """
        unknown = set(self.model_extra or {}) - set(
            NebiusStepOperatorConfig.model_fields
        )
        if unknown:
            raise ValueError(
                "Unsupported Nebius settings: " + ", ".join(sorted(unknown))
            )
        return self


class NebiusStepOperatorConfig(
    BaseStepOperatorConfig, NebiusStepOperatorSettings
):
    """Stable project, network and launcher authentication configuration."""

    project_id: str = Field(min_length=1)
    subnet_id: str = Field(min_length=1)
    credentials_file: Optional[str] = None
    registry_secret_version: Optional[str] = None

    @property
    def is_remote(self) -> bool:
        """Whether a remote ZenML server is required.

        Returns:
            True.
        """
        return True


class NebiusStepOperatorFlavor(BaseStepOperatorFlavor):
    """Flavor for executing Python steps as Nebius GPU Jobs."""

    @property
    def name(self) -> str:
        """Return the flavor name.

        Returns:
            The registered flavor name.
        """
        return NEBIUS_STEP_OPERATOR_FLAVOR

    @property
    def config_class(self) -> Type[NebiusStepOperatorConfig]:
        """Return the configuration class.

        Returns:
            The Nebius configuration class.
        """
        return NebiusStepOperatorConfig

    @property
    def implementation_class(self) -> Type["NebiusStepOperator"]:
        """Import the implementation only when the flavor is used.

        Returns:
            The Nebius step operator implementation.
        """
        from zenml.integrations.nebius.step_operators import NebiusStepOperator

        return NebiusStepOperator

    @property
    def docs_url(self) -> Optional[str]:
        """Return the component documentation URL.

        Returns:
            The generated documentation URL.
        """
        return self.generate_default_docs_url()
