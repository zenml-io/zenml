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
"""Monty sandbox flavor."""

from typing import TYPE_CHECKING, Dict, Optional, Type

from zenml.integrations.monty import MONTY_SANDBOX_FLAVOR
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.monty.sandboxes import MontySandbox


class MontySandboxSettings(BaseSandboxSettings):
    """Settings for the Monty sandbox implementation."""

    external_functions: Optional[Dict[str, str]] = None
    type_check_stubs: Optional[str] = None


class MontySandboxConfig(BaseSandboxConfig, MontySandboxSettings):
    """Configuration for the Monty sandbox component."""

    type_check: bool = True
    raise_on_failure: bool = True


class MontySandboxFlavor(BaseSandboxFlavor):
    """Monty sandbox flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MONTY_SANDBOX_FLAVOR

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
    def config_class(self) -> Type[MontySandboxConfig]:
        """Returns `MontySandboxConfig` config class.

        Returns:
            The config class.
        """
        return MontySandboxConfig

    @property
    def implementation_class(self) -> Type["MontySandbox"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.monty.sandboxes import MontySandbox

        return MontySandbox
