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
import os
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.io.utils import get_global_config_directory
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.stack import Stack


def test_default_local_stack():
    """Tests that the default_local_stack method returns a stack with local
    components."""
    stack = Stack.default_local_stack()

    assert isinstance(stack.orchestrator, LocalOrchestrator)
    assert isinstance(stack.metadata_store, SQLiteMetadataStore)
    assert isinstance(stack.artifact_store, LocalArtifactStore)
    assert stack.container_registry is None

    expected_artifact_store_path = os.path.join(
        get_global_config_directory(),
        "local_stores",
        str(stack.artifact_store.uuid),
    )
    expected_metadata_store_uri = os.path.join(
        expected_artifact_store_path, "metadata.db"
    )

    assert stack.artifact_store.path == expected_artifact_store_path
    assert stack.metadata_store.uri == expected_metadata_store_uri


def test_initializing_a_stack_from_components():
    """Tests that a stack can be initialized from a dict of components."""
    orchestrator = LocalOrchestrator(name="")
    metadata_store = SQLiteMetadataStore(name="", uri="")
    artifact_store = LocalArtifactStore(name="", path="")

    components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.METADATA_STORE: metadata_store,
        StackComponentType.ARTIFACT_STORE: artifact_store,
    }

    stack = Stack.from_components(name="", components=components)

    assert stack.orchestrator is orchestrator
    assert stack.metadata_store is metadata_store
    assert stack.artifact_store is artifact_store
    assert stack.container_registry is None

    # check that it also works with optional container registry
    container_registry = BaseContainerRegistry(name="", uri="")
    components[StackComponentType.CONTAINER_REGISTRY] = container_registry

    stack = Stack.from_components(name="", components=components)
    assert stack.container_registry is container_registry


def test_initializing_a_stack_with_missing_components():
    """Tests that initializing a stack with missing components fails."""
    with pytest.raises(TypeError):
        Stack.from_components(name="", components={})


def test_initializing_a_stack_with_wrong_components():
    """Tests that initializing a stack with wrong component classes fails."""
    orchestrator = LocalOrchestrator(name="")

    # orchestrators for all component types
    components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.METADATA_STORE: orchestrator,
        StackComponentType.ARTIFACT_STORE: orchestrator,
    }

    with pytest.raises(TypeError):
        Stack.from_components(name="", components=components)


def test_stack_validates_when_initialized(mocker):
    """Tests that a stack is validated when it's initialized."""
    mocker.patch.object(Stack, "validate")
    Stack.default_local_stack()
    Stack.validate.assert_called_once()


def test_stack_returns_all_its_components():
    """Tests that the stack `components` property returns the correct stack
    components."""
    orchestrator = LocalOrchestrator(name="")
    metadata_store = SQLiteMetadataStore(name="", uri="")
    artifact_store = LocalArtifactStore(name="", path="")
    stack = Stack(
        name="",
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
    )

    expected_components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.METADATA_STORE: metadata_store,
        StackComponentType.ARTIFACT_STORE: artifact_store,
    }
    assert stack.components == expected_components

    # check that it also works with optional container registry
    container_registry = BaseContainerRegistry(name="", uri="")
    stack = Stack(
        name="",
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
        container_registry=container_registry,
    )

    expected_components[
        StackComponentType.CONTAINER_REGISTRY
    ] = container_registry

    assert stack.components == expected_components


def test_stack_runtime_options_combines_runtime_options_of_components(
    stack_with_mock_components,
):
    """Tests that the stack gets the available runtime options of all its
    components and combines them."""
    stack_with_mock_components.orchestrator.runtime_options = {
        "key_1": None,
        "key_2": "Aria",
    }
    stack_with_mock_components.metadata_store.runtime_options = {
        "key_1": None,
        "key_3": "Not Aria",
    }
    stack_with_mock_components.artifact_store.runtime_options = {}

    expected_runtime_options = {
        "key_1": None,
        "key_2": "Aria",
        "key_3": "Not Aria",
    }
    assert (
        stack_with_mock_components.runtime_options == expected_runtime_options
    )


def test_stack_requirements(stack_with_mock_components):
    """Tests that the stack returns the requirements of all its components."""
    stack_with_mock_components.orchestrator.requirements = {"one_requirement"}
    stack_with_mock_components.metadata_store.requirements = {
        "another_requirement",
        "aria",
    }
    stack_with_mock_components.artifact_store.requirements = set()

    assert stack_with_mock_components.requirements() == {
        "one_requirement",
        "another_requirement",
        "aria",
    }


def test_stack_validation_fails_if_a_components_validator_fails(
    stack_with_mock_components, failing_stack_validator
):
    """Tests that the stack validation fails if one of its components validates
    fails to validate the stack."""
    stack_with_mock_components.orchestrator.validator = failing_stack_validator
    stack_with_mock_components.metadata_store.validator = None
    stack_with_mock_components.artifact_store.validator = None

    with pytest.raises(StackValidationError):
        stack_with_mock_components.validate()


def test_stack_validation_succeeds_if_no_component_validator_fails(
    stack_with_mock_components,
):
    """Tests that the stack validation succeeds if one no component validator
    fails."""
    stack_with_mock_components.orchestrator.validator = None
    stack_with_mock_components.metadata_store.validator = None
    stack_with_mock_components.artifact_store.validator = None

    with does_not_raise():
        stack_with_mock_components.validate()


def test_stack_deployment(
    stack_with_mock_components, one_step_pipeline, empty_step
):
    """Tests that when a pipeline is deployed on a stack, the stack calls
    preparation/cleanup methods on all of its components and calls the
    orchestrator to run the pipeline."""
    pipeline_run_return_value = object()
    stack_with_mock_components.orchestrator.run_pipeline.return_value = (
        pipeline_run_return_value
    )

    pipeline = one_step_pipeline(empty_step())
    run_name = "some_unique_pipeline_run_name"
    runtime_config = RuntimeConfiguration(run_name=run_name)
    return_value = stack_with_mock_components.deploy_pipeline(
        pipeline=pipeline, runtime_configuration=runtime_config
    )

    for component in stack_with_mock_components.components.values():
        component.prepare_pipeline_deployment.assert_called_once()
        component.prepare_pipeline_run.assert_called_once()
        component.cleanup_pipeline_run.assert_called_once()

    stack_with_mock_components.orchestrator.run_pipeline.assert_called_once_with(
        pipeline, stack=stack_with_mock_components, run_name=run_name
    )
    assert return_value is pipeline_run_return_value
