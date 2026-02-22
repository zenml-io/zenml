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
"""Daytona sandbox flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.daytona import DAYTONA_SANDBOX_FLAVOR
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.daytona.sandboxes import DaytonaSandbox


class DaytonaSandboxSettings(BaseSandboxSettings):
    """Settings for the Daytona sandbox implementation.

    Attributes:
        api_url: Optional Daytona API endpoint URL.
        target: Optional target where the sandbox should run.
        ephemeral: Whether to create ephemeral sandboxes that are automatically
            deleted when stopped.
        auto_stop_interval_minutes: Optional inactivity window before Daytona
            auto-stops the sandbox.
        auto_delete_interval_minutes: Optional delay after stop before Daytona
            auto-deletes the sandbox.
    """

    api_url: Optional[str] = None
    target: Optional[str] = None
    ephemeral: bool = True
    auto_stop_interval_minutes: Optional[int] = None
    auto_delete_interval_minutes: Optional[int] = None


class DaytonaSandboxConfig(BaseSandboxConfig, DaytonaSandboxSettings):
    """Configuration for the Daytona sandbox component."""

    default_image: str = "python:3.12"
    default_cpu: int = 2
    default_memory_gb: int = 4
    default_disk_gb: int = 8


class DaytonaSandboxFlavor(BaseSandboxFlavor):
    """Daytona sandbox flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DAYTONA_SANDBOX_FLAVOR

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
    def config_class(self) -> Type[DaytonaSandboxConfig]:
        """Returns `DaytonaSandboxConfig` config class.

        Returns:
            The config class.
        """
        return DaytonaSandboxConfig

    @property
    def implementation_class(self) -> Type["DaytonaSandbox"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.daytona.sandboxes import DaytonaSandbox

        return DaytonaSandbox
