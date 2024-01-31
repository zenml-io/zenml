"""Huggingface model deployer flavor."""
from typing import TYPE_CHECKING, Dict, Optional, Type

from pydantic import BaseModel

from zenml.config.base_settings import BaseSettings
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
    """Huggingface Inference Endpoint configuration."""

    endpoint_name: Optional[str] = "zenml-"
    repository: Optional[str] = None
    framework: Optional[str] = None
    accelerator: Optional[str] = None
    instance_size: Optional[str] = None
    instance_type: Optional[str] = None
    region: Optional[str] = None
    vendor: Optional[str] = None
    token: Optional[str] = None
    account_id: Optional[str] = None
    min_replica: Optional[int] = 0
    max_replica: Optional[int] = 1
    revision: Optional[str] = None
    task: Optional[str] = None
    custom_image: Optional[Dict] = None
    namespace: Optional[str] = None
    endpoint_type: str = "public"


class HuggingFaceModelDeployerSettings(HuggingFaceBaseConfig, BaseSettings):
    """Settings for the Huggingface model deployer."""


class HuggingFaceModelDeployerConfig(
    BaseModelDeployerConfig, HuggingFaceModelDeployerSettings
):
    """Configuration for the Huggingface model deployer.

    Attributes:
        token: Huggingface token used for authentication
        namespace: Huggingface namespace used to list endpoints
    """

    token: str = SecretField()

    # The namespace to list endpoints for. Set to `"*"` to list all endpoints
    # from all namespaces (i.e. personal namespace and all orgs the user belongs to).
    namespace: str


class HuggingFaceModelDeployerFlavor(BaseModelDeployerFlavor):
    """Huggingface Endpoint model deployer flavor."""

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
