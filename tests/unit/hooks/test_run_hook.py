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

import pytest

from zenml.enums import ExecutionStatus
from zenml.hooks import execution as hook_execution
from zenml.hooks.execution import run_hook


def _good_hook() -> int:
    return 5


def _boom_hook() -> None:
    raise RuntimeError("boom")


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
