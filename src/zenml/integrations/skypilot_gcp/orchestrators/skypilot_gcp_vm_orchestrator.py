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
"""Implementation of the a Skypilot-based GCP VM orchestrator."""

from typing import TYPE_CHECKING, cast

import sky

from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.skypilot.orchestrators.skypilot_base_vm_orchestrator import (
    SkypilotBaseOrchestrator,
)
from zenml.integrations.skypilot_gcp.flavors.skypilot_orchestrator_gcp_vm_flavor import (
    SkypilotGCPOrchestratorConfig,
    SkypilotGCPOrchestratorSettings,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings

logger = get_logger(__name__)


class SkypilotGCPOrchestrator(
    SkypilotBaseOrchestrator, GoogleCredentialsMixin
):
    """Orchestrator responsible for running pipelines remotely in a VM on GCP.

    This orchestrator does not support running on a schedule.
    """

    DEFAULT_INSTANCE_TYPE: str = "n1-standard-4"

    @property
    def cloud(self) -> sky.clouds.Cloud:
        """The type of sky cloud to use.

        Returns:
            A `sky.clouds.Cloud` instance.
        """
        return sky.clouds.GCP()

    @property
    def config(self) -> SkypilotGCPOrchestratorConfig:
        """Returns the `SkypilotGCPOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SkypilotGCPOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> type["BaseSettings"] | None:
        """Settings class for the Skypilot orchestrator.

        Returns:
            The settings class.
        """
        return SkypilotGCPOrchestratorSettings

    def prepare_environment_variable(self, set: bool = True) -> None:
        """Set up Environment variables that are required for the orchestrator.

        Args:
            set: Whether to set the environment variables or not.
        """
