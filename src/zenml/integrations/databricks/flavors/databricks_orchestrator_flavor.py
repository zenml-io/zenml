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

from zenml.config.base_settings import BaseSettings
from zenml.integrations.databricks import DATABRICKS_ORCHESTRATOR_FLAVOR
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.databricks.orchestrators import (
        DatabricksOrchestrator,
    )


logger = get_logger(__name__)


class DatabricksOrchestratorSettings(BaseSettings):
    """Databricks orchestrator base settings.

    Attributes:
        cluster_name: Databricks cluster name.
    """

    # Resources
    cluster_name: Optional[str] = None


class DatabricksOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, DatabricksOrchestratorSettings
):
    """Databricks orchestrator base config.

    Attributes:
        disable_step_based_settings: whether to disable step-based settings.
            If True, the orchestrator will run all steps with the pipeline
            settings in one single VM. If False, the orchestrator will run
            each step with its own settings in separate VMs if provided.
    """

    disable_step_based_settings: bool = False

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False


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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubeflow.png"

    @property
    def config_class(self) -> Type[DatabricksOrchestratorConfig]:
        """Returns `KubeflowOrchestratorConfig` config class.

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
