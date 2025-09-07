"""Unit tests for DefaultStepRuntime metadata/visualization toggles."""

from types import SimpleNamespace

from zenml.execution.default_runtime import DefaultStepRuntime


def test_publish_metadata_skips_when_disabled(monkeypatch):
    """Test that metadata is not published when disabled."""
    rt = DefaultStepRuntime()
    setattr(rt, "_metadata_enabled", False)

    called = {"run": 0, "step": 0}

    def _pub_run_md(*a, **k):
        """Mock publish pipeline run metadata."""
        called["run"] += 1

    def _pub_step_md(*a, **k):
        """Mock publish step run metadata."""
        called["step"] += 1

    monkeypatch.setattr(
        "zenml.orchestrators.publish_utils.publish_pipeline_run_metadata",
        _pub_run_md,
    )
    monkeypatch.setattr(
        "zenml.orchestrators.publish_utils.publish_step_run_metadata",
        _pub_step_md,
    )

    rt.publish_pipeline_run_metadata(
        pipeline_run_id=SimpleNamespace(), pipeline_run_metadata={}
    )
    rt.publish_step_run_metadata(
        step_run_id=SimpleNamespace(), step_run_metadata={}
    )

    assert called["run"] == 0
    assert called["step"] == 0
