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

from typing import TYPE_CHECKING, Dict, Optional, Tuple, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.databricks import DATABRICKS_ORCHESTRATOR_FLAVOR
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.databricks.orchestrators import (
        DatabricksOrchestrator,
    )


logger = get_logger(__name__)


class DatabricksOrchestratorSettings(BaseSettings):
    """Databricks orchestrator base settings.

    Attributes:
        spark_version: Spark version.
        num_workers: Number of workers.
        node_type_id: Node type id.
        policy_id: Policy id.
        autotermination_minutes: Autotermination minutes.
        autoscale: Autoscale.
        single_user_name: Single user name.
        spark_conf: Spark configuration.
        spark_env_vars: Spark environment variables.
    """

    # Resources
    spark_version: Optional[str] = None
    num_workers: Optional[int] = None
    node_type_id: Optional[str] = None
    policy_id: Optional[str] = None
    autotermination_minutes: Optional[int] = None
    autoscale: Tuple[int, int] = (2, 3)
    single_user_name: Optional[str] = None
    spark_conf: Optional[Dict[str, str]] = None
    spark_env_vars: Optional[Dict[str, str]] = None


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
    client_id: str = SecretField(default=None)
    client_secret: str = SecretField(default=None)

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
        return "https://upload.wikimedia.org/wikipedia/commons/6/63/Databricks_Logo.png"

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
