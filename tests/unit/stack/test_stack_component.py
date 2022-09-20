#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import json
from contextlib import ExitStack as does_not_raise
from typing import Iterator
from uuid import uuid4

import pytest
from pydantic import ValidationError, validator

from zenml.enums import StackComponentType
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestrator,
    BaseOrchestratorConfig,
)
from zenml.repository import Repository
from zenml.stack.flavor_registry import FlavorModel, flavor_registry


def test_stack_component_default_method_implementations(stub_component):
    """Tests the return values for default implementations of some
    StackComponent methods."""
    assert stub_component.validator is None
    assert stub_component.log_file is None
    assert stub_component.runtime_options == {}
    assert stub_component.requirements == set()

    assert stub_component.is_provisioned is True
    assert stub_component.is_running is True

    with pytest.raises(NotImplementedError):
        stub_component.provision()

    with pytest.raises(NotImplementedError):
        stub_component.deprovision()

    with pytest.raises(NotImplementedError):
        stub_component.resume()

    with pytest.raises(NotImplementedError):
        stub_component.suspend()


def test_stack_component_dict_only_contains_public_attributes(
    stub_component_config,
):
    """Tests that the `dict()` method which is used to serialize stack
    components does not include private attributes."""
    assert stub_component_config._some_private_attribute_name == "Also Aria"

    expected_dict_keys = {"some_public_attribute_name", "name", "uuid"}
    assert stub_component_config.dict().keys() == expected_dict_keys


def test_stack_component_public_attributes_are_immutable(stub_component_config):
    """Tests that stack component public attributes are immutable but private
    attribute can be modified."""
    with pytest.raises(TypeError):
        stub_component_config.some_public_attribute_name = "Not Aria"

    with does_not_raise():
        stub_component_config._some_private_attribute_name = "Woof"


def test_stack_component_prevents_extra_attributes(stub_component_config):
    """Tests that passing extra attributes to a StackComponent fails."""
    component_class = stub_component_config.__class__

    with does_not_raise():
        component_class(some_public_attribute_name="test")

    with pytest.raises(ValidationError):
        component_class(not_an_attribute_name="test")


class StubOrchestratorConfig(BaseOrchestratorConfig):
    attribute_without_validator: str = ""
    attribute_with_validator: str = ""

    @validator("attribute_with_validator")
    def _ensure_something(cls, value):
        return value


class StubOrchestrator(BaseOrchestrator):
    @property
    def config(self) -> StubOrchestratorConfig:
        return self._config

    def prepare_or_run_pipeline(self, **kwargs):
        pass


def _get_stub_orchestrator(name, **kwargs):
    return StubOrchestrator(
        name=name,
        id=uuid4(),
        config=StubOrchestratorConfig(**kwargs),
        flavor="TEST",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        project=uuid4(),
    )


@pytest.fixture
def register_stub_orchestrator_flavor() -> Iterator[FlavorModel]:
    """Create the stub orchestrator flavor temporarily."""
    flavor = FlavorModel(
        name="TEST",
        type=StackComponentType.ORCHESTRATOR,
        source=f"{StubOrchestrator.__module__}.{StubOrchestrator.__name__}",
        integration="built-in",
        config_schema="",
        project=uuid4(),
        user=uuid4(),
    )

    flavor_registry._register_flavor(flavor)
    yield None
    flavor_registry._flavors[flavor.type].pop(flavor.name)


def test_stack_component_prevents_secret_references_for_some_attributes():
    """Tests that the stack component prevents secret references for the name
    attribute and all attributes with associated pydantic validators."""
    with pytest.raises(ValueError):
        # Can't have a secret reference for the name
        _get_stub_orchestrator(name="{{secret.key}}")

    with pytest.raises(ValueError):
        # Can't have a secret reference for an attribute that requires
        # pydantic validation
        _get_stub_orchestrator(
            name="test", attribute_with_validator="{{secret.key}}"
        )

    with does_not_raise():
        _get_stub_orchestrator(
            name="test", attribute_without_validator="{{secret.key}}"
        )


def test_stack_component_secret_reference_resolving(
    clean_repo: Repository, register_stub_orchestrator_flavor
):
    """Tests that the stack component resolves secrets if possible."""
    component = _get_stub_orchestrator(
        name="", attribute_without_validator="{{secret.key}}"
    )
    with pytest.raises(RuntimeError):
        # not part of the active stack
        _ = component.config.attribute_without_validator

    stack = clean_repo.active_stack
    stack._orchestrator = component

    clean_repo.update_stack(stack=stack.to_model(user=uuid4(), project=uuid4()))

    with pytest.raises(RuntimeError):
        # no secret manager in stack
        _ = component.config.attribute_without_validator

    from zenml.secrets_managers import LocalSecretsManager

    secrets_manager = LocalSecretsManager(name="")
    stack._secrets_manager = secrets_manager
    clean_repo.update_stack(stack=stack.to_model(user=uuid4(), project=uuid4()))

    with pytest.raises(KeyError):
        # secret doesn't exist
        _ = component.config.attribute_without_validator

    from zenml.secret import ArbitrarySecretSchema

    secret_without_correct_key = ArbitrarySecretSchema(
        name="secret", wrong_key="value"
    )
    secrets_manager.register_secret(secret_without_correct_key)

    with pytest.raises(KeyError):
        # key doesn't exist
        _ = component.config.attribute_without_validator

    secret_with_correct_key = ArbitrarySecretSchema(name="secret", key="value")
    secrets_manager.update_secret(secret_with_correct_key)

    with does_not_raise():
        assert component.config.attribute_without_validator == "value"


def test_stack_component_serialization_does_not_resolve_secrets():
    """Tests that all the serialization methods of a stack component don't
    resolve secret references."""
    secret_ref = "{{name.key}}"
    component = _get_stub_orchestrator(
        name="", attribute_without_validator=secret_ref
    )
    assert component.config.dict()["attribute_without_validator"] == secret_ref
    assert dict(component.config)["attribute_without_validator"] == secret_ref
    assert (
        json.loads(component.config.json())["attribute_without_validator"]
        == secret_ref
    )
