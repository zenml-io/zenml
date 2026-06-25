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
"""SSH orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.ssh import SSH_ORCHESTRATOR_FLAVOR
from zenml.integrations.ssh.flavors.base import (
    BaseSSHComponentConfig,
    BaseSSHComponentSettings,
)
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.ssh.orchestrators import SSHOrchestrator


class SSHOrchestratorSettings(BaseSSHComponentSettings):
    """Settings for the SSH orchestrator."""


class SSHOrchestratorConfig(
    BaseOrchestratorConfig, BaseSSHComponentConfig, SSHOrchestratorSettings
):
    """Configuration for the SSH orchestrator."""

    @property
    def is_remote(self) -> bool:
        """Whether the orchestrator runs the pipeline remotely.

        Returns:
            True
        """
        return True

    @property
    def is_local(self) -> bool:
        """Whether the orchestrator runs the pipeline locally.

        Returns:
            False
        """
        return False

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator supports scheduled pipeline runs.

        Returns:
            False.
        """
        return False


class SSHOrchestratorFlavor(BaseOrchestratorFlavor):
    """SSH orchestrator flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            The flavor name.
        """
        return SSH_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/ssh.png"

    @property
    def config_class(self) -> Type[SSHOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return SSHOrchestratorConfig

    @property
    def implementation_class(self) -> Type["SSHOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.ssh.orchestrators import SSHOrchestrator

        return SSHOrchestrator
