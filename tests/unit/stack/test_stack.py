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
"""Tests for stack behavior."""

from contextlib import ExitStack as does_not_raise
from typing import List, Type
from uuid import uuid4

import pytest

from tests.unit.conftest_new import empty_pipeline  # noqa
from zenml.config import DockerSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.compiler import Compiler
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack
from zenml.step_operators import BaseStepOperator, BaseStepOperatorFlavor


def test_initializing_a_stack_from_components(
    local_orchestrator, local_artifact_store, local_container_registry
):
    """Tests that a stack can be initialized from a dict of components."""
    components = {
        StackComponentType.ORCHESTRATOR: [local_orchestrator],
        StackComponentType.ARTIFACT_STORE: [local_artifact_store],
    }

    stack = Stack.from_components_v2(
        id=uuid4(), name="", components=components
    )

    assert stack.orchestrator is local_orchestrator
    assert stack.artifact_store is local_artifact_store
    assert stack.container_registry is None

    # check that it also works with optional container registry
    components[StackComponentType.CONTAINER_REGISTRY] = [
        local_container_registry
    ]

    stack = Stack.from_components_v2(
        id=uuid4(), name="", components=components
    )
    assert stack.container_registry is local_container_registry


def test_initializing_a_stack_with_missing_components():
    """Tests that initializing a stack with missing components fails."""
    with pytest.raises(TypeError):
        Stack.from_components_v2(id=uuid4(), name="", components={}).validate()


