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

from tests.unit.conftest_new import empty_pipeline  # noqa
from zenml.config import DockerSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.compiler import Compiler
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.enums import StackComponentType
from zenml.exceptions import ProvisioningError, StackValidationError
from zenml.stack import Stack


def test_initializing_a_stack_from_components(
    local_orchestrator, local_artifact_store, local_container_registry
):
    """Tests that a stack can be initialized from a dict of components."""
    components = {
        StackComponentType.ORCHESTRATOR: local_orchestrator,
        StackComponentType.ARTIFACT_STORE: local_artifact_store,
    }

    stack = Stack.from_components(id=uuid4(), name="", components=components)

    assert stack.orchestrator is local_orchestrator
    assert stack.artifact_store is local_artifact_store
    assert stack.container_registry is None

    # check that it also works with optional container registry
    components[StackComponentType.CONTAINER_REGISTRY] = (
        local_container_registry
    )

    stack = Stack.from_components(id=uuid4(), name="", components=components)
    assert stack.container_registry is local_container_registry


def test_initializing_a_stack_with_missing_components():
    """Tests that initializing a stack with missing components fails."""
    with pytest.raises(TypeError):
        Stack.from_components(id=uuid4(), name="", components={}).validate()


def test_initializing_a_stack_with_wrong_components(local_orchestrator):
    """Tests that initializing a stack with wrong component classes fails."""
    # orchestrators for all component types
    components = {
        StackComponentType.ORCHESTRATOR: local_orchestrator,
        StackComponentType.ARTIFACT_STORE: local_orchestrator,
    }

    with pytest.raises(TypeError):
        Stack.from_components(
            id=uuid4(), name="", components=components
        ).validate()


def test_stack_returns_all_its_components(
    local_orchestrator, local_artifact_store, local_container_registry
):
    """Tests that the stack `components` property returns the correct stack components."""
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
    )

    expected_components = {
        StackComponentType.ORCHESTRATOR: local_orchestrator,
        StackComponentType.ARTIFACT_STORE: local_artifact_store,
    }
    assert stack.components == expected_components

    # check that it also works with optional container registry
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
        container_registry=local_container_registry,
    )

    expected_components[StackComponentType.CONTAINER_REGISTRY] = (
        local_container_registry
    )

    assert stack.components == expected_components


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
    """Tests that the stack validation fails if one of its components validates fails to validate the stack."""
    stack_with_mock_components.orchestrator.validator = failing_stack_validator
    stack_with_mock_components.artifact_store.validator = None

    with pytest.raises(StackValidationError):
        stack_with_mock_components.validate()


def test_stack_validation_succeeds_if_no_component_validator_fails(
    stack_with_mock_components,
):
    """Tests that the stack validation succeeds if one no component validator fails."""
    stack_with_mock_components.orchestrator.validator = None
    stack_with_mock_components.artifact_store.validator = None

    with does_not_raise():
        stack_with_mock_components.validate()


def test_stack_prepare_pipeline_deployment(
    stack_with_mock_components, sample_deployment_response_model
):
    """Tests that the stack prepares a pipeline run by calling the prepare methods of all its components."""
    stack_with_mock_components.prepare_pipeline_deployment(
        sample_deployment_response_model
    )
    for component in stack_with_mock_components.components.values():
        component.prepare_pipeline_deployment.assert_called_once()


