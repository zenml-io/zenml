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
    """Per-step settings for the Modal sandbox.

    Inherits ``gpu`` / ``region`` / ``cloud`` from
    ``ModalStepOperatorSettings`` so the two Modal stack components
    share one source of truth for the Modal-specific provisioning
    knobs. For cpu count, memory, and gpu count use the standard
    ``ResourceSettings`` instead — the sandbox reads them from the
    active step's resource settings and combines them with the gpu
    type via ``get_gpu_values``, the same helper the Modal step
    operator uses.

    See https://modal.com/docs/guide/region-selection for region / cloud
    selection (Enterprise & Team plans). Combinations that aren't available
    surface as Modal API errors at session creation time.
    """


class ModalSandboxConfig(BaseSandboxConfig, ModalSandboxSettings):
    """Configuration for the Modal sandbox component.

    Inherits per-step settings so they can be set as component-level defaults;
    ``ModalSandboxSettings`` overrides them per step.

    Modal credentials (``MODAL_TOKEN_ID`` / ``MODAL_TOKEN_SECRET``)
    are not configured here — the Modal SDK reads them from the
    process environment or ``~/.modal.toml``. Set them via your
    orchestrator's env-injection mechanism (e.g.
    ``DockerSettings(environment={"MODAL_TOKEN_ID": ...})``, a
    Kubernetes secret mounted into the pod, or a local
    ``modal setup``).
    """

    app_name: str = Field(
        default="zenml-sandbox",
        description="Name of the Modal App that hosts Sessions created by "
        "this component. Looked up (or created) lazily.",
    )
    default_image: str = Field(
        default="python:3.11-slim",
        description="Docker image used when neither the component nor the "
        "per-step settings specify a base_image. Fallback for the "
        "STEP_IMAGE sentinel when not in a containerized step.",
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/modal.png"

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
