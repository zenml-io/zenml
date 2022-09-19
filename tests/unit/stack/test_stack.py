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
from uuid import uuid4

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.container_registries import DefaultContainerRegistryFlavor
from zenml.enums import StackComponentType
from zenml.exceptions import ProvisioningError, StackValidationError
from zenml.orchestrators import LocalOrchestrator
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.stack import Stack


def test_initializing_a_stack_from_components():
    """Tests that a stack can be initialized from a dict of components."""
    orchestrator = LocalOrchestrator(name="")
    artifact_store = LocalArtifactStore(name="", path="")

    components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.ARTIFACT_STORE: artifact_store,
    }

    stack = Stack.from_components(id=uuid4(), name="", components=components)

    assert stack.orchestrator is orchestrator
    assert stack.artifact_store is artifact_store
    assert stack.container_registry is None

    # check that it also works with optional container registry
    container_registry = DefaultContainerRegistryFlavor(name="", uri="")
    components[StackComponentType.CONTAINER_REGISTRY] = container_registry

    stack = Stack.from_components(id=uuid4(), name="", components=components)
    assert stack.container_registry is container_registry


def test_initializing_a_stack_with_missing_components():
    """Tests that initializing a stack with missing components fails."""
    with pytest.raises(TypeError):
        Stack.from_components(name="", components={}).validate()


def test_initializing_a_stack_with_wrong_components():
    """Tests that initializing a stack with wrong component classes fails."""
    orchestrator = LocalOrchestrator(name="")

    # orchestrators for all component types
    components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.ARTIFACT_STORE: orchestrator,
    }

    with pytest.raises(TypeError):
        Stack.from_components(name="", components=components).validate()


def test_stack_returns_all_its_components():
    """Tests that the stack `components` property returns the correct stack
    components."""
    orchestrator = LocalOrchestrator(name="")
    artifact_store = LocalArtifactStore(name="", path="")
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=orchestrator,
        artifact_store=artifact_store,
    )

    expected_components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.ARTIFACT_STORE: artifact_store,
    }
    assert stack.components == expected_components

    # check that it also works with optional container registry
    container_registry = DefaultContainerRegistryFlavor(name="", uri="")
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=orchestrator,
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
    stack_with_mock_components.artifact_store.runtime_options = {
        "key_1": None,
        "key_3": "Not Aria",
    }

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
    stack_with_mock_components.artifact_store.requirements = {
        "another_requirement",
        "aria",
    }

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
    stack_with_mock_components.artifact_store.validator = None

    with pytest.raises(StackValidationError):
        stack_with_mock_components.validate()


def test_stack_validation_succeeds_if_no_component_validator_fails(
    stack_with_mock_components,
):
    """Tests that the stack validation succeeds if one no component validator
    fails."""
    stack_with_mock_components.orchestrator.validator = None
    stack_with_mock_components.artifact_store.validator = None

    with does_not_raise():
        stack_with_mock_components.validate()


def test_stack_prepare_pipeline_run(
    stack_with_mock_components, one_step_pipeline, empty_step
):
    """Tests that the stack prepares a pipeline run by calling the prepare
    methods of all its components."""
    pipeline = one_step_pipeline(empty_step())
    run_name = "some_unique_pipeline_run_name"
    runtime_config = RuntimeConfiguration(run_name=run_name)
    stack_with_mock_components.prepare_pipeline_run(pipeline, runtime_config)
    for component in stack_with_mock_components.components.values():
        component.prepare_pipeline_deployment.assert_called_once()
        component.prepare_pipeline_run.assert_called_once()


def test_stack_deployment(
    stack_with_mock_components, one_step_pipeline, empty_step
):
    """Tests that when a pipeline is deployed on a stack, the stack calls the
    orchestrator to run the pipeline and calls cleanup methods on all of its
    components.
    """
    # Mock the pipeline run registering which tries (and fails) to serialize
    # our mock objects
    pipeline_run_return_value = object()
    stack_with_mock_components.orchestrator.run.return_value = (
        pipeline_run_return_value
    )

    pipeline = one_step_pipeline(empty_step())
    run_name = "some_unique_pipeline_run_name"
    runtime_config = RuntimeConfiguration(run_name=run_name)
    return_value = stack_with_mock_components.deploy_pipeline(
        pipeline=pipeline, runtime_configuration=runtime_config
    )

    for component in stack_with_mock_components.components.values():
        component.cleanup_pipeline_run.assert_called_once()

    stack_with_mock_components.orchestrator.run.assert_called_once_with(
        pipeline,
        stack=stack_with_mock_components,
        runtime_configuration=runtime_config,
    )
    assert return_value is pipeline_run_return_value


