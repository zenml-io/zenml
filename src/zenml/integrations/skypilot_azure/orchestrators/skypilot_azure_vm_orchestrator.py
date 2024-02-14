#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the a Skypilot based Azure VM orchestrator."""

from typing import TYPE_CHECKING, Optional, Type, cast

import sky

from zenml.integrations.skypilot.orchestrators.skypilot_base_vm_orchestrator import (
    SkypilotBaseOrchestrator,
)
from zenml.integrations.skypilot_azure.flavors.skypilot_orchestrator_azure_vm_flavor import (
    SkypilotAzureOrchestratorConfig,
    SkypilotAzureOrchestratorSettings,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings

logger = get_logger(__name__)


class SkypilotAzureOrchestrator(SkypilotBaseOrchestrator):
    """Orchestrator responsible for running pipelines remotely in a VM on Azure.

    This orchestrator does not support running on a schedule.
    """

    DEFAULT_INSTANCE_TYPE: str = "Standard_B1ms"

    @property
    def cloud(self) -> sky.clouds.Cloud:
        """The type of sky cloud to use.

        Returns:
            A `sky.clouds.Cloud` instance.
        """
        return sky.clouds.Azure()

    @property
    def config(self) -> SkypilotAzureOrchestratorConfig:
        """Returns the `SkypilotAzureOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SkypilotAzureOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Skypilot orchestrator.

        Returns:
            The settings class.
        """
        return SkypilotAzureOrchestratorSettings

    def prepare_environment_variable(self, set: bool = True) -> None:
        """Set up Environment variables that are required for the orchestrator.

        Args:
            set: Whether to set the environment variables or not.
        """
        pass
