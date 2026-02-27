import logging
import threading
from typing import Any, List

from zenml.zen_stores.resource_pool_reconciler import ResourcePoolReconciler


class _DummyStoreConfig:
    def get_sqlalchemy_config(self) -> Any:
        return "sqlite://", {}, {}


class _DummyStore:
    config = _DummyStoreConfig()

    def __init__(self) -> None:
        self.reconcile_calls = 0

    def reconcile_resource_pools(
        self, max_allocations_per_pool: int = 100
    ) -> None:
        self.reconcile_calls += 1


def test_reconciler_start_is_idempotent(monkeypatch):
    store = _DummyStore()
    reconciler = ResourcePoolReconciler(store=store)

    def _fake_run_loop(
        stop_event: threading.Event,
        interval_seconds: float = 30.0,
        max_allocations_per_pool: int = 100,
    ) -> None:
        stop_event.wait(1)

    monkeypatch.setattr(reconciler, "run_loop", _fake_run_loop)

    reconciler.start(interval_seconds=30, max_allocations_per_pool=100)
    first_thread = reconciler._thread
    assert first_thread is not None
    reconciler.start(interval_seconds=30, max_allocations_per_pool=100)
    assert reconciler._thread is first_thread

    reconciler.stop(timeout_seconds=1)
    assert reconciler._thread is None
    assert reconciler._stop_event is None


def test_reconciler_stop_timeout_keeps_state_for_retry():
    store = _DummyStore()
    reconciler = ResourcePoolReconciler(store=store)
    reconciler._stop_event = threading.Event()

    class _NeverStoppingThread:
        def is_alive(self) -> bool:
            return True

        def join(self, timeout: float) -> None:
            return

    thread = _NeverStoppingThread()
    reconciler._thread = thread
    reconciler.stop(timeout_seconds=0.01)

    assert reconciler._thread is thread
    assert reconciler._stop_event is not None


def test_reconciler_follower_retry_uses_jitter_and_debug_log(
    monkeypatch, caplog
):
    store = _DummyStore()
    reconciler = ResourcePoolReconciler(store=store)

    monkeypatch.setattr(reconciler, "_try_acquire_lock", lambda: False)
    monkeypatch.setattr("random.uniform", lambda a, b: 1.5)

    wait_calls: List[float] = []

    class _StopAfterWaitEvent:
        def is_set(self) -> bool:
            return False

        def wait(self, timeout: float) -> bool:
            wait_calls.append(timeout)
            return True

    stop_event = _StopAfterWaitEvent()

    caplog.set_level(logging.DEBUG)
    reconciler.run_loop(
        stop_event=stop_event,
        interval_seconds=10,
        max_allocations_per_pool=100,
    )

    assert wait_calls == [11.5]