def test_stack_deployment(
    stack_with_mock_components,
    empty_pipeline,  # noqa: F811
):
    """Tests that when a pipeline is deployed on a stack, the stack calls the
    orchestrator to run the pipeline and calls cleanup methods on all of its
    components."""
    # Mock the pipeline run registering which tries (and fails) to serialize
    # our mock objects

    pipeline_run_return_value = object()
    stack_with_mock_components.orchestrator.run.return_value = (
        pipeline_run_return_value
    )

    with empty_pipeline:
        empty_pipeline.entrypoint()
    deployment = Compiler().compile(
        pipeline=empty_pipeline,
        stack=stack_with_mock_components,
        run_configuration=PipelineRunConfiguration(),
    )
    return_value = stack_with_mock_components.deploy_pipeline(
        deployment=deployment,
    )

    # for component in stack_with_mock_components.components.values():
    #     component.prepare_step_run.assert_called_once()

    stack_with_mock_components.orchestrator.run.assert_called_once_with(
        deployment=deployment,
        stack=stack_with_mock_components,
        placeholder_run=None,
    )
    assert return_value is pipeline_run_return_value


def test_stack_provisioning_status(stack_with_mock_components):
    """Tests that the stack `is_provisioned` property only returns True if all the components are provisioned."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    assert stack_with_mock_components.is_provisioned is True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_provisioned = False

    assert stack_with_mock_components.is_provisioned is False


def test_stack_running_status(stack_with_mock_components):
    """Tests that the stack `is_running` property only returns True if all the components are running."""
    for component in stack_with_mock_components.components.values():
        component.is_running = True

    assert stack_with_mock_components.is_running is True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.is_running = False

    assert stack_with_mock_components.is_running is False


def test_stack_forwards_provisioning_to_all_unprovisioned_components(
    stack_with_mock_components,
):
    """Tests that stack provisioning calls `component.provision()` on any component that isn't provisioned yet."""
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
    """Tests that stack provisioning fails if an error is raised when calling `provision()` on any of the stack components."""
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
    """Tests that stack deprovisioning calls `component.deprovision()` on any component that is provisioned."""
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
    """Tests that stack deprovisioning fails if an error is raised when calling `deprovision()` on any of the stack components."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.deprovision.side_effect = ProvisioningError()

    with pytest.raises(ProvisioningError):
        stack_with_mock_components.deprovision()


def test_stack_deprovisioning_does_not_fail_if_not_implemented_in_any_component(
    stack_with_mock_components,
):
    """Tests that stack deprovisioning does not fail if any component hasn't implemented the `deprovision()` method."""
    for component in stack_with_mock_components.components.values():
        component.is_provisioned = True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.deprovision.side_effect = NotImplementedError()

    with does_not_raise():
        stack_with_mock_components.deprovision()


def test_stack_forwards_resuming_to_all_suspended_components(
    stack_with_mock_components,
):
    """Tests that stack resuming calls `component.resume()` on any component that is provisioned and not running."""
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
    """Tests that stack suspending calls `component.suspend()` on any component that is running."""
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
    """Tests that stack suspending does not fail if any component hasn't implemented the `suspend()` method."""
    for component in stack_with_mock_components.components.values():
        component.is_running = True

    _, any_component = stack_with_mock_components.components.popitem()
    any_component.suspend.side_effect = NotImplementedError()

    with does_not_raise():
        stack_with_mock_components.suspend()


def test_stack_provisioning_fails_if_stack_component_validation_fails(
    stack_with_mock_components, failing_stack_validator
):
    """Tests that stack provisioning fails if the `validate()` method of a stack component is failing."""
    stack_with_mock_components.orchestrator.validator = failing_stack_validator
    stack_with_mock_components.artifact_store.validator = None

    for component in stack_with_mock_components.components.values():
        component.is_provisioned = False

    with pytest.raises(StackValidationError):
        stack_with_mock_components.provision()


def test_requires_remote_server(stack_with_mock_components, mocker):
    """Tests that the stack requires a remote server if either the orchestrator or the step operator are remote."""
    from zenml.step_operators import BaseStepOperator

    step_operator = mocker.Mock(
        spec=BaseStepOperator,
        type=StackComponentType.STEP_OPERATOR,
        flavor="mock",
        name="mock_step_operator",
    )
    stack_with_mock_components._step_operator = step_operator

    stack_with_mock_components.orchestrator.config.is_remote = False
    stack_with_mock_components.step_operator.config.is_remote = False
    assert stack_with_mock_components.requires_remote_server is False

    stack_with_mock_components.orchestrator.config.is_remote = True
    stack_with_mock_components.step_operator.config.is_remote = False
    assert stack_with_mock_components.requires_remote_server is True

    stack_with_mock_components.orchestrator.config.is_remote = False
    stack_with_mock_components.step_operator.config.is_remote = True
    assert stack_with_mock_components.requires_remote_server is True


