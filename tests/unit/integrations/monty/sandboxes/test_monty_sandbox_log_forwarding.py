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
"""Tests for Monty sandbox log forwarding behavior."""

from zenml.integrations.monty.sandboxes.monty_sandbox import (
    _build_print_callback,
)


def test_monty_print_callback_forwards_stdout_and_stderr(mocker) -> None:
    """Ensures Monty callback forwards stdout at INFO and stderr at WARNING."""
    info_mock = mocker.patch(
        "zenml.integrations.monty.sandboxes.monty_sandbox.logger.info"
    )
    warning_mock = mocker.patch(
        "zenml.integrations.monty.sandboxes.monty_sandbox.logger.warning"
    )

    expected_extra = {
        "zenml_log_source": "sandbox",
        "zenml_sandbox_session_id": "sess-abc",
    }

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    callback = _build_print_callback(
        stdout_chunks,
        stderr_chunks,
        forward_to_step_logs=True,
        session_id="sess-abc",
    )

    callback("stdout", "hello world\n")
    callback("stderr", "error line\n")

    assert stdout_chunks == ["hello world\n"]
    assert stderr_chunks == ["error line\n"]

    # Messages are plain (no prefix); routing info is in extras
    info_mock.assert_called_once_with("hello world", extra=expected_extra)
    warning_mock.assert_called_once_with("error line", extra=expected_extra)


def test_monty_print_callback_respects_disabled_forwarding(mocker) -> None:
    """Ensures Monty callback collects output but skips logging when disabled."""
    info_mock = mocker.patch(
        "zenml.integrations.monty.sandboxes.monty_sandbox.logger.info"
    )
    warning_mock = mocker.patch(
        "zenml.integrations.monty.sandboxes.monty_sandbox.logger.warning"
    )

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    callback = _build_print_callback(
        stdout_chunks,
        stderr_chunks,
        forward_to_step_logs=False,
    )

    callback("stdout", "hello\n")
    callback("stderr", "error\n")

    assert stdout_chunks == ["hello\n"]
    assert stderr_chunks == ["error\n"]

    info_mock.assert_not_called()
    warning_mock.assert_not_called()
