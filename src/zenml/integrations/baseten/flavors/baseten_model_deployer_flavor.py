#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Baseten model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.baseten.constants import BASETEN_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.baseten.model_deployers import BasetenModelDeployer


class BasetenModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for the Baseten model deployer.

    Attributes:
        baseten_api_key: The API key for Baseten authentication.
        model_name: Optional name for the model in Baseten.
        gpu: Optional GPU type to use for the deployment (e.g., 'T4', 'A10G', 'A100').
        cpu: Optional CPU allocation for the deployment (e.g., '1', '2').
        memory: Optional memory allocation for the deployment (e.g., '2Gi', '4Gi').
        replicas: Optional number of replicas for the deployment.
        environment_variables: Optional environment variables for the deployment.
        timeout: Optional timeout in seconds for deployment operations.
        max_retries: Optional maximum number of retries for API operations.
        api_host: Optional API host for Baseten (default: 'https://app.baseten.co').
    """

    baseten_api_key: Optional[str] = None
    model_name: Optional[str] = None
    gpu: Optional[str] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None
    replicas: Optional[int] = None
    environment_variables: Optional[dict] = None
    timeout: Optional[int] = 300
    max_retries: Optional[int] = 3
    api_host: Optional[str] = "https://app.baseten.co"

    def __init__(self, **kwargs):
        """Initialize the configuration with validation.

        Args:
            **kwargs: Keyword arguments for configuration attributes.

        Note:
            For backward compatibility, 'gpu_type' is mapped to 'gpu'.
        """
        # Map old gpu_type to gpu for backward compatibility
        if "gpu_type" in kwargs and "gpu" not in kwargs:
            kwargs["gpu"] = kwargs.pop("gpu_type")

        # Remove legacy service_path if present (no longer used)
        kwargs.pop("service_path", None)

        super().__init__(**kwargs)


class BasetenModelDeployerFlavor(BaseModelDeployerFlavor):
    """Flavor for the Baseten model deployer."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return BASETEN_MODEL_DEPLOYER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/baseten.png"

    @property
    def config_class(self) -> Type[BasetenModelDeployerConfig]:
        """Config class for the Baseten model deployer.

        Returns:
            The config class.
        """
        return BasetenModelDeployerConfig

    @property
    def implementation_class(self) -> Type["BasetenModelDeployer"]:
        """Implementation class for the Baseten model deployer.

        Returns:
            The implementation class.
        """
        from zenml.integrations.baseten.model_deployers import (
            BasetenModelDeployer,
        )

        return BasetenModelDeployer