def test_deployment_server_validation(
    mocker, stack_with_mock_components, sample_deployment_response_model
):
    """Tests that the deployment validation fails when the stack requires a remote server but the store is local."""

    ######### Remote server #########
    mocker.patch(
        "zenml.zen_stores.base_zen_store.BaseZenStore.is_local_store",
        return_value=False,
    )
    mocker.patch(
        "zenml.stack.Stack.requires_remote_server",
        return_value=False,
        new_callable=mocker.PropertyMock,
    )
    with does_not_raise():
        stack_with_mock_components.prepare_pipeline_deployment(
            sample_deployment_response_model
        )

    mocker.patch(
        "zenml.stack.Stack.requires_remote_server",
        return_value=True,
        new_callable=mocker.PropertyMock,
    )
    with does_not_raise():
        stack_with_mock_components.prepare_pipeline_deployment(
            sample_deployment_response_model
        )

    ######### Local server #########
    mocker.patch(
        "zenml.zen_stores.base_zen_store.BaseZenStore.is_local_store",
        return_value=True,
    )

    mocker.patch(
        "zenml.stack.Stack.requires_remote_server",
        return_value=False,
        new_callable=mocker.PropertyMock,
    )
    with does_not_raise():
        stack_with_mock_components.prepare_pipeline_deployment(
            sample_deployment_response_model
        )

    mocker.patch(
        "zenml.stack.Stack.requires_remote_server",
        return_value=True,
        new_callable=mocker.PropertyMock,
    )
    with pytest.raises(RuntimeError):
        stack_with_mock_components.prepare_pipeline_deployment(
            sample_deployment_response_model
        )


def test_get_pipeline_run_metadata(
    mocker, local_orchestrator, local_artifact_store
):
    """Unit test for `Stack.get_pipeline_run_metadata()`."""
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
    )
    orchestrator_metadata = {
        "orchstrator_key": "orchestrator_value",
        "pi": 3.14,
    }
    orchestrator_get_pipeline_run_mock = mocker.patch.object(
        local_orchestrator,
        "get_pipeline_run_metadata",
        return_value=orchestrator_metadata,
    )
    artifact_store_metadata = {"artifact_store_key": 42}
    artifact_store_get_pipeline_run_mock = mocker.patch.object(
        local_artifact_store,
        "get_pipeline_run_metadata",
        return_value=artifact_store_metadata,
    )
    run_metadata = stack.get_pipeline_run_metadata(run_id=uuid4())
    assert len(run_metadata) == 2
    assert run_metadata[local_orchestrator.id] == orchestrator_metadata
    assert run_metadata[local_artifact_store.id] == artifact_store_metadata
    assert orchestrator_get_pipeline_run_mock.call_count == 1
    assert artifact_store_get_pipeline_run_mock.call_count == 1


def test_get_pipeline_run_metadata_never_raises_errors(
    mocker, local_orchestrator, local_artifact_store
):
    """Test that `get_pipeline_run_metadata()` never raises errors."""
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
    )
    orchestrator_get_pipeline_run_mock = mocker.patch.object(
        local_orchestrator,
        "get_pipeline_run_metadata",
        side_effect=Exception("Orchestrator error"),
    )
    artifact_store_get_pipeline_run_mock = mocker.patch.object(
        local_artifact_store,
        "get_pipeline_run_metadata",
        side_effect=Exception("Artifact store error"),
    )
    run_metadata = stack.get_pipeline_run_metadata(run_id=uuid4())
    assert len(run_metadata) == 0
    assert orchestrator_get_pipeline_run_mock.call_count == 1
    assert artifact_store_get_pipeline_run_mock.call_count == 1


