#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Cloudflare orchestrator flavor (proof of concept)."""

from typing import TYPE_CHECKING, Optional, Type
from urllib.parse import urlparse

from pydantic import Field, field_validator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.cloudflare import CLOUDFLARE_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.cloudflare.orchestrators import (
        CloudflareOrchestrator,
    )


class CloudflareOrchestratorSettings(BaseSettings):
    """Settings for the Cloudflare orchestrator."""

    zenml_requirement: str = Field(
        default="zenml",
        description="Pip requirement specifier used to install ZenML inside "
        "each step sandbox before the step entrypoint runs. Examples: "
        "'zenml', 'zenml==0.94.0'. The sandbox image does not ship with "
        "ZenML preinstalled, so this is installed on every step launch",
    )
    step_timeout_ms: int = Field(
        default=600_000,
        description="Per-command timeout in milliseconds for sandbox "
        "execs launched by the orchestrator (the pip bootstrap and the "
        "step entrypoint each get this budget)",
    )


class CloudflareOrchestratorConfig(
    BaseOrchestratorConfig, CloudflareOrchestratorSettings
):
    """Configuration for the Cloudflare orchestrator."""

    worker_url: str = Field(
        description="URL of the deployed Cloudflare Sandbox bridge Worker "
        "used to launch step containers. Must be an https:// URL pointing "
        "at a Worker that implements the bridge HTTP API. Example: "
        "'https://sandbox-bridge.example.workers.dev'",
    )
    api_key: Optional[str] = SecretField(
        default=None,
        description="Bearer token for the bridge Worker (the "
        "SANDBOX_API_KEY configured at deploy time on the Worker). Stored "
        "as a ZenML secret. Example: a random 32+ byte hex string",
    )

    @field_validator("worker_url")
    @classmethod
    def _validate_worker_url_scheme(cls, value: str) -> str:
        """Require https for the bridge URL.

        Args:
            value: The configured worker URL.

        Returns:
            The validated URL, unchanged.

        Raises:
            ValueError: If the URL scheme is not https (or http to
                localhost/127.0.0.1).
        """
        parsed = urlparse(value)
        if parsed.scheme == "https":
            return value
        if parsed.scheme == "http" and parsed.hostname in (
            "localhost",
            "127.0.0.1",
        ):
            return value
        raise ValueError(
            f"Invalid worker_url '{value}': the Cloudflare sandbox bridge "
            "must be reached over https (the API key is sent as a bearer "
            "token on every request). Plain http is only allowed for "
            "localhost/127.0.0.1 when testing a local bridge."
        )

    @property
    def is_local(self) -> bool:
        """Whether this component runs locally.

        Returns:
            False.
        """
        return False

    @property
    def is_remote(self) -> bool:
        """Whether this component runs remotely.

        Returns:
            False.
        """
        # Reports False even though steps run on Cloudflare: True would make
        # pipeline submission require a remote ZenML server, and this POC must
        # remain runnable against a local server. Flip once it graduates.
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronously.

        Returns:
            True.
        """
        return True


class CloudflareOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Cloudflare orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return CLOUDFLARE_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """URL to the flavor documentation.

        Returns:
            The URL to the flavor documentation.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """URL to the SDK documentation.

        Returns:
            The URL to the SDK documentation.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """URL to the flavor logo.

        Returns:
            The URL to the flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/cloudflare.png"

    @property
    def config_class(self) -> Type[CloudflareOrchestratorConfig]:
        """Config class.

        Returns:
            The config class.
        """
        return CloudflareOrchestratorConfig

    @property
    def implementation_class(self) -> Type["CloudflareOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.cloudflare.orchestrators import (
            CloudflareOrchestrator,
        )

        return CloudflareOrchestrator
