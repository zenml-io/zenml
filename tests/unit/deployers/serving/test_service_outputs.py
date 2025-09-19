"""Unit tests for PipelineDeploymentService output mapping with in-memory mode."""

from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

import pytest
from pydantic import BaseModel

from zenml.deployers.server import runtime
from zenml.deployers.server.service import PipelineDeploymentService


class _DummyParams(BaseModel):
    """Minimal params model to bypass real pipeline loading."""

    # Accept no fields; service will validate and return {}
    pass


class _DummyPipelineConfig(BaseModel):
    name: str = "test-pipeline"


class _DummySnapshot:
    def __init__(self) -> None:
        self.id = uuid4()
        self.pipeline_configuration = _DummyPipelineConfig()
        self.step_configurations = {}
        self.stack = type("S", (), {"name": "test-stack"})()


class _DummyRun:
    def __init__(self) -> None:
        self.id = uuid4()
        self.name = "test-run"
        self.steps: Dict[str, Any] = {}


class _DummyClient:
    def __init__(self, run: _DummyRun) -> None:
        self._run = run
        self.active_stack = type("Stack", (), {})()

    def get_pipeline_run(self, *args: Any, **kwargs: Any) -> _DummyRun:  # noqa: D401
        return self._run

    @property
    def zen_store(self):  # noqa: D401
        return type("Store", (), {})()


@pytest.fixture(autouse=True)
def clean_runtime():
    runtime.stop()
    yield
    runtime.stop()


def test_service_captures_in_memory_outputs(monkeypatch: pytest.MonkeyPatch):
    """Service should capture in-memory outputs before stopping runtime."""

    service = PipelineDeploymentService(uuid4())
    service.snapshot = _DummySnapshot()
    service._params_model = _DummyParams

    dummy_run = _DummyRun()

    # Patch Client used inside the service
    import zenml.deployers.server.service as svc_mod

    monkeypatch.setattr(
        svc_mod.client_mod, "Client", lambda: _DummyClient(dummy_run)
    )

    # Patch placeholder run creator to return object with id
    class _PH:
        def __init__(self) -> None:
            self.id = uuid4()

    # ensure run_utils module is available on svc_mod
    monkeypatch.setattr(
        svc_mod.run_utils,
        "create_placeholder_run",
        lambda snapshot, logs: _PH(),
    )

    # Replace orchestrator with a dummy that records outputs into runtime
    class _DummyOrchestrator:
        def run(self, snapshot, stack, placeholder_run):  # noqa: D401
            # while runtime is active, record some fast-path outputs
            runtime.record_step_outputs("step1", {"result": "fast_value"})

    service._orchestrator = _DummyOrchestrator()

    # Execute with in-memory mode enabled
    response = service.execute_pipeline(parameters={}, use_in_memory=True)

    assert response["success"] is True
    assert response["outputs"]["step1.result"] == "fast_value"
    assert (
        response["metadata"]["pipeline_name"]
        == service.snapshot.pipeline_configuration.name
    )
