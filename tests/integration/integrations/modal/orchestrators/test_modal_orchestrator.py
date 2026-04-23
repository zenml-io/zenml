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

from unittest.mock import MagicMock

import pytest

from zenml.enums import ExecutionMode, StackComponentType
from zenml.integrations.modal.flavors import (
    ModalOrchestratorConfig,
    ModalOrchestratorFlavor,
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.orchestrators.modal_orchestrator import (
    ModalOrchestrator,
)


def test_flavor_metadata():
    """The orchestrator flavor surfaces the expected name/type pair."""
    flavor = ModalOrchestratorFlavor()
    assert flavor.name == "modal"
    assert flavor.type == StackComponentType.ORCHESTRATOR
    assert flavor.config_class is ModalOrchestratorConfig
    assert flavor.implementation_class.__name__ == "ModalOrchestrator"


def test_config_is_remote_and_synchronous_delegates():
    """Config flags should follow the declared Modal semantics."""
    default_config = ModalOrchestratorConfig()
    assert default_config.is_remote is True
    assert default_config.is_synchronous is True

    async_config = ModalOrchestratorConfig(synchronous=False)
    assert async_config.is_remote is True
    assert async_config.is_synchronous is False


def test_settings_defaults_are_cpu_only():
    """Default settings should not request any accelerator or cloud region."""
    settings = ModalOrchestratorSettings()
    assert settings.gpu is None
    assert settings.region is None
    assert settings.cloud is None
    assert settings.synchronous is True


@pytest.mark.parametrize(
    "artifact_local, registry_local, expected_ok, expected_fragment",
    [
        (True, False, False, "artifact store"),
        (False, True, False, "container registry"),
        (False, False, True, ""),
    ],
)
def test_validator_rejects_local_components(
    artifact_local, registry_local, expected_ok, expected_fragment
):
    """Validator should refuse stacks with local artifact store or registry."""
    stack = MagicMock()
    stack.artifact_store.config.is_local = artifact_local
    stack.artifact_store.name = "test-artifact-store"
    stack.container_registry.config.is_local = registry_local
    stack.container_registry.name = "test-container-registry"

    orchestrator = ModalOrchestrator.__new__(ModalOrchestrator)
    orchestrator._config = ModalOrchestratorConfig()
    validator = orchestrator.validator
    assert validator is not None
    ok, msg = validator._custom_validation_function(stack)
    assert ok is expected_ok
    if not expected_ok:
        assert expected_fragment in msg


def test_supported_execution_modes_cover_failure_policies():
    """Modal orchestrator should surface all three per-step failure modes."""
    orchestrator = ModalOrchestrator.__new__(ModalOrchestrator)
    orchestrator._config = ModalOrchestratorConfig()
    modes = orchestrator.supported_execution_modes
    assert ExecutionMode.FAIL_FAST in modes
    assert ExecutionMode.STOP_ON_FAILURE in modes
    assert ExecutionMode.CONTINUE_ON_FAILURE in modes
