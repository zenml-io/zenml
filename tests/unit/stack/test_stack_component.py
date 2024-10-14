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
from contextlib import ExitStack as does_not_raise
from typing import Dict, Generator, List, Mapping, Optional, Sequence, Type
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError, field_validator

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.models import ComponentRequest
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestrator,
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.stack import StackComponentConfig


def test_stack_component_default_method_implementations(stub_component):
    """Tests the return values for default implementations of some StackComponent methods."""
    assert stub_component.validator is None
    assert stub_component.log_file is None
    assert stub_component.settings_class is None
    assert stub_component.requirements == set()


def test_stack_component_dict_only_contains_public_attributes(
    stub_component_config,
):
    """Tests that the `dict()` method which is used to serialize stack components does not include private attributes."""
    assert stub_component_config._some_private_attribute_name == "Also Aria"

    expected_dict_keys = {"some_public_attribute_name"}
    assert set(stub_component_config.model_dump().keys()) == expected_dict_keys


def test_stack_component_public_attributes_are_immutable(
    stub_component_config,
):
    """Tests that stack component public attributes are immutable but private attribute can be modified."""
    with pytest.raises(ValidationError):
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

    @field_validator("attribute_with_validator")
    @classmethod
    def _ensure_something(cls, value):
        return value


class StubOrchestrator(BaseOrchestrator):
    @property
    def config(self) -> StubOrchestratorConfig:
        return self._config

    def prepare_or_run_pipeline(self, **kwargs):
        pass

    def get_orchestrator_run_id(self) -> str:
        return "some_run_id"


class StubOrchestratorFlavor(BaseOrchestratorFlavor):
    @property
    def name(self) -> str:
        return "TEST"

    @property
    def config_class(self) -> Type[StubOrchestratorConfig]:
        return StubOrchestratorConfig

    @property
    def implementation_class(self) -> Type[StubOrchestrator]:
        return StubOrchestrator


def _get_stub_orchestrator(name, repo=None, **kwargs) -> ComponentRequest:
    return ComponentRequest(
        name=name,
        configuration=StubOrchestratorConfig(**kwargs),
        flavor="TEST",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4() if repo is None else repo.active_user.id,
        workspace=uuid4() if repo is None else repo.active_workspace.id,
    )


@pytest.fixture
def client_with_stub_orchestrator_flavor(
    clean_client,
) -> Generator[Client, None, None]:
    """Create the stub orchestrator flavor temporarily."""
    flavor = StubOrchestratorFlavor()

    clean_client.zen_store.create_flavor(flavor.to_model())
    yield clean_client


def test_stack_component_prevents_secret_references_for_some_attributes(
    client_with_stub_orchestrator_flavor,
):
    """Tests that the stack component prevents secret references for the name attribute and all attributes with associated pydantic validators."""
    with pytest.raises(ValueError):
        # Can't have a secret reference for the name
        _get_stub_orchestrator(name="{{secret.key}}")

    with pytest.raises(ValueError):
        # Can't have a secret reference for an attribute that requires
        # pydantic validation
        client_with_stub_orchestrator_flavor.create_stack_component(
            name="test",
            configuration={"attribute_with_validator": "{{secret.key}}"},
            flavor="TEST",
            component_type=StackComponentType.ORCHESTRATOR,
        )

    with does_not_raise():
        client_with_stub_orchestrator_flavor.create_stack_component(
            name="test",
            configuration={"attribute_without_validator": "{{secret.key}}"},
            flavor="TEST",
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_stack_component_secret_reference_resolving(
    client_with_stub_orchestrator_flavor: Client,
):
    """Tests that the stack component resolves secrets if possible."""
    from zenml.artifact_stores import LocalArtifactStoreConfig

    new_artifact_store = (
        client_with_stub_orchestrator_flavor.create_stack_component(
            name="local",
            configuration=LocalArtifactStoreConfig().model_dump(),
            flavor="local",
            component_type=StackComponentType.ARTIFACT_STORE,
        )
    )
    new_orchestrator = (
        client_with_stub_orchestrator_flavor.create_stack_component(
            name="stub_orchestrator",
            component_type=StackComponentType.ORCHESTRATOR,
            configuration=StubOrchestratorConfig(
                attribute_without_validator="{{secret.key}}"
            ).model_dump(),
            flavor="TEST",
        )
    )

    client_with_stub_orchestrator_flavor.create_stack(
        name="new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: new_artifact_store.name,
            StackComponentType.ORCHESTRATOR: new_orchestrator.name,
        },
    )

    with pytest.raises(KeyError):
        # secret doesn't exist
        o = StubOrchestrator.from_model(new_orchestrator)
        _ = o.config.attribute_without_validator

    client_with_stub_orchestrator_flavor.create_secret(
        "secret", values=dict(wrong_key="value")
    )

    with pytest.raises(KeyError):
        # key doesn't exist
        o = StubOrchestrator.from_model(new_orchestrator)
        _ = o.config.attribute_without_validator

    client_with_stub_orchestrator_flavor.update_secret(
        "secret", add_or_update_values=dict(key="value")
    )

    with does_not_raise():
        o = StubOrchestrator.from_model(new_orchestrator)
        assert o.config.attribute_without_validator == "value"


def test_stack_component_serialization_does_not_resolve_secrets(
    client_with_stub_orchestrator_flavor,
):
    """Tests that all the serialization methods of a stack component don't resolve secret references."""
    secret_ref = "{{name.key}}"

    new_orchestrator = (
        client_with_stub_orchestrator_flavor.create_stack_component(
            name="stub_orchestrator",
            component_type=StackComponentType.ORCHESTRATOR,
            configuration=StubOrchestratorConfig(
                attribute_without_validator=secret_ref,
            ).model_dump(),
            flavor="TEST",
        )
    )
    assert (
        new_orchestrator.configuration["attribute_without_validator"]
        == secret_ref
    )


def test_stack_component_config_converts_json_strings():
    """Tests that the stack component config converts json strings if a string
    is passed for certain fields."""

    class PydanticModel(BaseModel):
        value: int

    class ComponentConfig(StackComponentConfig):
        list_: List[str]
        optional_list: Optional[List[str]] = None
        sequence_: Sequence[str]
        dict_: Dict[str, int]
        mapping_: Mapping[str, int]
        pydantic_model: PydanticModel
        optional_model: Optional[PydanticModel] = None

    config = ComponentConfig(
        list_=["item"],
        optional_list=["item"],
        sequence_=["item"],
        dict_={"key": 1},
        mapping_={"key": 1},
        pydantic_model=PydanticModel(value=1),
        optional_model=PydanticModel(value=1),
    )
    assert config.list_ == ["item"]
    assert config.optional_list == ["item"]
    assert config.sequence_ == ["item"]
    assert config.dict_ == {"key": 1}
    assert config.mapping_ == {"key": 1}
    assert config.pydantic_model == PydanticModel(value=1)
    assert config.optional_model == PydanticModel(value=1)

    config = ComponentConfig(
        list_='["item"]',
        optional_list='["item"]',
        sequence_='["item"]',
        dict_='{"key": 1}',
        mapping_='{"key": 1}',
        pydantic_model='{"value": 1}',
        optional_model='{"value": 1}',
    )
    assert config.list_ == ["item"]
    assert config.optional_list == ["item"]
    assert config.sequence_ == ["item"]
    assert config.dict_ == {"key": 1}
    assert config.mapping_ == {"key": 1}
    assert config.pydantic_model == PydanticModel(value=1)
    assert config.optional_model == PydanticModel(value=1)
