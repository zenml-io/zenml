"""Unit test for defensive artifact write behavior (retry + validate)."""

from types import SimpleNamespace

from zenml.execution.step_runtime import DefaultStepRuntime


def test_artifact_write_retry_and_validate(monkeypatch):
    """First batch create fails, retry succeeds; responses length validated."""
    rt = DefaultStepRuntime()

    # Patch helpers used to build requests
    monkeypatch.setattr(
        "zenml.orchestrators.publish_utils.publish_successful_step_run",
        lambda *a, **k: None,
    )

    # Minimal step context stub
    class _Ctx:
        def __init__(self):
            self.pipeline_run = SimpleNamespace(
                config=SimpleNamespace(tags=None), pipeline=None
            )
            self.step_run = SimpleNamespace(name="step")

        def get_output_metadata(self, name: str):
            return {}

        def get_output_tags(self, name: str):
            return []

    monkeypatch.setattr(
        "zenml.execution.step_runtime.get_step_context",
        lambda: _Ctx(),
    )

    # Patch request preparation to avoid heavy imports
    monkeypatch.setattr(
        "zenml.execution.step_runtime._store_artifact_data_and_prepare_request",
        lambda **k: {"req": k},
    )
    # Patch materializer selection
    monkeypatch.setattr(
        "zenml.execution.step_runtime.materializer_utils.select_materializer",
        lambda data_type, materializer_classes: object,
    )
    monkeypatch.setattr(
        "zenml.execution.step_runtime.source_utils.load_and_validate_class",
        lambda *a, **k: object,
    )

    calls = {"attempts": 0}

    class _Client:
        class _Store:
            def batch_create_artifact_versions(self, reqs):
                calls["attempts"] += 1
                if calls["attempts"] == 1:
                    raise RuntimeError("transient")
                # Return matching length list
                return [SimpleNamespace(id=i) for i in range(len(reqs))]

        zen_store = _Store()

    monkeypatch.setattr(
        "zenml.execution.step_runtime.Client", lambda: _Client()
    )

    res = rt.store_output_artifacts(
        output_data={"out": 1},
        output_materializers={"out": ()},
        output_artifact_uris={"out": "uri://out"},
        output_annotations={"out": SimpleNamespace(artifact_config=None)},
        artifact_metadata_enabled=False,
        artifact_visualization_enabled=False,
    )
    assert "out" in res
    assert calls["attempts"] == 2