def test_get_step_run_metadata(
    mocker, local_orchestrator, local_artifact_store
):
    """Unit test for `Stack.get_step_run_metadata()`."""
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
    )
    orchestrator_metadata = {
        "orchstrator_key": "orchestrator_value",
        "pi": 3.14,
    }
    orchestrator_get_step_run_mock = mocker.patch.object(
        local_orchestrator,
        "get_step_run_metadata",
        return_value=orchestrator_metadata,
    )
    artifact_store_metadata = {"artifact_store_key": 42}
    artifact_store_get_step_run_mock = mocker.patch.object(
        local_artifact_store,
        "get_step_run_metadata",
        return_value=artifact_store_metadata,
    )

    class MockStepInfo:
        config = {}

    mocker.patch.object(
        stack,
        "_get_active_components_for_step",
        return_value={
            StackComponentType.ORCHESTRATOR: local_orchestrator,
            StackComponentType.ARTIFACT_STORE: local_artifact_store,
        },
    )
    run_metadata = stack.get_step_run_metadata(info=MockStepInfo())
    assert len(run_metadata) == 2
    assert run_metadata[local_orchestrator.id] == orchestrator_metadata
    assert run_metadata[local_artifact_store.id] == artifact_store_metadata
    assert orchestrator_get_step_run_mock.call_count == 1
    assert artifact_store_get_step_run_mock.call_count == 1


def test_get_step_run_metadata_never_raises_errors(
    mocker, local_orchestrator, local_artifact_store
):
    """Test that `get_step_run_metadata()` never raises errors."""
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
    )
    orchestrator_get_step_run_mock = mocker.patch.object(
        local_orchestrator,
        "get_step_run_metadata",
        side_effect=Exception("Orchestrator error"),
    )
    artifact_store_get_step_run_mock = mocker.patch.object(
        local_artifact_store,
        "get_step_run_metadata",
        side_effect=Exception("Artifact store error"),
    )

    class MockStepInfo:
        config = {}

    mocker.patch.object(
        stack,
        "_get_active_components_for_step",
        return_value={
            StackComponentType.ORCHESTRATOR: local_orchestrator,
            StackComponentType.ARTIFACT_STORE: local_artifact_store,
        },
    )
    run_metadata = stack.get_step_run_metadata(info=MockStepInfo())
    assert len(run_metadata) == 0
    assert orchestrator_get_step_run_mock.call_count == 1
    assert artifact_store_get_step_run_mock.call_count == 1


def test_docker_builds_collection(
    stack_with_mock_components, sample_deployment_response_model
):
    """Tests that the stack collects the required Docker builds from all its
    components."""
    first_orchestrator_build = BuildConfiguration(
        key="orchestrator", settings=DockerSettings()
    )
    second_orchestrator_build = BuildConfiguration(
        key="orchestrator",
        step_name="step_1",
        settings=DockerSettings(target_repository="custom_repo"),
    )
    artifact_store_build = BuildConfiguration(
        key="artifact_store",
        settings=DockerSettings(
            requirements="artifact_store_requirements.txt"
        ),
    )
    stack_with_mock_components.orchestrator.get_docker_builds.return_value = [
        first_orchestrator_build,
        second_orchestrator_build,
    ]
    stack_with_mock_components.artifact_store.get_docker_builds.return_value = [
        artifact_store_build
    ]

    stack_builds = stack_with_mock_components.get_docker_builds(
        deployment=sample_deployment_response_model
    )

    assert len(stack_builds) == 3
    assert first_orchestrator_build in stack_builds
    assert second_orchestrator_build in stack_builds
    assert artifact_store_build in stack_builds
