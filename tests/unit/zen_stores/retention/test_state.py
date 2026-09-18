# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Sweep counters describe one whole scan, not its last resumed segment."""

from datetime import datetime
from uuid import uuid4

from zenml.zen_stores.retention.state import Cursor, RetentionState


def test_resumed_sweep_keeps_counts_until_a_new_scan_starts() -> None:
    """A lease that continues from a saved cursor accumulates counts."""
    state = RetentionState()
    state.start(uuid4())
    state.archived, state.failed = 200, 3
    state.cursor = Cursor(end_time=datetime(2026, 1, 1), run_id=uuid4())

    state.start(uuid4())
    assert (state.archived, state.failed) == (200, 3)

    state.cursor = None
    state.start(uuid4())
    assert (state.archived, state.failed) == (0, 0)
