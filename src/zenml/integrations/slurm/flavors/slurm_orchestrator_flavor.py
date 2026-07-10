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
"""Slurm orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.slurm import SLURM_ORCHESTRATOR_FLAVOR
from zenml.integrations.slurm.flavors.base import (
    SlurmConnectionConfig,
    SlurmJobSettings,
)
from zenml.orchestrators import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.slurm.orchestrators import SlurmOrchestrator


class SlurmOrchestratorSettings(SlurmJobSettings):
    """Settings for the Slurm orchestrator."""


class SlurmOrchestratorConfig(
    BaseOrchestratorConfig,
    SlurmConnectionConfig,
    SlurmOrchestratorSettings,
):
    """Configuration for the Slurm orchestrator."""

    @property
    def is_remote(self) -> bool:
        """Whether this component runs remotely.

        Returns:
            True, since jobs execute on the Slurm cluster.
        """
        return True


class SlurmOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor of the Slurm orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SLURM_ORCHESTRATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/slurm.png"

    @property
    def config_class(self) -> Type[SlurmOrchestratorConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return SlurmOrchestratorConfig

    @property
    def implementation_class(self) -> Type["SlurmOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.slurm.orchestrators import SlurmOrchestrator

        return SlurmOrchestrator
