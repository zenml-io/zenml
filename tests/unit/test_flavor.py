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
from datetime import datetime
from typing import Optional, Type
from uuid import uuid4

import pytest

from zenml import __version__ as zenml_version
from zenml.enums import StackComponentType
from zenml.exceptions import CustomFlavorImportError
from zenml.models import (
    FlavorResponse,
    FlavorResponseBody,
    FlavorResponseMetadata,
)
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.stack.flavor import Flavor, validate_flavor_source


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


class MissingImplementationFlavor(BaseOrchestratorFlavor):
    @property
    def name(self) -> str:
        return "missing_implementation"

    @property
    def config_class(self) -> Type[AriaOrchestratorConfig]:
        return AriaOrchestratorConfig

    @property
    def implementation_class(self) -> Type["LocalOrchestrator"]:
        raise ImportError("No module named 'missing_dependency'")


_ZERO_ARG_CALLABLE_WAS_CALLED = False


def _zero_arg_callable() -> AriaOrchestratorFlavor:
    global _ZERO_ARG_CALLABLE_WAS_CALLED
    _ZERO_ARG_CALLABLE_WAS_CALLED = True
    return AriaOrchestratorFlavor()


def _flavor_response(source: str, is_custom: bool = True) -> FlavorResponse:
    now = datetime.utcnow()
    return FlavorResponse(
        id=uuid4(),
        name="aria",
        body=FlavorResponseBody(
            user_id=uuid4(),
            type=StackComponentType.ORCHESTRATOR,
            display_name="Aria",
            integration=None,
            source=source,
            logo_url=None,
            is_custom=is_custom,
            created=now,
            updated=now,
        ),
        metadata=FlavorResponseMetadata(
            config_schema={},
            connector_type=None,
            connector_resource_type=None,
            connector_resource_id_attr=None,
            docs_url=None,
            sdk_docs_url=None,
        ),
        resources=None,
    )


def test_sdk_docs_url():
    """Tests that SDK Docs URLs are correct."""
    assert AriaOrchestratorFlavor().sdk_docs_url == (
        f"https://sdkdocs.zenml.io/{zenml_version}/core_code_docs/core-orchestrators/#tests.unit.test_flavor"
    )


def test_docs_url():
    """Tests that Docs URLs are correct."""
    assert AriaOrchestratorFlavor().docs_url == (
        "https://docs.zenml.io/stack-components/orchestrators/aria"
    )


def test_integration_sdk_docs_url():
    """Tests that integration SDK Docs URLs point to specific config classes."""
    from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
        KubernetesOrchestratorFlavor,
    )

    flavor = KubernetesOrchestratorFlavor()
    expected_url = (
        f"https://sdkdocs.zenml.io/{zenml_version}/integration_code_docs"
        f"/integrations-kubernetes"
        f"#zenml.integrations.kubernetes.flavors.KubernetesOrchestratorConfig"
    )
    assert flavor.sdk_docs_url == expected_url


def test_validate_flavor_source_returns_class_and_instance():
    """Tests that flavor validation returns both the class and an instance."""
    flavor_class, flavor = validate_flavor_source(
        source=f"{__name__}.AriaOrchestratorFlavor",
        component_type=StackComponentType.ORCHESTRATOR,
    )

    assert flavor_class is AriaOrchestratorFlavor
    assert isinstance(flavor, AriaOrchestratorFlavor)


def test_flavor_from_model_does_not_call_non_flavor_source():
    """Tests that flavor hydration rejects callables without invoking them."""
    global _ZERO_ARG_CALLABLE_WAS_CALLED
    _ZERO_ARG_CALLABLE_WAS_CALLED = False

    with pytest.raises(CustomFlavorImportError):
        Flavor.from_model(
            _flavor_response(source=f"{__name__}._zero_arg_callable")
        )

    assert _ZERO_ARG_CALLABLE_WAS_CALLED is False


def test_flavor_from_model_raises_custom_import_error():
    """Tests that custom flavor import errors are raised during validation."""
    with pytest.raises(CustomFlavorImportError):
        Flavor.from_model(
            _flavor_response(source="not_a_real_module.NotARealFlavor")
        )


def test_flavor_from_model_skips_implementation_class_validation():
    """Tests that flavor hydration does not require optional dependencies."""
    flavor = Flavor.from_model(
        _flavor_response(source=f"{__name__}.MissingImplementationFlavor")
    )

    assert isinstance(flavor, MissingImplementationFlavor)


def test_validate_flavor_source_validates_implementation_class_by_default():
    """Tests that explicit flavor source validation still validates classes."""
    with pytest.raises(ValueError, match="missing_dependency"):
        validate_flavor_source(
            source=f"{__name__}.MissingImplementationFlavor",
            component_type=StackComponentType.ORCHESTRATOR,
        )
