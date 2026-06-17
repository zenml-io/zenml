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
"""Modal step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal import MODAL_STEP_OPERATOR_FLAVOR
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.modal.step_operators import ModalStepOperator

DEFAULT_TIMEOUT_SECONDS = 86400  # 24 hours


class ModalStepOperatorSettings(BaseSettings):
    """Settings for the Modal step operator.

    Specifying the region and cloud provider is only available for Enterprise
    and Team plan customers.

    Certain combinations of settings are not available. It is suggested to err
    on the side of looser settings rather than more restrictive ones to avoid
    pipeline execution failures. In the case of failures, however, Modal
    provides detailed error messages that can help identify what is
    incompatible. See more in the Modal docs at https://modal.com/docs/guide/region-selection.
    """

    gpu: Optional[str] = Field(
        None,
        description="GPU type for step execution. Must be a valid Modal GPU type. "
        "Examples: 'T4' (cost-effective), 'A100' (high-performance), 'V100' (training workloads). "
        "Use ResourceSettings.gpu_count to specify number of GPUs. If not specified, uses CPU-only execution",
    )
    region: Optional[str] = Field(
        None,
        description="Cloud region for step execution. Must be a valid region for the selected cloud provider. "
        "Examples: 'us-east-1', 'us-west-2', 'eu-west-1'. If not specified, Modal uses default region "
        "based on cloud provider and availability",
    )
    cloud: Optional[str] = Field(
        None,
        description="Cloud provider for step execution. Must be a valid Modal-supported cloud provider. "
        "Examples: 'aws', 'gcp'. If not specified, Modal uses default cloud provider "
        "based on workspace configuration",
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
        description=f"Maximum execution time in seconds for step completion. Must be between 1 and {DEFAULT_TIMEOUT_SECONDS} seconds. "
        f"Examples: 3600 (1 hour), 7200 (2 hours), {DEFAULT_TIMEOUT_SECONDS} (24 hours maximum). "
        "Step execution will be terminated if it exceeds this timeout",
    )


class ModalStepOperatorConfig(
    BaseStepOperatorConfig, ModalStepOperatorSettings
):
    """Configuration for the Modal step operator.

    Attributes:
        token_id: Modal API token ID (ak-xxxxx format) for authentication.
        token_secret: Modal API token secret (as-xxxxx format) for authentication.

    Note: If token_id and token_secret are provided, both fields must be set.
    If they are not provided, Modal falls back to its default authentication
    (~/.modal.toml or environment variables).
    All other configuration options (modal_environment, gpu, region, etc.)
    are inherited from ModalStepOperatorSettings.
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
    def validate_modal_token_pair(self) -> "ModalStepOperatorConfig":
        """Validate that Modal token fields are configured together."""
        token_id = self.token_id.strip() if self.token_id else None
        token_secret = self.token_secret.strip() if self.token_secret else None

        if bool(token_id) != bool(token_secret):
            raise ValueError(
                "Modal token_id and token_secret must be configured together."
            )

        return self

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True


class ModalStepOperatorFlavor(BaseStepOperatorFlavor):
    """Modal step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MODAL_STEP_OPERATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/modal.png"

    @property
    def config_class(self) -> Type[ModalStepOperatorConfig]:
        """Returns `ModalStepOperatorConfig` config class.

        Returns:
            The config class.
        """
        return ModalStepOperatorConfig

    @property
    def implementation_class(self) -> Type["ModalStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.modal.step_operators import ModalStepOperator

        return ModalStepOperator
