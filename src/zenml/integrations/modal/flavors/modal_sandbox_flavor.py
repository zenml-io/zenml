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
"""Modal sandbox flavor."""

from typing import TYPE_CHECKING, List, Optional, Type

from zenml.integrations.modal import MODAL_SANDBOX_FLAVOR
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.modal.sandboxes import ModalSandbox


class ModalSandboxSettings(BaseSandboxSettings):
    """Settings for the Modal sandbox implementation.

    Attributes:
        block_network: Whether to block outbound network access.
        cidr_allowlist: Optional CIDR ranges that remain reachable when
            network blocking is enabled.
        verbose: Whether to show verbose Modal execution output.
    """

    block_network: bool = False
    cidr_allowlist: Optional[List[str]] = None
    verbose: bool = False


class ModalSandboxConfig(BaseSandboxConfig, ModalSandboxSettings):
    """Configuration for the Modal sandbox component."""

    app_name: str = "zenml-sandbox"
    default_image: str = "python:3.11-slim"
    default_timeout_seconds: int = 300
    default_cpu: float = 1.0
    default_memory_mb: int = 2048


class ModalSandboxFlavor(BaseSandboxFlavor):
    """Modal sandbox flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MODAL_SANDBOX_FLAVOR

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
    def config_class(self) -> Type[ModalSandboxConfig]:
        """Returns `ModalSandboxConfig` config class.

        Returns:
            The config class.
        """
        return ModalSandboxConfig

    @property
    def implementation_class(self) -> Type["ModalSandbox"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.modal.sandboxes import ModalSandbox

        return ModalSandbox
