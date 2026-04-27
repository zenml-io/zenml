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
"""Databricks orchestrator base config and settings."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.databricks import DATABRICKS_ORCHESTRATOR_FLAVOR
from zenml.integrations.databricks.flavors.databricks_shared_settings import (
    DatabricksBaseSettings,
)
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.databricks.orchestrators import (
        DatabricksOrchestrator,
    )


class DatabricksOrchestratorSettings(DatabricksBaseSettings):
    """Databricks orchestrator settings."""


class DatabricksOrchestratorConfig(
    BaseOrchestratorConfig, DatabricksOrchestratorSettings
):
    """Databricks orchestrator base config.

    Attributes:
        host: Databricks host.
        client_id: Databricks client id.
        client_secret: Databricks client secret.
    """

    host: str
    client_id: Optional[str] = SecretField(default=None)
    client_secret: Optional[str] = SecretField(default=None)

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return True


class DatabricksOrchestratorFlavor(BaseOrchestratorFlavor):
    """Databricks orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DATABRICKS_ORCHESTRATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/databricks.png"

    @property
    def config_class(self) -> Type[DatabricksOrchestratorConfig]:
        """Returns DatabricksOrchestratorConfig config class.

        Returns:
                The config class.
        """
        return DatabricksOrchestratorConfig

    @property
    def implementation_class(self) -> Type["DatabricksOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.databricks.orchestrators import (
            DatabricksOrchestrator,
        )

        return DatabricksOrchestrator
