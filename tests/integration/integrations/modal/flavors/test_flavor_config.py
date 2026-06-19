#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

import importlib
import importlib.abc
import sys
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.integrations.modal import ModalIntegration
from zenml.integrations.modal.flavors import (
    ModalOrchestratorConfig,
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.flavors.modal_step_operator_flavor import (
    DEFAULT_TIMEOUT_SECONDS,
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.integrations.modal.orchestrators import ModalOrchestrator


def _make_orchestrator(
    config: ModalOrchestratorConfig | None = None,
) -> ModalOrchestrator:
    return ModalOrchestrator(
        name="modal",
        id=uuid4(),
        config=config or ModalOrchestratorConfig(),
        flavor="modal",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _stack_component(
    *,
    name: str,
    component_type: StackComponentType,
    is_local: bool = False,
    local_path: str | None = None,
):
    return SimpleNamespace(
        name=name,
        type=component_type,
        flavor="stub",
        config=SimpleNamespace(is_local=is_local),
        local_path=local_path,
    )


def _stack(
    *,
    artifact_store_local: bool = False,
    container_registry_local: bool = False,
    extra_components=None,
):
    artifact_store = _stack_component(
        name="artifacts",
        component_type=StackComponentType.ARTIFACT_STORE,
        is_local=artifact_store_local,
    )
    container_registry = _stack_component(
        name="registry",
        component_type=StackComponentType.CONTAINER_REGISTRY,
        is_local=container_registry_local,
    )
    image_builder = _stack_component(
        name="builder",
        component_type=StackComponentType.IMAGE_BUILDER,
    )
    components = [artifact_store, container_registry, image_builder]
    if extra_components:
        components.extend(extra_components)

    return SimpleNamespace(
        name="active-stack",
        artifact_store=artifact_store,
        container_registry=container_registry,
        all_components=components,
    )


def test_modal_settings_timeout_accepts_valid_values() -> None:
    # Test minimum valid value
    settings = ModalStepOperatorSettings(timeout=1)
    assert settings.timeout == 1

    # Test maximum valid value
    settings = ModalStepOperatorSettings(timeout=DEFAULT_TIMEOUT_SECONDS)
    assert settings.timeout == DEFAULT_TIMEOUT_SECONDS

    # Test mid-range value
    settings = ModalStepOperatorSettings(timeout=3600)
    assert settings.timeout == 3600


def test_modal_settings_timeout_rejects_below_minimum() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModalStepOperatorSettings(timeout=0)

    assert "greater than or equal to 1" in str(exc_info.value)


def test_modal_settings_timeout_rejects_above_maximum() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModalStepOperatorSettings(timeout=DEFAULT_TIMEOUT_SECONDS + 1)

    assert "less than or equal to" in str(exc_info.value)


def test_modal_settings_timeout_rejects_negative() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModalStepOperatorSettings(timeout=-1)

    assert "greater than or equal to 1" in str(exc_info.value)


def test_modal_config_accepts_missing_or_complete_token_pair() -> None:
    assert ModalStepOperatorConfig().token_id is None

    config = ModalStepOperatorConfig(
        token_id="ak-test",
        token_secret="as-test",
    )
    assert config.token_id == "ak-test"
    assert config.token_secret == "as-test"


def test_modal_config_does_not_expose_workspace_field() -> None:
    assert "workspace" not in ModalStepOperatorConfig.model_fields


def test_modal_config_rejects_partial_token_pair() -> None:
    with pytest.raises(ValidationError) as token_id_error:
        ModalStepOperatorConfig(token_id="ak-test")

    assert "token_id and token_secret must be configured together" in str(
        token_id_error.value
    )

    with pytest.raises(ValidationError) as token_secret_error:
        ModalStepOperatorConfig(token_secret="as-test")

    assert "token_id and token_secret must be configured together" in str(
        token_secret_error.value
    )


def test_modal_orchestrator_settings_timeout_accepts_valid_values() -> None:
    settings = ModalOrchestratorSettings(timeout=3600)
    assert settings.timeout == 3600


def test_modal_orchestrator_settings_timeout_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError) as below_minimum:
        ModalOrchestratorSettings(timeout=0)
    assert "greater than or equal to 1" in str(below_minimum.value)

    with pytest.raises(ValidationError) as above_maximum:
        ModalOrchestratorSettings(timeout=DEFAULT_TIMEOUT_SECONDS + 1)
    assert "less than or equal to" in str(above_maximum.value)


def test_modal_orchestrator_config_accepts_missing_or_complete_token_pair() -> (
    None
):
    assert ModalOrchestratorConfig().token_id is None

    config = ModalOrchestratorConfig(
        token_id="ak-test",
        token_secret="as-test",
    )
    assert config.token_id == "ak-test"
    assert config.token_secret == "as-test"


def test_modal_orchestrator_config_rejects_partial_token_pair() -> None:
    with pytest.raises(ValidationError) as token_id_error:
        ModalOrchestratorConfig(token_id="ak-test")
    assert "token_id and token_secret must be configured together" in str(
        token_id_error.value
    )

    with pytest.raises(ValidationError) as token_secret_error:
        ModalOrchestratorConfig(token_secret="as-test")
    assert "token_id and token_secret must be configured together" in str(
        token_secret_error.value
    )


def test_modal_orchestrator_config_remote_schedulable_and_sync_flags() -> None:
    config = ModalOrchestratorConfig()
    assert config.is_remote is True
    assert config.is_local is False
    assert config.is_schedulable is False
    assert config.is_synchronous is True
    assert config.supports_client_side_caching is False
    assert config.handles_step_retries is False

    async_config = ModalOrchestratorConfig(synchronous=False)
    assert async_config.is_synchronous is False


def test_modal_integration_registers_step_operator_and_orchestrator_flavors() -> (
    None
):
    assert [flavor.__name__ for flavor in ModalIntegration.flavors()] == [
        "ModalStepOperatorFlavor",
        "ModalOrchestratorFlavor",
        "ModalSandboxFlavor",
    ]


def test_modal_orchestrator_validator_accepts_remote_stack() -> None:
    validator = _make_orchestrator().validator
    assert validator is not None
    validator.validate(_stack())


def test_modal_orchestrator_validator_rejects_local_artifact_store() -> None:
    validator = _make_orchestrator().validator
    assert validator is not None

    with pytest.raises(StackValidationError) as exc_info:
        validator.validate(_stack(artifact_store_local=True))

    assert "artifact store `artifacts`" in str(exc_info.value)
    assert "local" in str(exc_info.value)
    assert "Modal orchestrator" in str(exc_info.value)


def test_modal_orchestrator_validator_rejects_local_container_registry() -> (
    None
):
    validator = _make_orchestrator().validator
    assert validator is not None

    with pytest.raises(StackValidationError) as exc_info:
        validator.validate(_stack(container_registry_local=True))

    assert "container registry `registry`" in str(exc_info.value)
    assert "local" in str(exc_info.value)
    assert "Modal orchestrator" in str(exc_info.value)


def test_modal_orchestrator_validator_rejects_local_path_components(
    tmp_path,
) -> None:
    validator = _make_orchestrator().validator
    assert validator is not None
    local_path = tmp_path / "validator"
    local_component = _stack_component(
        name="local-validator",
        component_type=StackComponentType.DATA_VALIDATOR,
        local_path=str(local_path),
    )

    with pytest.raises(StackValidationError) as exc_info:
        validator.validate(_stack(extra_components=[local_component]))

    assert "local-validator" in str(exc_info.value)
    assert str(local_path) in str(exc_info.value)
    assert "cannot access local filesystem paths" in str(exc_info.value)


def test_modal_flavor_imports_do_not_import_modal_sdk() -> None:
    class ModalSdkImportBlocker(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname == "modal" or fullname.startswith("modal."):
                raise AssertionError(
                    "Flavor imports must not import the optional Modal SDK."
                )
            return None

    saved_modal_modules = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "modal" or name.startswith("modal.")
    }
    for name in saved_modal_modules:
        sys.modules.pop(name, None)

    blocker = ModalSdkImportBlocker()
    sys.meta_path.insert(0, blocker)
    try:
        importlib.reload(
            importlib.import_module(
                "zenml.integrations.modal.flavors.modal_step_operator_flavor"
            )
        )
        importlib.reload(
            importlib.import_module(
                "zenml.integrations.modal.flavors.modal_orchestrator_flavor"
            )
        )
        importlib.reload(
            importlib.import_module(
                "zenml.integrations.modal.flavors.modal_sandbox_flavor"
            )
        )
        importlib.reload(
            importlib.import_module("zenml.integrations.modal.flavors")
        )
        assert [flavor.__name__ for flavor in ModalIntegration.flavors()] == [
            "ModalStepOperatorFlavor",
            "ModalOrchestratorFlavor",
            "ModalSandboxFlavor",
        ]
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(saved_modal_modules)
