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

    Attributes:
        main_studio_name: Main studio name.
        machine_type: Machine type.
        user_id: User id.
        api_key: api_key.
        username: Username.
        teamspace: Teamspace.
        organization: Organization.
        custom_commands: Custom commands to run.
        synchronous: If `True`, the client running a pipeline using this
            orchestrator waits until all steps finish running. If `False`,
            the client returns immediately and the pipeline is executed
            asynchronously. Defaults to `True`. This setting only
            has an effect when specified on the pipeline and will be ignored if
            specified on steps.
    """

    # Resources
    main_studio_name: Optional[str] = None
    machine_type: Optional[str] = None
    user_id: Optional[str] = SecretField(default=None)
    api_key: Optional[str] = SecretField(default=None)
    username: Optional[str] = None
    teamspace: Optional[str] = None
    organization: Optional[str] = None
    custom_commands: Optional[List[str]] = None
    synchronous: bool = True


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
