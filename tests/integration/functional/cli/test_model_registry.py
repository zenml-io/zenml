#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Any, ClassVar, Dict, List, Optional, Type
from uuid import uuid4

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.enums import StackComponentType
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    BaseModelRegistryFlavor,
    ModelRegistryModelMetadata,
    ModelVersionStage,
    RegisteredModel,
    RegistryModelVersion,
)


class ConcreteModelDeployerFlavor(BaseModelRegistryFlavor):
    """Concrete subclass of BaseModelRegistryFlavor that mocks the registered models method"""

    @property
    def name(self) -> str:
        return "local"

    @property
    def implementation_class(self) -> Type["ConcreteModelRegistry"]:
        return ConcreteModelRegistry


class ConcreteModelRegistry(BaseModelRegistry):
    """Concrete subclass of BaseModelDeployer that mocks the deploy_model method"""

    NAME: ClassVar[str] = "TestModelRegistry"
    FLAVOR: ClassVar[Type["BaseModelRegistryFlavor"]] = BaseModelRegistryFlavor

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        pass

    def delete_model(
        self,
        name: str,
    ) -> None:
        pass

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
    ) -> RegisteredModel:
        pass

    def get_model(self, name: str) -> RegisteredModel:
        pass

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        pass

    def register_model_version(
        self,
        name: str,
        version: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        **kwargs: Any,
    ) -> RegistryModelVersion:
        pass

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        pass

    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        remove_metadata: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> RegistryModelVersion:
        pass

    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        stage: Optional[ModelVersionStage] = None,
        count: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        order_by_date: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[List[RegistryModelVersion]]:
        pass

    def get_model_version(
        self, name: str, version: str
    ) -> RegistryModelVersion:
        pass

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        pass

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        pass


@pytest.fixture
def concrete_registered_models(mocker):
    registered_model = mocker.MagicMock(spec=RegisteredModel)
    registered_model.name = "test_model"
    registered_model.description = "test_model_description"
    registered_model.metadata = {"test": "test"}
    return [registered_model]


@pytest.fixture
def concrete_registered_model_version(mocker, concrete_registered_models):
    registered_model_version = mocker.MagicMock(spec=RegistryModelVersion)
    registered_model_version.registered_model = concrete_registered_models[0]
    registered_model_version.version = "test_version"
    registered_model_version.description = "test_version_description"
    registered_model_version.model_source_uri = "test_uri"
    registered_model_version.model_format = "test_format"
    registered_model_version.metadata = ModelRegistryModelMetadata(test="test")
    registered_model_version.stage = ModelVersionStage.NONE
    registered_model_version.created_at = datetime.now()
    registered_model_version.last_updated_at = datetime.now()
    return [registered_model_version]


@pytest.fixture
def concrete_model_registry():
    """Returns a test model registry."""
    return ConcreteModelRegistry(
        name="arias_registry",
        id=uuid4(),
        flavor="test",
        config={},
        type=StackComponentType.MODEL_REGISTRY,
        user=uuid4(),
        project=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_list_models(
    mocker,
    concrete_registered_models,
    concrete_model_registry,
):
    # Get the list command
    runner = CliRunner()
    list_registered_models = (
        cli.commands["model-registry"].commands["models"].commands["list"]
    )

    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelRegistry,
        "list_models",
        return_value=concrete_registered_models,
    )
    # Run the command
    result = runner.invoke(list_registered_models, obj=concrete_model_registry)

    # Check the result
    assert result.exit_code == 0
    assert "test_model" in result.output


def test_update_model(
    mocker,
    concrete_registered_models,
    concrete_model_registry,
):
    # Get the list command
    runner = CliRunner()
    update_registered_model = (
        cli.commands["model-registry"].commands["models"].commands["update"]
    )

    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelRegistry,
        "update_model",
        return_value=concrete_registered_models[0],
    )
    # Run the command
    result = runner.invoke(
        update_registered_model,
        ["test_model", "--description", "new_test_description"],
        obj=concrete_model_registry,
    )

    # Check the result
    assert result.exit_code == 0
    assert "updated successfully." in result.output


def test_get_model(
    mocker,
    concrete_registered_models,
    concrete_model_registry,
):
    # Get the list command
    runner = CliRunner()
    list_registered_model = (
        cli.commands["model-registry"].commands["models"].commands["get"]
    )

    # Patch the find_model_server method\
    model_name = "test_model"
    mocker.patch.object(
        ConcreteModelRegistry,
        "get_model",
        return_value=concrete_registered_models[0],
    )
    # Run the command
    result = runner.invoke(
        list_registered_model, [model_name], obj=concrete_model_registry
    )

    # Check the result
    assert result.exit_code == 0
    assert model_name in result.output

    # Patch the find_model_server method
    model_name = "test_model_not_exist"
    mocker.patch.object(
        ConcreteModelRegistry,
        "get_model",
        side_effect=KeyError("Model with name `{model_name}` does not exist."),
    )

    # Run the command
    result = runner.invoke(
        list_registered_model, [model_name], obj=concrete_model_registry
    )
    # Check the result
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_list_model_versions(
    mocker,
    concrete_registered_model_version,
    concrete_model_registry,
):
    # Get the list command
    runner = CliRunner()
    list_model_versions = (
        cli.commands["model-registry"]
        .commands["models"]
        .commands["list-versions"]
    )

    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelRegistry,
        "list_model_versions",
        return_value=concrete_registered_model_version,
    )
    # Run the command
    result = runner.invoke(
        list_model_versions, ["test_model"], obj=concrete_model_registry
    )

    # Check the result
    assert result.exit_code == 0
    assert "test_version" in result.output
    assert "test_version_description" in result.output


def test_get_model_version(
    mocker,
    concrete_registered_model_version,
    concrete_model_registry,
):
    # Get the list command
    runner = CliRunner()
    get_model_version = (
        cli.commands["model-registry"]
        .commands["models"]
        .commands["get-version"]
    )

    # Patch the find_model_server method
    model_name = "test_model"
    model_version = "test_version"
    mocker.patch.object(
        ConcreteModelRegistry,
        "get_model_version",
        return_value=concrete_registered_model_version[0],
    )

    # Run the command
    result = runner.invoke(
        get_model_version,
        [model_name, "--version", model_version],
        obj=concrete_model_registry,
    )
    # Check the result
    assert result.exit_code == 0
    assert model_version in result.output

    mocker.patch.object(
        ConcreteModelRegistry,
        "get_model_version",
        side_effect=KeyError(
            f"Model with name {model_name} and version {model_version} does not exist."
        ),
    )

    # Run the command
    result = runner.invoke(
        get_model_version,
        [model_name, "--version", model_version],
        obj=concrete_model_registry,
    )

    # Check the result
    assert result.exit_code == 1
    assert "Error:" in result.output
