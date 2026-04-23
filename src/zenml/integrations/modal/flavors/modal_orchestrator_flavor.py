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

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal import MODAL_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.modal.orchestrators import ModalOrchestrator


class ModalOrchestratorSettings(BaseSettings):
    """Settings for the Modal orchestrator.

    Region and cloud selection are only available on Modal's Enterprise and
    Team plans. When unset, Modal picks a region automatically. See the Modal
    docs for valid combinations: https://modal.com/docs/guide/region-selection.
    """

    gpu: Optional[str] = Field(
        default=None,
        description="GPU type to request for each step sandbox (for example "
        "'A100' or 'H100'). Combined with resource_settings.gpu_count to form "
        "the Modal GPU specifier. Leave unset for CPU-only runs.",
    )
    region: Optional[str] = Field(
        default=None,
        description="Modal region for each step sandbox (for example "
        "'us-east-1'). Enterprise/Team plans only.",
    )
    cloud: Optional[str] = Field(
        default=None,
        description="Modal cloud provider selector for each step sandbox. "
        "Enterprise/Team plans only.",
    )
    synchronous: bool = Field(
        default=True,
        description="Whether the orchestrator blocks the client until the "
        "pipeline finishes. If False, the pipeline submission returns "
        "immediately and steps run in the background on Modal.",
    )


class ModalOrchestratorConfig(
    BaseOrchestratorConfig, ModalOrchestratorSettings
):
    """Configuration for the Modal orchestrator."""

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

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous


class ModalOrchestratorFlavor(BaseOrchestratorFlavor):
    """Modal orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MODAL_ORCHESTRATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/modal.png"

    @property
    def config_class(self) -> Type[ModalOrchestratorConfig]:
        """Returns ``ModalOrchestratorConfig`` config class.

        Returns:
            The config class.
        """
        return ModalOrchestratorConfig

    @property
    def implementation_class(self) -> Type["ModalOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.modal.orchestrators import ModalOrchestrator

        return ModalOrchestrator
