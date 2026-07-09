"""Unit tests for the snapshot-on-failure helper in run_episode.

These are pure fakes — no sandbox, no server — covering the three
outcomes _snapshot_failed_session must never confuse: snapshot taken,
flavor doesn't support snapshots (kubernetes/local today), and snapshot
attempt itself crashed. In all three cases the helper must not raise:
a snapshot failure must never turn a scored episode into a crashed step.

Run from the example directory:  pytest tests/test_snapshot.py -v
"""

import sys
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

EXAMPLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXAMPLE_DIR))

from steps.run_episode import _snapshot_failed_session  # noqa: E402

from zenml.sandboxes import SandboxSnapshot  # noqa: E402


class SnapshotCapableSession:
    def __init__(self) -> None:
        self.sandbox_id = uuid4()

    def create_snapshot(self) -> SandboxSnapshot:
        return SandboxSnapshot(sandbox_id=self.sandbox_id, ref="im-test123")


class UnsupportedSession:
    def create_snapshot(self) -> SandboxSnapshot:
        raise NotImplementedError(
            "KubernetesSandboxSession does not support creating snapshots."
        )


class CrashingSession:
    def create_snapshot(self) -> SandboxSnapshot:
        raise RuntimeError("provider exploded")


def _fresh_result() -> Dict[str, Any]:
    return {"snapshot": None, "snapshot_error": None}


def test_snapshot_recorded_on_success() -> None:
    session = SnapshotCapableSession()
    result, timings = _fresh_result(), {}
    _snapshot_failed_session(session, result, timings)
    assert result["snapshot"]["ref"] == "im-test123"
    assert result["snapshot"]["sandbox_id"] == str(session.sandbox_id)
    assert result["snapshot_error"] is None
    assert "snapshot_s" in timings
    # The stored dict must round-trip back into the model restore() needs.
    assert SandboxSnapshot(**result["snapshot"]).ref == "im-test123"


def test_unsupported_flavor_records_error_without_raising() -> None:
    result, timings = _fresh_result(), {}
    _snapshot_failed_session(UnsupportedSession(), result, timings)
    assert result["snapshot"] is None
    assert result["snapshot_error"].startswith("unsupported: ")
    assert "snapshot_s" in timings


def test_snapshot_crash_records_error_without_raising() -> None:
    result, timings = _fresh_result(), {}
    _snapshot_failed_session(CrashingSession(), result, timings)
    assert result["snapshot"] is None
    assert result["snapshot_error"] == "RuntimeError: provider exploded"
    assert "snapshot_s" in timings
