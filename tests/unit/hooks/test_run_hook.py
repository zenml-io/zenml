#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Unit tests for run_hook status and exception handling."""

from unittest import mock
from uuid import uuid4

import pytest

from zenml.constants import ENV_ZENML_TRACK_LIFECYCLE_HOOK_OUTPUTS
from zenml.enums import ExecutionStatus, HookType
from zenml.hooks import execution as hook_execution
from zenml.hooks.execution import (
    _get_log_source_name,
    run_hook,
    run_lifecycle_hook,
)
from zenml.utils import source_utils


def _good_hook() -> int:
    return 5


def _boom_hook() -> None:
    raise RuntimeError("boom")


async def _async_hook() -> int:
    return 7


async def _async_boom_hook() -> None:
    raise RuntimeError("async boom")


def test_run_hook_output_parse_error_keeps_status_completed():
    """An output parse error does not mark a successful hook as FAILED."""
    with mock.patch.object(
        hook_execution,
        "_parse_hook_outputs",
        side_effect=ValueError("bad shape"),
    ):
        with mock.patch.object(
            hook_execution, "record_hook_invocation"
        ) as record:
            with pytest.raises(ValueError, match="bad shape"):
                run_hook(_good_hook, store_return=True)

    record.assert_called_once()
    assert record.call_args.kwargs["status"] == ExecutionStatus.COMPLETED
    assert record.call_args.kwargs["exception_info"] is None


def test_run_hook_failure_records_failed_with_exception_info():
    """A failing hook records FAILED with exception info and re-raises."""
    with mock.patch.object(hook_execution, "record_hook_invocation") as record:
        with pytest.raises(RuntimeError, match="boom"):
            run_hook(_boom_hook)

    record.assert_called_once()
    assert record.call_args.kwargs["status"] == ExecutionStatus.FAILED
    assert record.call_args.kwargs["exception_info"] is not None


def test_run_hook_async_function_runs_coroutine_to_completion():
    """An async hook runs to completion and returns its result."""
    with mock.patch.object(hook_execution, "record_hook_invocation"):
        assert run_hook(_async_hook) == 7


def test_run_hook_async_failure_records_failed_with_exception_info():
    """A failing async hook records FAILED with exception info and re-raises."""
    with mock.patch.object(hook_execution, "record_hook_invocation") as record:
        with pytest.raises(RuntimeError, match="async boom"):
            run_hook(_async_boom_hook)

    record.assert_called_once()
    assert record.call_args.kwargs["status"] == ExecutionStatus.FAILED
    assert record.call_args.kwargs["exception_info"] is not None


def test_hook_log_source_lifecycle_uses_type():
    """Lifecycle hooks log under a source named after their type."""
    assert (
        _get_log_source_name(HookType.STEP_FAILURE, None)
        == "hook:step_failure"
    )


def test_hook_log_source_custom_uses_name():
    """A named custom hook logs under a source named after it."""
    assert (
        _get_log_source_name(HookType.CUSTOM, "model_call")
        == "hook:custom:model_call"
    )


def test_hook_log_source_custom_without_name():
    """An unnamed custom hook logs under the generic custom source."""
    assert _get_log_source_name(HookType.CUSTOM, None) == "hook:custom"


def test_run_hook_links_logs_id_from_context_to_record():
    """The logs id is read off the logging context and linked on the record."""
    logs_id = uuid4()
    fake_context = mock.MagicMock()
    fake_context.log_model.id = logs_id
    with (
        mock.patch.object(
            hook_execution,
            "setup_hook_logging_context",
            return_value=fake_context,
        ) as logs_context,
        mock.patch.object(hook_execution, "record_hook_invocation") as record,
    ):
        run_hook(_good_hook)

    logs_context.assert_called_once_with(HookType.CUSTOM, "_good_hook")
    record.assert_called_once()
    assert record.call_args.kwargs["logs_id"] == logs_id
    assert record.call_args.kwargs["name"] == "_good_hook"
    assert "hook_invocation_id" not in record.call_args.kwargs


def test_run_hook_untracked_skips_recording():
    """An untracked hook captures logs but records nothing."""
    with (
        mock.patch.object(
            hook_execution, "setup_hook_logging_context"
        ) as logs_context,
        mock.patch.object(hook_execution, "record_hook_invocation") as record,
    ):
        assert run_hook(_good_hook, track=False) == 5

    logs_context.assert_called_once_with(HookType.CUSTOM, "_good_hook")
    record.assert_not_called()


def test_run_hook_without_run_context_still_returns():
    """A missing run context disables log capture without breaking the hook."""
    with mock.patch.object(hook_execution, "record_hook_invocation"):
        assert run_hook(_good_hook) == 5


def test_run_lifecycle_hook_outputs_disabled_by_default():
    """A lifecycle hook does not store its return value by default."""
    source = source_utils.resolve(_good_hook)
    with mock.patch.object(hook_execution, "run_hook") as run:
        run_lifecycle_hook(source, HookType.STEP_END)

    run.assert_called_once()
    assert run.call_args.kwargs["store_return"] is False


def test_run_lifecycle_hook_outputs_enabled_by_env_var(monkeypatch):
    """The env var enables storing lifecycle hook return values."""
    monkeypatch.setenv(ENV_ZENML_TRACK_LIFECYCLE_HOOK_OUTPUTS, "true")
    source = source_utils.resolve(_good_hook)
    with mock.patch.object(hook_execution, "run_hook") as run:
        run_lifecycle_hook(source, HookType.STEP_END)

    run.assert_called_once()
    assert run.call_args.kwargs["store_return"] is True