def test_stack_provisioning_status(stack_with_mock_components):
    """Tests that the stack `is_provisioned` property only returns True if all
    the components are provisioned."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    assert stack_with_mock_components.is_provisioned is True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_provisioned = False

    assert stack_with_mock_components.is_provisioned is False


def test_stack_running_status(stack_with_mock_components):
    """Tests that the stack `is_running` property only returns True if all
    the components are running."""
    for component in stack_with_mock_components.components.values():
        component.is_running = True

    assert stack_with_mock_components.is_running is True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_running = False

    assert stack_with_mock_components.is_running is False


def test_stack_forwards_provisioning_to_all_unprovisioned_components(
    stack_with_mock_components,
):
    """Tests that stack provisioning calls `component.provision()` on any
    component that isn't provisioned yet."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = False

    stack_with_mock_components.provision()

    for component in stack_with_mock_components.components.values():
        component.provision.assert_called_once()

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_provisioned = True

    stack_with_mock_components.provision()

    # the component with `is_provisioned == True` does not get called again
    any_component.provision.assert_called_once()


def test_stack_provisioning_fails_if_any_component_raises_an_error(
    stack_with_mock_components,
):
    """Tests that stack provisioning fails if an error is raised when calling
    `provision()` on any of the stack components."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = False

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.provision.side_effect = ProvisioningError()

    with pytest.raises(ProvisioningError):
        stack_with_mock_components.provision()

    any_component.provision.side_effect = NotImplementedError()

    with pytest.raises(NotImplementedError):
        stack_with_mock_components.provision()


def test_stack_forwards_deprovisioning_to_all_provisioned_components(
    stack_with_mock_components,
):
    """Tests that stack deprovisioning calls `component.deprovision()` on any
    component that is provisioned."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    stack_with_mock_components.deprovision()

    for component in stack_with_mock_components.components.values():
        component.deprovision.assert_called_once()

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_provisioned = False

    stack_with_mock_components.deprovision()

    # the component with `is_provisioned == False` does not get called again
    any_component.deprovision.assert_called_once()


def test_stack_deprovisioning_fails_if_any_component_raises_an_error(
    stack_with_mock_components,
):
    """Tests that stack deprovisioning fails if an error is raised when calling
    `deprovision()` on any of the stack components."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.deprovision.side_effect = ProvisioningError()

    with pytest.raises(ProvisioningError):
        stack_with_mock_components.deprovision()


def test_stack_deprovisioning_does_not_fail_if_not_implemented_in_any_component(
    stack_with_mock_components,
):
    """Tests that stack deprovisioning does not fail if any component hasn't
    implemented the `deprovision()` method."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.deprovision.side_effect = NotImplementedError()

    with does_not_raise():
        stack_with_mock_components.deprovision()


def test_stack_forwards_resuming_to_all_suspended_components(
    stack_with_mock_components,
):
    """Tests that stack resuming calls `component.resume()` on any
    component that is provisioned and not running."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True
        component.is_running = False

    stack_with_mock_components.resume()

    for component in stack_with_mock_components.components.values():
        component.resume.assert_called_once()

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_running = True

    stack_with_mock_components.resume()

    # the component with `is_running == True` does not get called again
    any_component.resume.assert_called_once()

    # if the component is not provisioned or running, resuming fails
    any_component.is_provisioned = False
    any_component.is_running = False

    with pytest.raises(ProvisioningError):
        stack_with_mock_components.resume()


def test_stack_forwards_suspending_to_all_running_components(
    stack_with_mock_components,
):
    """Tests that stack suspending calls `component.suspend()` on any
    component that is running."""
    for component in stack_with_mock_components.components.values():
        component.is_suspended = False

    stack_with_mock_components.suspend()

    for component in stack_with_mock_components.components.values():
        component.suspend.assert_called_once()

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_suspended = True

    stack_with_mock_components.suspend()

    # the component with `is_running == False` does not get called again
    any_component.suspend.assert_called_once()


def test_stack_suspending_does_not_fail_if_not_implemented_in_any_component(
    stack_with_mock_components,
):
    """Tests that stack suspending does not fail if any component hasn't
    implemented the `suspend()` method."""
    for component in stack_with_mock_components.components.values():
        component.is_running = True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.suspend.side_effect = NotImplementedError()

    with does_not_raise():
        stack_with_mock_components.suspend()
