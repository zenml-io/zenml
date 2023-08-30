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
"""Implementation of the a Skypilot based AWS VM orchestrator."""

from typing import TYPE_CHECKING, Optional, Type, cast

import sky

from zenml.integrations.skypilot.flavors.skypilot_orchestrator_aws_vm_flavor import (
    SkypilotAWSOrchestratorConfig,
    SkypilotAWSOrchestratorSettings,
)
from zenml.integrations.skypilot.orchestrators.skypilot_base_vm_orchestrator import (
    SkypilotBaseOrchestrator,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.stack import Stack

logger = get_logger(__name__)


class SkypilotAWSOrchestrator(SkypilotBaseOrchestrator):
    """Orchestrator responsible for running pipelines remotely in a VM.

    This orchestrator does not support running on a schedule.
    """

    DEFAULT_INSTANCE_TYPE: str = "t3.xlarge"

    @property
    def cloud(self) -> sky.clouds.Cloud:
        """The type of sky cloud to use.

        Returns:
            A `sky.clouds.Cloud` instance.
        """
        return sky.clouds.AWS()

    def get_setup(self, stack: Optional["Stack"]) -> Optional[str]:
        """Run to set up the sky job.

        Args:
            stack: The stack to use.

        Returns:
            A `setup` string.
        """
        assert stack.container_registry is not None
        return f"aws ecr get-login-password --region {stack.container_registry._get_region()} | docker login --username AWS --password-stdin {stack.container_registry.config.uri}"

    @property
    def config(self) -> SkypilotAWSOrchestratorConfig:
        """Returns the `SkypilotAWSOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SkypilotAWSOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Skypilot orchestrator.

        Returns:
            The settings class.
        """
        return SkypilotAWSOrchestratorSettings
