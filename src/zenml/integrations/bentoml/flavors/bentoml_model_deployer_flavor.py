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
"""BentoML model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.bentoml import BENTOML_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.bentoml.model_deployers import BentoMLModelDeployer


class BentoMLModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for the BentoMLModelDeployer."""

    service_path: str = ""


class BentoMLModelDeployerFlavor(BaseModelDeployerFlavor):
    """Flavor for the BentoML model deployer."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            Name of the flavor.
        """
        return BENTOML_MODEL_DEPLOYER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/bentoml.png"

    @property
    def config_class(self) -> Type[BentoMLModelDeployerConfig]:
        """Returns `BentoMLModelDeployerConfig` config class.

        Returns:
                The config class.
        """
        return BentoMLModelDeployerConfig

    @property
    def implementation_class(self) -> Type["BentoMLModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.bentoml.model_deployers import (
            BentoMLModelDeployer,
        )

        return BentoMLModelDeployer
