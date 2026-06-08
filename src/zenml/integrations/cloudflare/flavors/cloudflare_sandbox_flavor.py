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
"""Cloudflare sandbox flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.integrations.cloudflare import CLOUDFLARE_SANDBOX_FLAVOR
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.cloudflare.sandboxes import CloudflareSandbox


CLOUDFLARE_STEP_IMAGE_SENTINEL = "<step>"
DEFAULT_BRIDGE_TIMEOUT_MS = 120_000


class CloudflareSandboxSettings(BaseSandboxSettings):
    """Per-step settings for the Cloudflare sandbox."""

    base_image: Optional[str] = Field(
        default=None,
        description="Container image override for the Cloudflare sandbox. "
        "Reserved for future use: the current bridge HTTP API does not "
        "accept a custom image on POST /v1/sandbox; the Worker's bound "
        "container image is used. Accepts the '<step>' sentinel to reuse "
        "the active step's containerized-orchestrator image. Example: "
        "'docker.io/library/python:3.11-slim'",
    )
    timeout_ms: Optional[int] = Field(
        default=None,
        ge=1,
        description="Per-exec timeout in milliseconds. Passed to the bridge "
        "as timeout_ms on POST /v1/sandbox/:id/exec. Must be a positive "
        "integer. Example: 60000 for a one-minute cap. When omitted the "
        "component-level default applies",
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Default working directory inside the sandbox workspace. "
        "Server-side paths are confined to /workspace, so this should be a "
        "relative or absolute path under that root. Example: "
        "'/workspace/my-project'",
    )


class CloudflareSandboxConfig(BaseSandboxConfig, CloudflareSandboxSettings):
    """Configuration for the Cloudflare sandbox component."""

    worker_url: str = Field(
        description="URL of the deployed Cloudflare Sandbox bridge Worker. "
        "Must be an https:// URL pointing at a Worker that implements the "
        "bridge HTTP API (POST /v1/sandbox, /exec, /file, /session). "
        "Example: 'https://sandbox-bridge.example.workers.dev'",
    )
    api_key: Optional[str] = SecretField(
        default=None,
        description="Bearer token for the bridge Worker (the SANDBOX_API_KEY "
        "configured at deploy time on the Worker). Stored as a ZenML secret. "
        "When set, sent as 'Authorization: Bearer <token>' on every request "
        "to the bridge. Example: a random 32+ byte hex string",
    )
    default_image: str = Field(
        default="docker.io/library/python:3.11-slim",
        description="Container image used when no per-step base_image is "
        "specified. Reserved for future use; currently informational only "
        "until the bridge supports image overrides. Example: "
        "'docker.io/library/python:3.11-slim'",
    )

    @property
    def is_remote(self) -> bool:
        """Cloudflare sandboxes run on Cloudflare's infrastructure.

        Returns:
            ``True``: the ZenML server is not the host.
        """
        return True


class CloudflareSandboxFlavor(BaseSandboxFlavor):
    """Cloudflare sandbox flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            ``"cloudflare"``.
        """
        return CLOUDFLARE_SANDBOX_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """URL to user-facing docs for this flavor.

        Returns:
            The flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """URL to SDK docs for this flavor.

        Returns:
            The flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """Dashboard logo URL.

        Returns:
            The flavor logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/sandbox/cloudflare.png"

    @property
    def config_class(self) -> Type[CloudflareSandboxConfig]:
        """Config class.

        Returns:
            ``CloudflareSandboxConfig``.
        """
        return CloudflareSandboxConfig

    @property
    def implementation_class(self) -> Type["CloudflareSandbox"]:
        """Implementation class.

        Returns:
            ``CloudflareSandbox``.
        """
        from zenml.integrations.cloudflare.sandboxes import CloudflareSandbox

        return CloudflareSandbox
