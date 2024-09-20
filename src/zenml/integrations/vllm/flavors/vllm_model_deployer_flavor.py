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
"""vLLM model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.vllm import VLLM_MODEL_DEPLOYER
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.vllm.model_deployers import VLLMModelDeployer


class VLLMModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for vLLM Inference model deployer."""

    service_path: str = ""


class VLLMModelDeployerFlavor(BaseModelDeployerFlavor):
    """vLLM model deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return VLLM_MODEL_DEPLOYER

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
        return "https://raw.githubusercontent.com/vllm-project/vllm/main/docs/source/assets/logos/vllm-logo-text-dark.png"

    @property
    def config_class(self) -> Type[VLLMModelDeployerConfig]:
        """Returns `VLLMModelDeployerConfig` config class.

        Returns:
            The config class.
        """
        return VLLMModelDeployerConfig

    @property
    def implementation_class(self) -> Type["VLLMModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.vllm.model_deployers import VLLMModelDeployer

        return VLLMModelDeployer
