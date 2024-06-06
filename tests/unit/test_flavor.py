#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import Optional, Type

from zenml import __version__ as zenml_version
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator


class AriaOrchestratorConfig(BaseOrchestratorConfig):
    favorite_orchestration_language: str
    favorite_orchestration_language_version: Optional[str] = None


class AriaOrchestratorFlavor(BaseOrchestratorFlavor):
    @property
    def name(self) -> str:
        return "aria"

    @property
    def config_class(self) -> Type[AriaOrchestratorConfig]:
        return AriaOrchestratorConfig

    @property
    def implementation_class(self) -> Type["LocalOrchestrator"]:
        return LocalOrchestrator

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()


def test_sdk_docs_url():
    """Tests that SDK Docs URLs are correct."""
    assert AriaOrchestratorFlavor().sdk_docs_url == (
        f"https://sdkdocs.zenml.io/{zenml_version}/core_code_docs/core-orchestrators/#tests.unit.test_flavor"
    )


def test_docs_url():
    """Tests that Docs URLs are correct."""
    assert AriaOrchestratorFlavor().docs_url == (
        f"https://docs.zenml.io/v/{zenml_version}/stack-components/orchestrators/aria"
    )
