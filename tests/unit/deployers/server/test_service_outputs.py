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
"""Unit tests for PipelineDeploymentService output mapping with in-memory mode."""

from types import SimpleNamespace
from typing import Generator
from uuid import uuid4

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from zenml.deployers.server import runtime
from zenml.deployers.server.models import BaseDeploymentInvocationRequest
from zenml.deployers.server.service import PipelineDeploymentService


class _DummyParams(BaseModel):
    """Minimal params model to bypass real pipeline loading."""

    city: str = "Berlin"


class _DummySnapshot:
    def __init__(self) -> None:
        self.id = uuid4()
        self.name = "snapshot"
        self.pipeline_configuration = SimpleNamespace(
            name="test-pipeline",
            environment={},
            init_hook_source=None,
            init_hook_kwargs=None,
            cleanup_hook_source=None,
        )
        self.pipeline_spec = SimpleNamespace(
            parameters={},
            input_schema=None,
            output_schema=None,
            outputs=[SimpleNamespace(step_name="step1", output_name="result")],
        )
        self.step_configurations = {}
        self.stack = SimpleNamespace(name="test-stack")


class _DummyDeployment:
    def __init__(self) -> None:
        self.id = uuid4()
        self.name = "test-deployment"
        self.snapshot = _DummySnapshot()


class _DummyRun:
    def __init__(self) -> None:
        self.id = uuid4()
        self.name = "test-run"


@pytest.fixture(autouse=True)
def clean_runtime_state() -> Generator[None, None, None]:
    """Ensure runtime state is reset before and after each test."""

    runtime.stop()
    yield
    runtime.stop()


def _make_service(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> PipelineDeploymentService:
    """Construct a deployment service instance backed by dummy artifacts."""

    deployment = _DummyDeployment()

    class DummyZenStore:
        """Return the snapshot associated with the provided ID."""

        def get_deployment(self, deployment_id: object) -> _DummyDeployment:  # noqa: D401
            return deployment

        def get_snapshot(self, snapshot_id: object) -> _DummySnapshot:  # noqa: D401
            return deployment.snapshot

        def create_snapshot(self, request: object) -> _DummySnapshot:  # noqa: D401
            """Return the snapshot that would be created in the real store."""

            return deployment.snapshot

    class DummyClient:
        """Client stub exposing zen_store and active stack attributes."""

        def __init__(self) -> None:
            self.zen_store = DummyZenStore()
            self.active_stack = mocker.MagicMock()

        def get_pipeline_run(
            self, *args: object, **kwargs: object
        ) -> _DummyRun:  # noqa: D401
            """Return a dummy pipeline run."""

            return _DummyRun()

    monkeypatch.setattr("zenml.deployers.server.service.Client", DummyClient)

    service = PipelineDeploymentService(uuid4())
    service.params_model = _DummyParams
    return service


def test_service_captures_in_memory_outputs(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """Service should capture in-memory outputs before stopping runtime."""

    service = _make_service(monkeypatch, mocker)

    placeholder_run = _DummyRun()
    monkeypatch.setattr(
        "zenml.deployers.server.service.run_utils.create_placeholder_run",
        mocker.MagicMock(return_value=placeholder_run),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.utils.deployment_snapshot_request_from_source_snapshot",
        lambda source_snapshot, deployment_parameters: SimpleNamespace(),
    )

    class _DummyOrchestrator:
        def run(self, snapshot, stack, placeholder_run):  # noqa: D401
            runtime.record_step_outputs("step1", {"result": "fast_value"})

    service._orchestrator = _DummyOrchestrator()

    request = BaseDeploymentInvocationRequest(
        parameters=_DummyParams(),
        use_in_memory=True,
    )

    response = service.execute_pipeline(request)

    assert response.success is True
    assert response.outputs == {"result": "fast_value"}
    assert service.total_executions == 1
