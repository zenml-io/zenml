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

from pydantic import Field

from zenml.integrations.modal import MODAL_ORCHESTRATOR_FLAVOR
from zenml.integrations.modal.flavors.modal_base_flavor import (
    ModalCredentialsMixin,
    ModalSettingsMixin,
)
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.modal.orchestrators import ModalOrchestrator


class ModalOrchestratorSettings(ModalSettingsMixin):
    """Settings for Modal sandboxes created by the orchestrator.

    The shared compute/placement fields (gpu, region, cloud, modal_environment,
    timeout) come from :class:`ModalSettingsMixin`. They apply to the sandbox
    that controls the run and to child sandboxes that execute individual steps.
    """

    synchronous: bool = Field(
        True,
        description="Whether to wait for the orchestration Modal Sandbox to finish after submission. When enabled, controller failures are surfaced to the submitting process.",
    )


class ModalOrchestratorConfig(
    BaseOrchestratorConfig, ModalCredentialsMixin, ModalOrchestratorSettings
):
    """Configuration for the Modal orchestrator.

    Authentication fields (token_id, token_secret) come from
    :class:`ModalCredentialsMixin`.
    """

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
