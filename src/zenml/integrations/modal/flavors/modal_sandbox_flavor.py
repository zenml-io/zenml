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

    # gpu / region / cloud / modal_environment are inherited from
    # ModalStepOperatorSettings so the two Modal stack components share a
    # single source of truth. cpu_count / memory / gpu_count come from the
    # active step's ResourceSettings.

    base_image: Optional[str] = Field(
        default=None,
        description="Container image override for the Modal sandbox. Accepts "
        "any registry reference Modal can pull (e.g. 'python:3.11-slim', "
        "'my-registry/my-image:tag'). Pass the module-local sentinel "
        "'<step>' to reuse the active step's containerized-orchestrator "
        "image. When None, the component's 'default_image' is used.",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Per-session TTL (in seconds) passed to Modal as the "
        "Sandbox timeout. Modal terminates the Sandbox after this many "
        "seconds regardless of in-flight execs. Example: 3600 for a "
        "1-hour cap. When None, Modal's own default applies.",
    )


class ModalSandboxConfig(BaseSandboxConfig, ModalStepOperatorConfig):
    """Configuration for the Modal sandbox component."""

    # Inherits from ModalStepOperatorConfig so token_id / token_secret /
    # the both-or-neither validator are shared with the Modal step
    # operator — a stack running both components only needs one set of
    # credentials.

    app_name: str = Field(
        default="zenml-sandbox",
        description="Name of the Modal App that hosts Sessions created by "
        "this component. Looked up (or created) lazily.",
    )
    default_image: str = Field(
        default="python:3.11-slim",
        description="Docker image used when neither the component nor the "
        "per-step settings specify a base_image. Also the fallback when the "
        "'<step>' sentinel is requested but no containerized step image is "
        "available. Example: 'python:3.11-slim'.",
    )

    @property
    def is_remote(self) -> bool:
        """Modal sandboxes run on Modal's infrastructure.

        Returns:
            ``True`` — the ZenML server is not the host.
        """
        return True


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
