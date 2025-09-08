"""Unit tests for MemoryStepRuntime instance-scoped isolation."""

from types import SimpleNamespace

from zenml.execution.memory_runtime import MemoryStepRuntime


def test_memory_runtime_instance_isolated_store(monkeypatch):
    """Each runtime instance isolates values by run id; no cross leakage."""
    # Create two independent runtimes (instance-scoped stores)
    rt1 = MemoryStepRuntime()
    rt2 = MemoryStepRuntime()

    # Patch get_step_context to return minimal stubs
    class _Ctx:
        def __init__(self, run_id: str, step_name: str):
            self.pipeline_run = SimpleNamespace(id=run_id)
            self.step_run = SimpleNamespace(name=step_name)

        def get_output_metadata(self, name: str):
            return {}

        def get_output_tags(self, name: str):
            return []

    monkeypatch.setattr(
        "zenml.execution.step_runtime.get_step_context",
        lambda: _Ctx("run-1", "s1"),
    )

    # Store with rt1
    outputs = {"out": 123}
    handles1 = rt1.store_output_artifacts(
        output_data=outputs,
        output_materializers={"out": ()},
        output_artifact_uris={"out": "memory://run-1/s1/out"},
        output_annotations={"out": SimpleNamespace(artifact_config=None)},
        artifact_metadata_enabled=False,
        artifact_visualization_enabled=False,
    )
    h1 = handles1["out"]

    # Switch context for rt2
    monkeypatch.setattr(
        "zenml.execution.step_runtime.get_step_context",
        lambda: _Ctx("run-2", "s2"),
    )
    handles2 = rt2.store_output_artifacts(
        output_data={"out": 999},
        output_materializers={"out": ()},
        output_artifact_uris={"out": "memory://run-2/s2/out"},
        output_annotations={"out": SimpleNamespace(artifact_config=None)},
        artifact_metadata_enabled=False,
        artifact_visualization_enabled=False,
    )
    h2 = handles2["out"]

    # rt1 should load its own value
    v1 = rt1.load_input_artifact(artifact=h1, data_type=int, stack=None)
    assert v1 == 123

    # rt2 should load its own value
    v2 = rt2.load_input_artifact(artifact=h2, data_type=int, stack=None)
    assert v2 == 999

    # rt1 should NOT see rt2 value
    assert (
        rt1.load_input_artifact(artifact=h2, data_type=int, stack=None) is None
    )
