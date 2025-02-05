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
        gpu_type: Optional GPU type to use for the deployment.
        environment_variables: Optional environment variables for the deployment.
        service_path: Optional path to store service information.
    """

    baseten_api_key: Optional[str] = None
    model_name: Optional[str] = None
    gpu_type: Optional[str] = None
    environment_variables: Optional[dict] = None
    service_path: Optional[str] = "./baseten_services"


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
