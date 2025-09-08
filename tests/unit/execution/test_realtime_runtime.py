"""Unit tests for RealtimeStepRuntime queue/backpressure and sweep."""

import queue
from types import SimpleNamespace

from zenml.execution.realtime_runtime import RealtimeStepRuntime


def test_realtime_queue_full_inline_fallback(monkeypatch):
    """When queue is full, publish events are processed inline as fallback."""
    rt = RealtimeStepRuntime(ttl_seconds=1, max_entries=8)

    # Replace queue with a tiny one and fill it
    rt._q = queue.Queue(maxsize=1)  # type: ignore[attr-defined]
    rt._q.put(("dummy", (), {}))  # fill once

    called = {"step": 0}

    def _pub_step_run_metadata(*args, **kwargs):
        called["step"] += 1

    monkeypatch.setattr(
        "zenml.orchestrators.publish_utils.publish_step_run_metadata",
        _pub_step_run_metadata,
    )

    # This put_nowait should hit Full and process inline
    rt.publish_step_run_metadata(
        step_run_id=SimpleNamespace(), step_run_metadata={}
    )
    assert called["step"] == 1


def test_realtime_sweep_expired_no_keyerror():
    """Expired cache entries are swept safely without KeyError races."""
    rt = RealtimeStepRuntime(ttl_seconds=0, max_entries=8)
    # Insert an expired cache entry manually
    with rt._lock:  # type: ignore[attr-defined]
        rt._cache["k1"] = ("v", 0.0)  # type: ignore[attr-defined]
    # Should not raise
    rt._sweep_expired()
