"""Unit tests for trigger dispatch state collation behavior."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.models import (
    TriggerDispatchStatusCode,
    TriggerSnapshotDispatchState,
)
from zenml.zen_stores.schemas.trigger_assoc import TriggerSnapshotSchema


def test_error_count_increments_for_same_error_type() -> None:
    """Same error type should increment the persisted error count."""
    state = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.ERROR,
        last_error_message="existing failure",
        last_error_type="DISPATCH_PUBLISH_ERROR",
        last_error_count=1,
    )
    next_error = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.ERROR,
        last_error_message="second failure",
        last_error_type="DISPATCH_PUBLISH_ERROR",
    )
    state.apply_new_state(new_state=next_error)
    assert state.last_error_count == 2


def test_error_count_resets_for_new_error_type() -> None:
    """Changing error type should reset count to one."""
    state = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.ERROR,
        last_error_message="publish failed",
        last_error_type="DISPATCH_PUBLISH_ERROR",
        last_error_count=7,
    )
    new_error = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.ERROR,
        last_error_message="execution failed",
        last_error_type="DISPATCH_EXECUTION_ERROR",
    )
    state.apply_new_state(new_state=new_error)
    assert state.last_error_count == 1
    assert state.last_error_type == "DISPATCH_EXECUTION_ERROR"


def test_success_keeps_previous_error_details() -> None:
    """Success state should preserve the latest error details."""
    state = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.ERROR,
        last_error_message="boom",
        last_error_type="DISPATCH_EXECUTION_ERROR",
        last_error_count=3,
    )
    success_change = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.SUCCESS,
    )
    state.apply_new_state(new_state=success_change)
    assert state.last_status == TriggerDispatchStatusCode.SUCCESS
    assert state.last_error_message == "boom"
    assert state.last_error_type == "DISPATCH_EXECUTION_ERROR"
    assert state.last_error_count == 3


def test_parse_trigger_dispatch_state_returns_none_for_invalid_json() -> None:
    """Invalid persisted JSON should be treated as missing state."""
    row = TriggerSnapshotSchema(
        trigger_id=uuid4(),
        snapshot_id=uuid4(),
        dispatch_state="{not-json",
    )
    assert row.parsed_dispatch_state is None


def test_dispatch_state_field_limits_are_enforced() -> None:
    """Message is truncated but error type length is validated."""
    state = TriggerSnapshotDispatchState(
        last_status=TriggerDispatchStatusCode.ERROR,
        last_error_message="x" * 5000,
        last_error_type="DISPATCH_EXECUTION_ERROR",
    )

    assert state.last_error_message is not None
    assert (
        len(state.last_error_message)
        == TriggerSnapshotDispatchState.MESSAGE_MAX_LENGTH
    )

    with pytest.raises(ValidationError):
        TriggerSnapshotDispatchState(
            last_status=TriggerDispatchStatusCode.ERROR,
            last_error_message="boom",
            last_error_type="E" * 500,
        )
