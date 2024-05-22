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
"""Hugging Face model deployer flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic import BaseModel

from zenml.integrations.huggingface import HUGGINGFACE_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.huggingface.model_deployers.huggingface_model_deployer import (
        HuggingFaceModelDeployer,
    )


class HuggingFaceBaseConfig(BaseModel):
    """Hugging Face Inference Endpoint configuration."""

    repository: Optional[str] = None
    framework: Optional[str] = None
    accelerator: Optional[str] = None
    instance_size: Optional[str] = None
    instance_type: Optional[str] = None
    region: Optional[str] = None
    vendor: Optional[str] = None
    account_id: Optional[str] = None
    min_replica: int = 0
    max_replica: int = 1
    revision: Optional[str] = None
    task: Optional[str] = None
    custom_image: Optional[Dict[str, Any]] = None
    endpoint_type: str = "public"
    secret_name: Optional[str] = None
    namespace: Optional[str] = None


class HuggingFaceModelDeployerConfig(
    BaseModelDeployerConfig, HuggingFaceBaseConfig
):
    """Configuration for the Hugging Face model deployer.

    Attributes:
        token: Hugging Face token used for authentication
        namespace: Hugging Face namespace used to list endpoints
    """

    token: Optional[str] = SecretField(default=None)

    # The namespace to list endpoints for. Set to `"*"` to list all endpoints
    # from all namespaces (i.e. personal namespace and all orgs the user belongs to).
    namespace: str


class HuggingFaceModelDeployerFlavor(BaseModelDeployerFlavor):
    """Hugging Face Endpoint model deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return HUGGINGFACE_MODEL_DEPLOYER_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_registry/huggingface.png"

    @property
    def config_class(self) -> Type[HuggingFaceModelDeployerConfig]:
        """Returns `HuggingFaceModelDeployerConfig` config class.

        Returns:
            The config class.
        """
        return HuggingFaceModelDeployerConfig

    @property
    def implementation_class(self) -> Type["HuggingFaceModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.huggingface.model_deployers.huggingface_model_deployer import (
            HuggingFaceModelDeployer,
        )

        return HuggingFaceModelDeployer
