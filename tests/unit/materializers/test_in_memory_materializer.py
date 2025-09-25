"""Unit tests for the simple in-memory materializer."""

from typing import Any, Dict

from zenml.materializers.in_memory_materializer import InMemoryMaterializer


def test_in_memory_materializer_uses_runtime(monkeypatch) -> None:
    """Verify that the materializer stores and loads data via the runtime."""

    stored: Dict[str, Any] = {}

    # Patch the serving runtime helpers used by the materializer.
    from zenml.deployers.server import runtime

    monkeypatch.setattr(runtime, "is_active", lambda: True)
    monkeypatch.setattr(
        runtime, "should_skip_artifact_materialization", lambda: True
    )
    monkeypatch.setattr(runtime, "put_in_memory_data", stored.__setitem__)
    monkeypatch.setattr(runtime, "get_in_memory_data", stored.get)

    # Simple approach - no wrapping needed
    materializer = InMemoryMaterializer(
        uri="s3://bucket/artifact", artifact_store=None
    )

    payload = {"foo": "bar"}
    materializer.save(payload)

    # Data should be stored with original URI as key
    assert stored["s3://bucket/artifact"] == payload

    loaded = materializer.load(dict)
    assert loaded == payload


def test_in_memory_materializer_metadata_methods() -> None:
    """Test that metadata methods return empty results in serving mode."""

    materializer = InMemoryMaterializer(
        uri="s3://bucket/artifact", artifact_store=None
    )

    # All metadata methods should return empty/None in serving mode
    assert materializer.extract_full_metadata({}) == {}
    assert materializer.compute_content_hash({}) is None
    assert materializer.save_visualizations({}) == {}


def test_in_memory_materializer_missing_data() -> None:
    """Test that loading missing data raises appropriate error."""

    from zenml.deployers.server import runtime

    materializer = InMemoryMaterializer(
        uri="s3://missing/artifact", artifact_store=None
    )

    # Mock runtime to return None for missing data
    def mock_get_data(uri):
        return None

    import unittest.mock

    with unittest.mock.patch.object(
        runtime, "get_in_memory_data", mock_get_data
    ):
        try:
            materializer.load(dict)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "No data available" in str(e)
            assert "s3://missing/artifact" in str(e)
