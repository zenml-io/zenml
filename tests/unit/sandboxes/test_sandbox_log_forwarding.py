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
"""Tests for the shared sandbox log forwarding helper."""

import logging

import pytest

from zenml.sandboxes.base_sandbox import (
    BaseSandboxSettings,
    _iter_output_lines,
    forward_sandbox_output,
)


class TestIterOutputLines:
    """Tests for _iter_output_lines helper."""

    def test_empty_string_yields_nothing(self) -> None:
        assert list(_iter_output_lines("")) == []

    def test_single_line_without_newline(self) -> None:
        assert list(_iter_output_lines("hello")) == ["hello"]

    def test_single_line_with_newline(self) -> None:
        assert list(_iter_output_lines("hello\n")) == ["hello"]

    def test_multiple_lines(self) -> None:
        assert list(_iter_output_lines("line1\nline2\nline3")) == [
            "line1",
            "line2",
            "line3",
        ]

    def test_trailing_newline_does_not_produce_empty_line(self) -> None:
        lines = list(_iter_output_lines("line1\nline2\n"))
        assert lines == ["line1", "line2"]


class TestForwardSandboxOutput:
    """Tests for forward_sandbox_output helper."""

    def test_stdout_logged_at_info_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        test_logger = logging.getLogger("test.sandbox.forwarding")
        with caplog.at_level(logging.DEBUG, logger="test.sandbox.forwarding"):
            forward_sandbox_output(
                stdout="hello world\n",
                stderr="",
                target_logger=test_logger,
            )

        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) == 1
        assert "[sandbox:stdout]" in info_records[0].message
        assert "hello world" in info_records[0].message

    def test_stderr_logged_at_warning_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        test_logger = logging.getLogger("test.sandbox.forwarding")
        with caplog.at_level(logging.DEBUG, logger="test.sandbox.forwarding"):
            forward_sandbox_output(
                stdout="",
                stderr="error occurred\n",
                target_logger=test_logger,
            )

        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warning_records) == 1
        assert "[sandbox:stderr]" in warning_records[0].message
        assert "error occurred" in warning_records[0].message

    def test_multiline_output_produces_one_record_per_line(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        test_logger = logging.getLogger("test.sandbox.forwarding")
        with caplog.at_level(logging.DEBUG, logger="test.sandbox.forwarding"):
            forward_sandbox_output(
                stdout="line1\nline2\nline3\n",
                stderr="err1\nerr2\n",
                target_logger=test_logger,
            )

        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(info_records) == 3
        assert len(warning_records) == 2

    def test_empty_output_produces_no_records(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        test_logger = logging.getLogger("test.sandbox.forwarding")
        with caplog.at_level(logging.DEBUG, logger="test.sandbox.forwarding"):
            forward_sandbox_output(
                stdout="",
                stderr="",
                target_logger=test_logger,
            )

        assert len(caplog.records) == 0

    def test_custom_prefixes(self, caplog: pytest.LogCaptureFixture) -> None:
        test_logger = logging.getLogger("test.sandbox.forwarding")
        with caplog.at_level(logging.DEBUG, logger="test.sandbox.forwarding"):
            forward_sandbox_output(
                stdout="out\n",
                stderr="err\n",
                target_logger=test_logger,
                stdout_prefix="[custom:out]",
                stderr_prefix="[custom:err]",
            )

        messages = [r.message for r in caplog.records]
        assert any("[custom:out]" in m for m in messages)
        assert any("[custom:err]" in m for m in messages)

    def test_stdout_before_stderr_ordering(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        test_logger = logging.getLogger("test.sandbox.forwarding")
        with caplog.at_level(logging.DEBUG, logger="test.sandbox.forwarding"):
            forward_sandbox_output(
                stdout="out\n",
                stderr="err\n",
                target_logger=test_logger,
            )

        assert len(caplog.records) == 2
        assert caplog.records[0].levelno == logging.INFO
        assert caplog.records[1].levelno == logging.WARNING


class TestBaseSandboxSettings:
    """Tests for the forward_output_to_step_logs setting."""

    def test_default_is_enabled(self) -> None:
        settings = BaseSandboxSettings()
        assert settings.forward_output_to_step_logs is True

    def test_can_be_disabled(self) -> None:
        settings = BaseSandboxSettings(forward_output_to_step_logs=False)
        assert settings.forward_output_to_step_logs is False
