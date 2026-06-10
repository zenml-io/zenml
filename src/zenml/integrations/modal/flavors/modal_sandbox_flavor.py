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
"""Modal sandbox flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.integrations.modal import MODAL_SANDBOX_FLAVOR
from zenml.integrations.modal.flavors.modal_step_operator_flavor import (
    DEFAULT_TIMEOUT_SECONDS,
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.modal.sandboxes import ModalSandbox


class ModalSandboxSettings(BaseSandboxSettings, ModalStepOperatorSettings):
    """Per-step settings for the Modal sandbox."""

    image: str = Field(
        default="python:3.11-slim",
        description="Docker image used to boot the Modal sandbox. Accepts "
        "any registry reference Modal can pull. Example: "
        "'python:3.11-slim', 'my-registry/my-image:tag'.",
    )
    cpu: Optional[int] = Field(
        default=None,
        description="Number of CPU cores requested for the sandbox. Must be "
        "a positive integer accepted by Modal. Examples: 1, 2, 4. If not "
        "set, Modal's default CPU allocation applies",
    )
    memory: Optional[str] = Field(
        default=None,
        description="Memory requested for the sandbox as a string with a "
        "byte unit. Examples: '512MB', '2GB'. If not set, Modal's default "
        "memory allocation applies",
    )
    timeout: int = Field(
        default=3600,
        ge=1,
        le=DEFAULT_TIMEOUT_SECONDS,
        description="Sandbox lifetime (TTL) in seconds. Modal terminates "
        "the sandbox once this elapses, regardless of running commands. "
        "Note that closing a session does NOT terminate the sandbox; only "
        "destroy() or this TTL does, so unused sandboxes keep billing "
        "until then. Examples: 600 (10 minutes), 3600 (1 hour, default)",
    )


class ModalSandboxConfig(
    BaseSandboxConfig, ModalSandboxSettings, ModalStepOperatorConfig
):
    """Configuration for the Modal sandbox component."""

    app_name: str = Field(
        default="zenml-sandbox",
        description="Name of the Modal App that hosts Sessions created by "
        "this component. Looked up (or created) lazily.",
    )


class ModalSandboxFlavor(BaseSandboxFlavor):
    """Modal sandbox flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            ``"modal"``.
        """
        return MODAL_SANDBOX_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/sandbox/modal.png"

    @property
    def config_class(self) -> Type[ModalSandboxConfig]:
        """Config class.

        Returns:
            ``ModalSandboxConfig``.
        """
        return ModalSandboxConfig

    @property
    def implementation_class(self) -> Type["ModalSandbox"]:
        """Implementation class.

        Returns:
            ``ModalSandbox``.
        """
        from zenml.integrations.modal.sandboxes import ModalSandbox

        return ModalSandbox
