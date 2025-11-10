#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""MLflow-Notion model registry flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.integrations.mlflow_notion import (
    MLFLOW_NOTION_MODEL_REGISTRY_FLAVOR,
)
from zenml.model_registries.base_model_registry import (
    BaseModelRegistryConfig,
    BaseModelRegistryFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.mlflow_notion.model_registries import (
        MLFlowNotionModelRegistry,
    )


class MLFlowNotionModelRegistryConfig(BaseModelRegistryConfig):
    """Configuration for the MLflow-Notion model registry."""

    tracking_uri: Optional[str] = Field(
        None,
        description="MLflow tracking server URI for connecting to the MLflow "
        "backend. Examples: 'http://localhost:5000' (remote server), "
        "'databricks' (Databricks workspace), 'sqlite:///mlflow.db' (local "
        "SQLite database). If not specified, uses MLFLOW_TRACKING_URI "
        "environment variable or defaults to local ./mlruns directory",
    )
    registry_uri: Optional[str] = Field(
        None,
        description="MLflow model registry URI when using a separate "
        "registry backend from the tracking server. Only required for "
        "advanced deployments where model registry and experiment tracking "
        "use different backends. If not specified, uses tracking_uri for "
        "both tracking and registry operations",
    )
    notion_api_token: str = SecretField(
        description="Notion API integration token for authentication. Create "
        "a Notion integration at https://www.notion.so/my-integrations and "
        "copy the Internal Integration Token. The integration must have "
        "read/write access to the target database",
    )
    database_id: str = Field(
        description="Notion database ID for storing model registry metadata. "
        "Extract from the database URL format: "
        "notion.so/workspace/{database_id}?v=viewId. The database must be "
        "shared with your Notion integration and follow the standard model "
        "registry schema with properties: Model Name, Version, Stage, "
        "Model Source URI, Description, Created At",
    )
    sync_on_write: bool = Field(
        True,
        description="Controls automatic synchronization behavior for model "
        "registry operations. If True, model registrations and updates in "
        "MLflow immediately mirror to Notion (best-effort, does not fail if "
        "Notion is unavailable). If False, sync only occurs via explicit "
        "sync operations or scheduled sync pipelines. Recommended: True for "
        "real-time collaboration, False for batch-only syncing",
    )


class MLFlowNotionModelRegistryFlavor(BaseModelRegistryFlavor):
    """Model registry flavor for MLflow-Notion hybrid integration."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MLFLOW_NOTION_MODEL_REGISTRY_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_registry/mlflow_notion.png"

    @property
    def config_class(self) -> Type[MLFlowNotionModelRegistryConfig]:
        """Returns `MLFlowNotionModelRegistryConfig` config class.

        Returns:
            The config class.
        """
        return MLFlowNotionModelRegistryConfig

    @property
    def implementation_class(self) -> Type["MLFlowNotionModelRegistry"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.mlflow_notion.model_registries import (
            MLFlowNotionModelRegistry,
        )

        return MLFlowNotionModelRegistry
