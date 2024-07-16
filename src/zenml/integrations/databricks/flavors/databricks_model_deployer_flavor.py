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
"""Databricks model deployer flavor."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from databricks.sdk.service.serving import (
    ServedModelInputWorkloadSize,
    ServedModelInputWorkloadType,
)
from pydantic import BaseModel

from zenml.integrations.databricks import DATABRICKS_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.databricks.model_deployers.databricks_model_deployer import (
        DatabricksModelDeployer,
    )


class DatabricksBaseConfig(BaseModel):
    """Databricks Inference Endpoint configuration."""

    workload_size: ServedModelInputWorkloadSize
    scale_to_zero_enabled: bool = False
    env_vars: Optional[Dict[str, str]] = None
    workload_type: Optional[ServedModelInputWorkloadType] = None
    endpoint_secret_name: Optional[str] = None


class DatabricksModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for the Databricks model deployer.

    Attributes:
        host: Databricks host.
        secret_name: Secret name to use for authentication.
        client_id: Databricks client id.
        client_secret: Databricks client secret.
    """

    host: str
    secret_name: Optional[str] = None
    client_id: Optional[str] = SecretField(default=None)
    client_secret: Optional[str] = SecretField(default=None)


class DatabricksModelDeployerFlavor(BaseModelDeployerFlavor):
    """Databricks Endpoint model deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DATABRICKS_MODEL_DEPLOYER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/databricks.png"

    @property
    def config_class(self) -> Type[DatabricksModelDeployerConfig]:
        """Returns `DatabricksModelDeployerConfig` config class.

        Returns:
            The config class.
        """
        return DatabricksModelDeployerConfig

    @property
    def implementation_class(self) -> Type["DatabricksModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.databricks.model_deployers.databricks_model_deployer import (
            DatabricksModelDeployer,
        )

        return DatabricksModelDeployer