def test_initializing_a_stack_with_wrong_components(local_orchestrator):
    """Tests that initializing a stack with wrong component classes fails."""
    # orchestrators for all component types
    components = {
        StackComponentType.ORCHESTRATOR: local_orchestrator,
        StackComponentType.ARTIFACT_STORE: local_orchestrator,
    }

    with pytest.raises(TypeError):
        Stack.from_components_v2(
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
        StackComponentType.ORCHESTRATOR: [local_orchestrator],
        StackComponentType.ARTIFACT_STORE: [local_artifact_store],
    }
    assert all(
        stack._components[component_type] == component
        for component_type, component in expected_components.items()
    )

    # check that it also works with optional container registry
    stack = Stack(
        id=uuid4(),
        name="",
        orchestrator=local_orchestrator,
        artifact_store=local_artifact_store,
        container_registry=local_container_registry,
    )

    expected_components[StackComponentType.CONTAINER_REGISTRY] = [
        local_container_registry
    ]

    assert all(
        stack._components[component_type] == component
        for component_type, component in expected_components.items()
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


def test_stack_submission(
    stack_with_mock_components,
    empty_pipeline,  # noqa: F811
):
    """Tests that stack submission delegates to the orchestrator.

    When a pipeline is deployed on a stack, the stack calls the
    orchestrator to run the pipeline and calls cleanup methods on all of its
    components.
    """
    # Mock the pipeline run registering which tries (and fails) to serialize
    # our mock objects
    empty_pipeline.prepare()
    snapshot = Compiler().compile(
        pipeline=empty_pipeline,
        stack=stack_with_mock_components,
        run_configuration=PipelineRunConfiguration(),
    )
    stack_with_mock_components.submit_pipeline(
        snapshot=snapshot,
    )

    stack_with_mock_components.orchestrator.run.assert_called_once_with(
        snapshot=snapshot,
        stack=stack_with_mock_components,
        placeholder_run=None,
    )


def test_requires_remote_server(stack_with_mock_components, mocker):
    """Tests that the stack requires a remote server if either the orchestrator or the step operator are remote."""
    from zenml.step_operators import BaseStepOperator

    step_operator = mocker.Mock(
        spec=BaseStepOperator,
        type=StackComponentType.STEP_OPERATOR,
        flavor="mock",
    )
    step_operator.name = "mock_step_operator"
    step_operator.config.is_remote = False
    stack_with_mock_components._components[
        StackComponentType.STEP_OPERATOR
    ] = [step_operator]

    stack_with_mock_components.orchestrator.config.is_remote = False
    stack_with_mock_components.step_operator.config.is_remote = False
    assert stack_with_mock_components.requires_remote_server is False

    stack_with_mock_components.orchestrator.config.is_remote = True
    stack_with_mock_components.step_operator.config.is_remote = False
    assert stack_with_mock_components.requires_remote_server is True

    stack_with_mock_components.orchestrator.config.is_remote = False
    stack_with_mock_components.step_operator.config.is_remote = True
    assert stack_with_mock_components.requires_remote_server is True


def test_submission_server_validation(
    mocker, stack_with_mock_components, sample_snapshot_response_model
):
    """Tests that the submission validation fails when the stack requires a remote server but the store is local."""
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
        stack_with_mock_components.prepare_pipeline_submission(
            sample_snapshot_response_model
        )

    mocker.patch(
        "zenml.stack.Stack.requires_remote_server",
        return_value=True,
        new_callable=mocker.PropertyMock,
    )
    with does_not_raise():
        stack_with_mock_components.prepare_pipeline_submission(
            sample_snapshot_response_model
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
        stack_with_mock_components.prepare_pipeline_submission(
            sample_snapshot_response_model
        )

    mocker.patch(
        "zenml.stack.Stack.requires_remote_server",
        return_value=True,
        new_callable=mocker.PropertyMock,
    )
    with pytest.raises(RuntimeError):
        stack_with_mock_components.prepare_pipeline_submission(
            sample_snapshot_response_model
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
        return_value=[local_orchestrator, local_artifact_store],
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
        return_value=[local_orchestrator, local_artifact_store],
    )
    run_metadata = stack.get_step_run_metadata(info=MockStepInfo())
    assert len(run_metadata) == 0
    assert orchestrator_get_step_run_mock.call_count == 1
    assert artifact_store_get_step_run_mock.call_count == 1


def test_docker_builds_collection(
    stack_with_mock_components, sample_snapshot_response_model
):
    """Tests that the stack collects the required Docker builds.

    The stack collects builds from all its components.
    """
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
        snapshot=sample_snapshot_response_model
    )

    assert len(stack_builds) == 3
    assert first_orchestrator_build in stack_builds
    assert second_orchestrator_build in stack_builds
    assert artifact_store_build in stack_builds


class _StubStepOperatorFlavor(BaseStepOperatorFlavor):
    @property
    def name(self) -> str:
        return "stub_step_operator"

    @property
    def implementation_class(self) -> Type[BaseStepOperator]:
        return BaseStepOperator


def test_stack_from_model_uses_stored_default_step_operator(clean_client):
    """Tests that the runtime stack uses the stored default, not the oldest."""
    clean_client.zen_store.create_flavor(_StubStepOperatorFlavor().to_model())
    for name in ("first", "second"):
        clean_client.create_stack_component(
            name=name,
            flavor="stub_step_operator",
            component_type=StackComponentType.STEP_OPERATOR,
            configuration={},
        )

    def _create_stack(name: str, step_operators: List[str]) -> None:
        clean_client.create_stack(
            name=name,
            components={
                StackComponentType.ORCHESTRATOR: "default",
                StackComponentType.ARTIFACT_STORE: "default",
                StackComponentType.STEP_OPERATOR: step_operators,
            },
        )

    _create_stack("first_default", ["first", "second"])
    _create_stack("second_default", ["first"])
    clean_client.update_stack(
        "second_default",
        component_updates={
            StackComponentType.STEP_OPERATOR: ["second", "first"]
        },
    )

    for stack_name, expected_default in [
        ("first_default", "first"),
        ("second_default", "second"),
    ]:
        stack_model = clean_client.get_stack(stack_name, hydrate=False)
        stack = Stack.from_model(stack_model)
        assert stack.step_operator.name == expected_default
