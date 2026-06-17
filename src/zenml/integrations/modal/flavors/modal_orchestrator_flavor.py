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
"""Modal orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal import MODAL_ORCHESTRATOR_FLAVOR
from zenml.integrations.modal.flavors.modal_step_operator_flavor import (
    DEFAULT_TIMEOUT_SECONDS,
)
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.modal.orchestrators import ModalOrchestrator


class ModalOrchestratorSettings(BaseSettings):
    """Settings for Modal sandboxes created by the orchestrator.

    These settings can apply to the sandbox that controls the run and to child
    sandboxes that execute individual steps.
    """

    gpu: Optional[str] = Field(
        None,
        description="GPU type for Modal sandboxes, for example 'T4' or 'A100'. "
        "Use ResourceSettings.gpu_count to request multiple GPUs. If not set, sandboxes run on CPU.",
    )
    region: Optional[str] = Field(
        None,
        description="Cloud region for Modal sandboxes, for example 'us-east-1'. If not set, Modal chooses a default region.",
    )
    cloud: Optional[str] = Field(
        None,
        description="Cloud provider for Modal sandboxes, for example 'aws' or 'gcp'. If not set, Modal chooses a default provider.",
    )
    modal_environment: Optional[str] = Field(
        None,
        description="Modal environment name passed to App.lookup(..., environment_name=...), for example 'main' or 'staging'. If not set, Modal uses the default environment.",
    )
    timeout: int = Field(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=DEFAULT_TIMEOUT_SECONDS,
        description=f"Maximum Modal Sandbox lifetime in seconds, from 1 to {DEFAULT_TIMEOUT_SECONDS}. Modal terminates the sandbox if it exceeds this timeout.",
    )
    synchronous: bool = Field(
        True,
        description="Whether to wait for the orchestration Modal Sandbox to finish after submission. When enabled, controller failures are surfaced to the submitting process.",
    )


class ModalOrchestratorConfig(
    BaseOrchestratorConfig, ModalOrchestratorSettings
):
    """Configuration for the Modal orchestrator."""

    token_id: Optional[str] = SecretField(
        default=None,
        description="Modal API token ID for authentication. Must be configured together with token_secret.",
    )
    token_secret: Optional[str] = SecretField(
        default=None,
        description="Modal API token secret for authentication. Must be configured together with token_id.",
    )

    @model_validator(mode="after")
    def validate_modal_token_pair(self) -> "ModalOrchestratorConfig":
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
        """Checks if this stack component is running remotely."""
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally."""
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronously or not."""
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator supports schedules."""
        return False

    @property
    def supports_client_side_caching(self) -> bool:
        """Whether the orchestrator supports client-side caching."""
        return False

    @property
    def handles_step_retries(self) -> bool:
        """Whether the orchestrator handles step retries internally."""
        return False


class ModalOrchestratorFlavor(BaseOrchestratorFlavor):
    """Modal orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor."""
        return MODAL_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor."""
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor."""
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard."""
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/modal.png"

    @property
    def config_class(self) -> Type[ModalOrchestratorConfig]:
        """Returns the Modal orchestrator config class."""
        return ModalOrchestratorConfig

    @property
    def implementation_class(self) -> Type["ModalOrchestrator"]:
        """Implementation class for this flavor."""
        from zenml.integrations.modal.orchestrators import ModalOrchestrator

        return ModalOrchestrator
