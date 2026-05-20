"""Unit tests for ZenML logging setup and formatters."""

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

import json
import logging
import sys
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import pytest
import structlog

import zenml.logger as zenml_logger_module
from zenml.constants import (
    ENV_ZENML_LOGGING_COLORS_DISABLED,
    ENV_ZENML_LOGGING_FORMAT,
)
from zenml.enums import LoggingLevels
from zenml.logger import (
    ZenMLConsoleFormatter,
    ZenMLConsoleHandler,
    ZenMLJsonFormatter,
    ZenMLLoggingHandler,
    bind_request_context,
    get_console_handler,
    get_logger,
    get_logging_context,
    init_logging,
    logging_scope,
)


@pytest.fixture(scope="module", autouse=True)
def auto_environment() -> Generator[
    tuple[SimpleNamespace, SimpleNamespace], None, None
]:
    """Use a lightweight test environment for logger-only tests."""
    yield SimpleNamespace(), SimpleNamespace()


@pytest.fixture(autouse=True)
def clean_logging_state(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Restore global logging state mutated by logger unit tests."""
    # `init_logging()` configures the process-wide root logger. The tests in
    # this module call it directly, so we preserve the root logger state that
    # existed before each test and restore it afterwards.
    root_logger = logging.getLogger()
    root_handlers = root_logger.handlers[:]
    root_level = root_logger.level
    root_disabled = root_logger.disabled
    disabled_level = logging.root.manager.disable

    # `init_logging()` also wraps stdout/stderr through `wrap_stdout_stderr()`.
    # Register the current stream methods and ZenML wrapper flags with
    # monkeypatch so pytest restores them if a test fails midway.
    monkeypatch.setattr(sys.stdout, "write", sys.stdout.write)
    monkeypatch.setattr(sys.stderr, "write", sys.stderr.write)
    monkeypatch.setattr(
        zenml_logger_module,
        "_original_stdout_write",
        zenml_logger_module._original_stdout_write,
    )
    monkeypatch.setattr(
        zenml_logger_module,
        "_original_stderr_write",
        zenml_logger_module._original_stderr_write,
    )
    monkeypatch.setattr(
        zenml_logger_module,
        "_stdout_wrapped",
        zenml_logger_module._stdout_wrapped,
    )
    monkeypatch.setattr(
        zenml_logger_module,
        "_stderr_wrapped",
        zenml_logger_module._stderr_wrapped,
    )

    structlog.contextvars.clear_contextvars()

    yield

    # Remove handlers added by the test, but do not close handlers that existed
    # before the test. Pytest and other fixtures may still own those handlers.
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        if handler not in root_handlers:
            handler.close()

    # Restore the original root logger configuration so later tests see the
    # same logging setup they would have seen if this module had not run.
    for handler in root_handlers:
        root_logger.addHandler(handler)

    root_logger.setLevel(root_level)
    root_logger.disabled = root_disabled
    logging.disable(disabled_level)

    # Structured logging context is stored separately from stdlib logging.
    # Clear it so request/scope fields from one test don't appear in another.
    structlog.contextvars.clear_contextvars()


def _make_log_record(
    message: str = "Step `demo` has started.",
    level: int = logging.INFO,
    **extra: Any,
) -> logging.LogRecord:
    """Create a log record with optional extra fields."""
    record = logging.LogRecord(
        name="zenml.test",
        level=level,
        pathname=__file__,
        lineno=42,
        msg=message,
        args=(),
        exc_info=None,
        func="test_function",
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_init_logging_is_idempotent() -> None:
    """Calling init_logging repeatedly does not duplicate ZenML handlers."""
    root_logger = logging.getLogger()

    # First init logging call
    init_logging()
    after_first_init = [
        type(handler).__name__ for handler in root_logger.handlers
    ]

    logging.getLogger("zenml.test").info("Step `demo` has started.")

    # Second init logging call
    init_logging()
    after_second_init = [
        type(handler).__name__ for handler in root_logger.handlers
    ]

    # Assert the handlers are the same after second init logging call.
    assert after_second_init == after_first_init

    # Assert zenml handlers are present
    assert (
        sum(
            isinstance(handler, ZenMLConsoleHandler)
            for handler in root_logger.handlers
        )
        == 1
    )
    assert (
        sum(
            isinstance(handler, ZenMLLoggingHandler)
            for handler in root_logger.handlers
        )
        == 1
    )


def test_init_logging_preserves_foreign_root_handlers() -> None:
    """Foreign root handlers survive ZenML logging reinitialization."""
    root_logger = logging.getLogger()
    foreign_handler = logging.NullHandler()
    root_logger.addHandler(foreign_handler)

    init_logging()

    assert foreign_handler in root_logger.handlers
    assert (
        sum(
            isinstance(handler, ZenMLConsoleHandler)
            for handler in root_logger.handlers
        )
        == 1
    )
    assert (
        sum(
            isinstance(handler, ZenMLLoggingHandler)
            for handler in root_logger.handlers
        )
        == 1
    )


def test_removing_zenml_handlers_does_not_remove_foreign_handlers() -> None:
    """ZenML handler cleanup does not remove unrelated stream handlers."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    foreign_handler = logging.StreamHandler()
    console_handler = get_console_handler()
    zenml_handler = ZenMLLoggingHandler()
    root_logger.addHandler(foreign_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(zenml_handler)

    zenml_logger_module._remove_zenml_handlers(root_logger)

    assert root_logger.handlers == [foreign_handler]


def test_json_formatted_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The logging format env var switches the console handler to JSON."""
    # Set the logging format to JSON.
    monkeypatch.setenv(ENV_ZENML_LOGGING_FORMAT, "json")

    handler = get_console_handler()
    record = _make_log_record(
        "request.completed",
        request_id="request-1",
        duration_ms=12.3,
        endpoint="list_pipelines",
    )

    # Assert the handler is a console handler and the formatter is a JSON formatter.
    assert isinstance(handler, ZenMLConsoleHandler)
    assert isinstance(handler.formatter, ZenMLJsonFormatter)

    # Assert the log record is formatted as a JSON object.
    payload = json.loads(handler.format(record))

    assert payload["message"] == "request.completed"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "zenml.test"
    assert payload["function"] == "test_function"
    assert payload["line"] == 42
    assert payload["request_id"] == "request-1"
    assert payload["duration_ms"] == 12.3
    assert payload["endpoint"] == "list_pipelines"
    assert payload["timestamp"]
    # Assert that payload does not contain any internal stdlib LogRecord fields.
    assert "event" not in payload
    assert "time" not in payload
    assert "msg" not in payload
    assert "args" not in payload
    assert "levelno" not in payload


def test_extra_collision_with_reserved_key_raises() -> None:
    """Reserved stdlib log record fields cannot be overwritten by extras."""
    logger = get_logger("zenml.test.reserved")

    with pytest.raises(KeyError, match="Attempt to overwrite 'name'"):
        logger.info("collision", extra={"name": "bad"})


def test_structured_console_formatted_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default console formatter renders structured logs with extras."""
    # By default, the logging format is console
    monkeypatch.delenv(ENV_ZENML_LOGGING_FORMAT, raising=False)
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.DEBUG,
    )
    # Disable ANSI colors so the structured console output can be asserted
    # as plain text.
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    handler = get_console_handler()
    record = _make_log_record(
        "endpoint.completed",
        level=logging.DEBUG,
        request_id="request-1",
        duration_ms=12.3,
    )

    # Assert the handler is a console handler and the formatter is a console formatter.
    assert isinstance(handler, ZenMLConsoleHandler)
    assert isinstance(handler.formatter, ZenMLConsoleFormatter)

    # Assert the log record is formatted as a structured log with extras.
    formatted = handler.format(record)

    assert "DEBUG" in formatted
    assert "zenml.test:test_function:42" in formatted
    assert "endpoint.completed" in formatted
    assert formatted.endswith(
        ' | {"request_id":"request-1","duration_ms":12.3}'
    )


def test_console_highlights_backticks_and_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bare console logs highlight backtick text and URLs when colors are on."""
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "false")
    record = _make_log_record(
        "Open `dashboard` at https://docs.zenml.io/path?q=1"
    )

    formatted = ZenMLConsoleFormatter().format(record)

    assert "`dashboard`" not in formatted
    assert f"{ZenMLConsoleFormatter._PURPLE}dashboard" in formatted
    assert (
        f"{ZenMLConsoleFormatter._BLUE}https://docs.zenml.io/path?q=1"
    ) in formatted


def test_color_disabled_strips_ansi_and_preserves_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabling colors removes ANSI codes from formatted console logs."""
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")
    message = "Open `dashboard` at https://docs.zenml.io/path?q=1"
    record = _make_log_record(message)

    formatted = ZenMLConsoleFormatter().format(record)

    assert formatted == message
    assert "\x1b[" not in formatted


def test_contextvars_filter_copies_bound_context_to_log_record() -> None:
    """Bound logging context is copied onto standard library log records."""
    # Bind the request context.
    bind_request_context(request_id="request-1", method="GET")
    record = _make_log_record("request.received")

    # Call the contextvars filter to copy the contextvars onto the log record.
    zenml_logger_module._ContextVarsFilter().filter(record)

    # Assert the contextvars are copied onto the log record.
    assert getattr(record, "request_id") == "request-1"
    assert getattr(record, "method") == "GET"


def test_logging_scope_restores_outer_context() -> None:
    """Scoped logging context is removed after leaving the scope."""
    bind_request_context(request_id="request-1")

    with logging_scope(transaction_id="transaction-1"):
        assert get_logging_context() == {
            "request_id": "request-1",
            "transaction_id": "transaction-1",
        }

    assert get_logging_context() == {"request_id": "request-1"}
