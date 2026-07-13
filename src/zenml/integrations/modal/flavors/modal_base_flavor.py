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
"""Shared settings/credential mixins for Modal stack components."""

from typing import Optional

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.utils.secret_utils import SecretField

DEFAULT_TIMEOUT_SECONDS = 86400  # 24 hours


class ModalSettingsMixin(BaseSettings):
    """Shared Modal compute and placement settings.

    Attributes:
        gpu: The type of GPU to use for execution (e.g., "T4", "A100").
            Use ResourceSettings.gpu_count to specify the number of GPUs.
        region: The region to use for execution.
        cloud: The cloud provider to use for execution.
        modal_environment: The Modal environment to use for app lookup.
        timeout: Maximum execution time in seconds (default 24h).
    """

    gpu: Optional[str] = Field(
        None,
        description="GPU type for execution. Must be a valid Modal GPU type. "
        "Examples: 'T4' (cost-effective), 'A100' (high-performance), 'V100' (training workloads). "
        "Use ResourceSettings.gpu_count to specify number of GPUs. If not specified, uses CPU-only execution",
    )
    region: Optional[str] = Field(
        None,
        description="Cloud region for execution. Must be a valid region for the selected cloud provider. "
        "Examples: 'us-east-1', 'us-west-2', 'eu-west-1'. If not specified, Modal uses default region "
        "based on cloud provider and availability. Only available on Modal Enterprise and Team plans",
    )
    cloud: Optional[str] = Field(
        None,
        description="Cloud provider for execution. Must be a valid Modal-supported cloud provider. "
        "Examples: 'aws', 'gcp'. If not specified, Modal uses default cloud provider "
        "based on workspace configuration. Only available on Modal Enterprise and Team plans",
    )
    modal_environment: Optional[str] = Field(
        None,
        description="Modal environment name for app lookup. Must be a valid environment "
        "configured in Modal. ZenML passes it as the Modal SDK App.lookup "
        "environment_name argument. Examples: 'main', 'staging', 'production'. "
        "If not specified, Modal uses the default environment.",
    )
    timeout: int = Field(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=DEFAULT_TIMEOUT_SECONDS,
        description=f"Maximum execution time in seconds. Must be between 1 and {DEFAULT_TIMEOUT_SECONDS} seconds. "
        f"Examples: 3600 (1 hour), 7200 (2 hours), {DEFAULT_TIMEOUT_SECONDS} (24 hours maximum). "
        "Execution will be terminated if it exceeds this timeout",
    )


class ModalCredentialsMixin(BaseSettings):
    """Shared Modal API token credentials.

    Attributes:
        token_id: Modal API token ID (ak-xxxxx format) for authentication.
        token_secret: Modal API token secret (as-xxxxx format) for
            authentication.
    """

    token_id: Optional[str] = SecretField(
        default=None,
        description="Modal API token ID for authentication. Must be configured together with token_secret. "
        "When token_id and token_secret are both provided, ZenML creates an explicit Modal SDK "
        "client from those credentials. If not provided, Modal falls back to its default "
        "authentication from environment variables or ~/.modal.toml.",
    )
    token_secret: Optional[str] = SecretField(
        default=None,
        description="Modal API token secret for authentication. Must be configured together with token_id. "
        "When token_id and token_secret are both provided, ZenML creates an explicit Modal SDK "
        "client from those credentials. If not provided, Modal falls back to its default "
        "authentication from environment variables or ~/.modal.toml.",
    )

    @model_validator(mode="after")
    def validate_modal_token_pair(self) -> "ModalCredentialsMixin":
        """Validate that Modal token fields are configured together.

        Returns:
            The validated instance.

        Raises:
            ValueError: If only one of token_id/token_secret is configured.
        """
        token_id = self.token_id.strip() if self.token_id else None
        token_secret = self.token_secret.strip() if self.token_secret else None

        if bool(token_id) != bool(token_secret):
            raise ValueError(
                "Modal token_id and token_secret must be configured together."
            )

        return self
