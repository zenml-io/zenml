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
"""Lightning orchestrator base config and settings."""

from typing import TYPE_CHECKING, List, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.lightning import LIGHTNING_ORCHESTRATOR_FLAVOR
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.lightning.orchestrators import (
        LightningOrchestrator,
    )

logger = get_logger(__name__)


class LightningOrchestratorSettings(BaseSettings):
    """Lightning orchestrator base settings.

    Configuration for executing pipelines on Lightning AI platform.
    Field descriptions are defined inline using Field() descriptors.
    """

    # Lightning AI Platform Configuration
    main_studio_name: Optional[str] = Field(
        default=None,
        description="Lightning AI studio instance name where the pipeline will execute.",
    )
    machine_type: Optional[str] = Field(
        default=None,
        description="Compute instance type for pipeline execution. "
        "Refer to Lightning AI documentation for available options.",
    )
    user_id: Optional[str] = SecretField(
        default=None, description="Lightning AI user ID for authentication."
    )
    api_key: Optional[str] = SecretField(
        default=None,
        description="Lightning AI API key for platform authentication.",
    )
    username: Optional[str] = Field(
        default=None, description="Lightning AI platform username."
    )
    teamspace: Optional[str] = Field(
        default=None,
        description="Lightning AI teamspace for collaborative pipeline execution.",
    )
    organization: Optional[str] = Field(
        default=None,
        description="Lightning AI organization name for enterprise accounts.",
    )
    custom_commands: Optional[List[str]] = Field(
        default=None,
        description="Additional shell commands to execute in the Lightning AI environment.",
    )
    synchronous: bool = Field(
        default=True,
        description="Whether to wait for pipeline completion. "
        "When `False`, execution continues asynchronously after submission.",
    )


class LightningOrchestratorConfig(
    BaseOrchestratorConfig, LightningOrchestratorSettings
):
    """Lightning orchestrator base config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return False

    @property
    def supports_client_side_caching(self) -> bool:
        """Whether the orchestrator supports client side caching.

        Returns:
            Whether the orchestrator supports client side caching.
        """
        # The Lightning orchestrator starts step studios from a pipeline studio.
        # This is currently not supported when using client-side caching.
        return False


class LightningOrchestratorFlavor(BaseOrchestratorFlavor):
    """Lightning orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return LIGHTNING_ORCHESTRATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/lightning.png"

    @property
    def config_class(self) -> Type[LightningOrchestratorConfig]:
        """Returns `KubeflowOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return LightningOrchestratorConfig

    @property
    def implementation_class(self) -> Type["LightningOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.lightning.orchestrators import (
            LightningOrchestrator,
        )

        return LightningOrchestrator
