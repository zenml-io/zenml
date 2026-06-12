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

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.cloudflare import CLOUDFLARE_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)

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
        "step entrypoint each get this budget). Example: 600000 (10 "
        "minutes). Long-running training steps need a higher value",
    )


class CloudflareOrchestratorConfig(
    BaseOrchestratorConfig, CloudflareOrchestratorSettings
):
    """Configuration for the Cloudflare orchestrator.

    The orchestrator carries no connection configuration of its own: it
    launches steps through the Cloudflare sandbox component that must be
    part of the same stack, reusing its bridge Worker URL and API key.
    """

    @property
    def is_local(self) -> bool:
        """Whether this component runs locally.

        The orchestration loop runs on the client, but the steps execute
        on Cloudflare.

        Returns:
            False.
        """
        return False

    @property
    def is_remote(self) -> bool:
        """Whether this component runs remotely.

        Steps execute on Cloudflare, so this is conceptually a remote
        orchestrator. It still reports ``False`` for now: ``True`` makes
        pipeline submission require a remote ZenML server, and this proof
        of concept must remain runnable against a local server (where the
        in-sandbox step is expected to fail at server contact). Flip this
        to ``True`` once the flavor graduates from POC.

        Returns:
            False.
        """
        return False

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronously.

        The POC drives sandboxes from the client and blocks until the
        last step finished.

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
