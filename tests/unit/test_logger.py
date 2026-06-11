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
from typing import Any, cast

import pytest

import zenml.logger as zenml_logger_module
from zenml.constants import (
    ENV_ZENML_CONSOLE_LOGGING_FORMAT,
    ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS,
    ENV_ZENML_LOGGING_COLORS_DISABLED,
    ENV_ZENML_LOGGING_FORMAT,
    ENV_ZENML_SERVER,
)
from zenml.enums import LoggingLevels
from zenml.logger import (
    ZenMLConsoleFormatter,
    ZenMLConsoleHandler,
    ZenMLJsonFormatter,
    ZenMLLoggingHandler,
    bind_log_context,
    clear_log_context,
    get_logger,
    get_logging_context,
    init_logging,
    logging_context,
)

#####################
# Fixtures / helpers
# ###################


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

    clear_log_context()

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
    clear_log_context()


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


###############################################
# Logging Initialization And Handler Lifecycle
###############################################


def test_init_logging_is_idempotent() -> None:
    """Calling init_logging repeatedly does not duplicate ZenML handlers."""
    root_logger = logging.getLogger()

    init_logging()
    after_first_init = [
        type(handler).__name__ for handler in root_logger.handlers
    ]

    # Emitting once between init calls exercises the configured handlers before
    # reinitialization. The second init should reconfigure ZenML-owned handlers
    # without stacking duplicate console/log-store handlers on the root logger.
    logging.getLogger("zenml.test").info("Step `demo` has started.")

    init_logging()
    after_second_init = [
        type(handler).__name__ for handler in root_logger.handlers
    ]

    assert after_second_init == after_first_init

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
    console_handler = ZenMLConsoleHandler()
    zenml_handler = ZenMLLoggingHandler()
    root_logger.addHandler(foreign_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(zenml_handler)

    zenml_logger_module._remove_zenml_handlers(root_logger)

    assert root_logger.handlers == [foreign_handler]


######################################################
# Console Format Selection And Environment Variables
######################################################


def test_default_console_logging_format_selects_console_formatter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset logging format env vars select the human console formatter."""
    monkeypatch.delenv(ENV_ZENML_LOGGING_FORMAT, raising=False)
    monkeypatch.delenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, raising=False)
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    handler = ZenMLConsoleHandler()

    # Assert the handler is a console handler and logs are
    # formatted as expected.
    assert isinstance(handler.formatter, ZenMLConsoleFormatter)
    assert handler.format(_make_log_record("default layout")) == (
        "default layout"
    )


def test_custom_console_logging_format_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid custom console formats are applied to log records."""
    monkeypatch.setenv(
        ENV_ZENML_CONSOLE_LOGGING_FORMAT, "%(message)s [%(levelname)s]"
    )
    handler = ZenMLConsoleHandler()

    assert handler.format(_make_log_record("custom layout")) == (
        "custom layout [INFO]"
    )


def test_invalid_console_logging_format_falls_back_to_console_formatter(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Invalid custom console formats fall back to the default formatter."""
    monkeypatch.setenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, "invalid")
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    with caplog.at_level(logging.WARNING):
        handler = ZenMLConsoleHandler()

    assert isinstance(handler.formatter, ZenMLConsoleFormatter)
    assert handler.format(_make_log_record("fallback layout")) == (
        "fallback layout"
    )
    assert "Invalid console logging format: invalid" in caplog.text


def test_deprecated_logging_format_alias_uses_custom_console_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deprecated logging format variable remains a custom format alias."""
    monkeypatch.delenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, raising=False)
    monkeypatch.setenv(ENV_ZENML_LOGGING_FORMAT, "%(message)s [%(levelname)s]")

    handler = ZenMLConsoleHandler()

    assert handler.format(_make_log_record("custom log layout")) == (
        "custom log layout [INFO]"
    )


def test_deprecated_logging_format_alias_warns_on_init(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Using only the deprecated logging format variable emits a warning."""
    monkeypatch.delenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, raising=False)
    monkeypatch.setenv(ENV_ZENML_LOGGING_FORMAT, "%(message)s")

    with caplog.at_level(logging.WARNING):
        init_logging()

    assert (
        f"The `{ENV_ZENML_LOGGING_FORMAT}` environment variable is deprecated"
        in caplog.text
    )
    assert f"Use `{ENV_ZENML_CONSOLE_LOGGING_FORMAT}` instead" in caplog.text


def test_console_logging_format_takes_precedence_over_deprecated_alias(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The new console logging format variable wins over the deprecated alias."""
    # Both env vars can be present during migration. The new variable should
    # select the formatter and suppress the deprecation warning for the old one.
    monkeypatch.setenv(ENV_ZENML_LOGGING_FORMAT, "%(levelname)s %(message)s")
    monkeypatch.setenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, "%(message)s")

    with caplog.at_level(logging.WARNING):
        init_logging()

    console_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, ZenMLConsoleHandler)
    ]

    assert console_handlers[0].format(_make_log_record("new format")) == (
        "new format"
    )
    assert ENV_ZENML_LOGGING_FORMAT not in caplog.text


def test_deprecated_logging_format_alias_selects_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deprecated logging format variable can still select JSON output."""
    monkeypatch.delenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, raising=False)
    monkeypatch.setenv(ENV_ZENML_LOGGING_FORMAT, "json")

    handler = ZenMLConsoleHandler()

    assert isinstance(handler.formatter, ZenMLJsonFormatter)
    assert (
        json.loads(handler.format(_make_log_record("legacy json")))["message"]
        == "legacy json"
    )


def test_server_logs_use_custom_console_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server console logs use valid custom console formats."""
    monkeypatch.setenv(ENV_ZENML_SERVER, "true")
    monkeypatch.setenv(
        ENV_ZENML_CONSOLE_LOGGING_FORMAT, "%(asctime)s %(message)s"
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    handler = ZenMLConsoleHandler()
    record = _make_log_record("server.started")

    formatted = handler.format(record)

    assert formatted.endswith(" server.started")
    assert "zenml.test:test_function:42" not in formatted


def test_server_logs_default_to_structured_console_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server console logs use structured output when no custom format is set."""
    monkeypatch.setenv(ENV_ZENML_SERVER, "true")
    monkeypatch.delenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, raising=False)
    monkeypatch.delenv(ENV_ZENML_LOGGING_FORMAT, raising=False)
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    formatted = ZenMLConsoleFormatter().format(
        _make_log_record("server.started")
    )

    assert "INFO" in formatted
    assert "zenml.test:test_function:42" in formatted
    assert formatted.endswith("server.started")


##########################
# JSON Console Formatting
##########################


def test_json_formatted_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The client console logging format env var selects JSON output."""
    monkeypatch.setenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, "json")

    handler = ZenMLConsoleHandler()
    record = _make_log_record(
        "request.completed",
        request_id="request-1",
        duration_ms=12.3,
        endpoint="list_pipelines",
        step="trainer",
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
    assert payload["step"] == "trainer"
    assert payload["timestamp"]
    # Assert that payload does not contain any internal stdlib LogRecord fields.
    assert "event" not in payload
    assert "time" not in payload
    assert "msg" not in payload
    assert "args" not in payload
    assert "levelno" not in payload


def test_json_logs_keep_message_unprefixed_when_step_prefix_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON output keeps step context structured instead of mutating message."""
    monkeypatch.setenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, "json")
    record = _make_log_record("training.started", step="trainer")
    # Step prefixes are a human-console affordance. JSON logs should retain
    # `step` as structured data instead of folding it into `message`.
    token = zenml_logger_module.step_names_in_console.set(True)

    try:
        payload = json.loads(ZenMLConsoleHandler().format(record))
    finally:
        zenml_logger_module.step_names_in_console.reset(token)

    assert payload["message"] == "training.started"
    assert payload["step"] == "trainer"
    assert record.getMessage() == "training.started"


def test_json_logs_include_exception_and_stack_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON logs include diagnostic fields for exceptions and stack info."""
    monkeypatch.setenv(ENV_ZENML_CONSOLE_LOGGING_FORMAT, "json")

    try:
        raise ValueError("broken")
    except ValueError:
        record = _make_log_record("request.failed")
        record.exc_info = sys.exc_info()
        record.stack_info = "Stack (most recent call last):\nstack line"

    payload = json.loads(ZenMLConsoleHandler().format(record))

    assert payload["message"] == "request.failed"
    assert payload["exception"]["type"] == "ValueError"
    assert payload["exception"]["message"] == "broken"
    assert "ValueError: broken" in payload["exception"]["stacktrace"]
    assert (
        payload["stack_info"] == "Stack (most recent call last):\nstack line"
    )


################################
# Structured Console Formatting
################################


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

    handler = ZenMLConsoleHandler()
    record = _make_log_record(
        "endpoint.completed",
        level=logging.DEBUG,
        request_id="request-1",
        duration_ms=12.3,
        step="trainer",
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
        ' | {"request_id":"request-1","duration_ms":12.3,"step":"trainer"}'
    )


def test_structured_console_logs_prefix_step_name_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured human console logs prefix the message when enabled."""
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.DEBUG,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")
    record = _make_log_record(
        "endpoint.completed",
        level=logging.DEBUG,
        request_id="request-1",
        step="trainer",
    )
    # Formatting temporarily mutates LogRecord.msg so the prefix appears in the
    # %(message)s position. The assertion below verifies the record is restored
    # afterwards, which protects other handlers attached to the same record.
    token = zenml_logger_module.step_names_in_console.set(True)

    try:
        formatted = ZenMLConsoleFormatter().format(record)
    finally:
        zenml_logger_module.step_names_in_console.reset(token)

    assert (
        "zenml.test:test_function:42 | [trainer] endpoint.completed"
        in formatted
    )
    assert formatted.endswith(' | {"request_id":"request-1","step":"trainer"}')
    assert record.getMessage() == "endpoint.completed"


def test_structured_console_logs_append_traceback_and_stack_info_after_extras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured logs append traceback and stack details after extras."""
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.DEBUG,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    try:
        raise ValueError("broken")
    except ValueError:
        record = _make_log_record(
            "endpoint.failed",
            level=logging.ERROR,
            request_id="request-1",
        )
        record.exc_info = sys.exc_info()
        record.stack_info = "Stack (most recent call last):\nstack line"

    formatted = ZenMLConsoleFormatter().format(record)

    # The primary log line should stay machine-parseable: extras remain attached
    # to that line and diagnostics are appended afterwards on separate lines.
    extras_index = formatted.index(' | {"request_id":"request-1"}')
    traceback_index = formatted.index("Traceback (most recent call last):")
    stack_index = formatted.index("Stack (most recent call last):")

    assert extras_index < traceback_index < stack_index
    assert "ValueError: broken" in formatted
    assert "stack line" in formatted


def test_extra_collision_with_reserved_key_raises() -> None:
    """Reserved stdlib log record fields cannot be overwritten by extras."""
    logger = get_logger("zenml.test.reserved")

    with pytest.raises(KeyError, match="Attempt to overwrite 'name'"):
        logger.info("collision", extra={"name": "bad"})


#########################################
# Compact Log Formatting for Client Logs
# And Custom Console Formatting
#########################################


def test_compact_console_logs_include_extras_for_client_info_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compact client console logs include extras and hide redundant step."""
    # Client INFO logs use the compact human layout. The active step is already
    # visible in ZenML's step boundary messages, so the formatter omits `step`
    # from the JSON extras unless step-name prefixes are explicitly enabled.
    monkeypatch.setenv(ENV_ZENML_SERVER, "false")
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    # disable colors so the formatted log can be asserted as plain text.
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")
    record = _make_log_record(
        "training.started",
        dataset="mnist",
        epochs=10,
        step="trainer",
    )

    formatted = ZenMLConsoleFormatter().format(record)

    assert formatted == 'training.started | {"dataset":"mnist","epochs":10}'
    assert "trainer" not in formatted
    assert "\x1b[" not in formatted


def test_compact_console_logs_prefix_step_name_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compact client logs prefix messages when step-name output is enabled."""
    monkeypatch.setenv(ENV_ZENML_SERVER, "false")
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")
    record = _make_log_record(
        "training.started",
        dataset="mnist",
        step="trainer",
    )
    token = zenml_logger_module.step_names_in_console.set(True)

    try:
        formatted = ZenMLConsoleFormatter().format(record)
    finally:
        zenml_logger_module.step_names_in_console.reset(token)

    assert formatted == '[trainer] training.started | {"dataset":"mnist"}'
    assert record.getMessage() == "training.started"


def test_custom_console_format_prefixes_step_name_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Custom human console formats preserve old step-prefix behavior."""
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")
    formatter = ZenMLConsoleFormatter(
        custom_log_format="%(message)s [%(levelname)s]"
    )
    record = _make_log_record("custom layout", step="trainer")
    token = zenml_logger_module.step_names_in_console.set(True)

    try:
        formatted = formatter.format(record)
    finally:
        zenml_logger_module.step_names_in_console.reset(token)

    assert formatted == "[trainer] custom layout [INFO]"
    assert record.getMessage() == "custom layout"


##################################
# Console Colors And Highlighting
##################################


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


#################################################
# Stdout/Stderr Wrapping And Step Name Prefixing
#################################################


def test_wrapped_stdout_stores_raw_message_without_step_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored stdout logs stay raw while terminal output gets the step prefix."""
    # `emitted_messages` captures what would be stored in the log store, while
    # `terminal_messages` captures what the user sees in stdout. The prefix is
    # useful in the terminal but would be redundant/noisy in stored logs.
    emitted_messages: list[str] = []
    terminal_messages: list[str] = []

    def emit(record: logging.LogRecord) -> None:
        emitted_messages.append(record.getMessage())

    def get_step_context() -> SimpleNamespace:
        return SimpleNamespace(step_name="trainer")

    monkeypatch.setattr(
        "zenml.utils.logging_utils.LoggingContext.dispatch", emit
    )
    monkeypatch.setattr("zenml.steps.get_step_context", get_step_context)
    token = zenml_logger_module.step_names_in_console.set(True)

    try:
        wrapped_write = zenml_logger_module._wrapped_write(
            terminal_messages.append, "stdout"
        )

        wrapped_write("hello\n")
    finally:
        zenml_logger_module.step_names_in_console.reset(token)

    assert emitted_messages == ["hello\n"]
    assert terminal_messages == ["[trainer] hello\n"]


@pytest.mark.parametrize(
    ("env_value", "expected_message"),
    [
        (None, "hello\n"),
        ("false", "[trainer] hello\n"),
        ("true", "hello\n"),
    ],
)
def test_logging_context_step_name_prefix_uses_legacy_env_semantics(
    monkeypatch: pytest.MonkeyPatch,
    env_value: str | None,
    expected_message: str,
) -> None:
    """Step prefixes are hidden by default and shown when disabled is false."""
    from zenml.utils import logging_utils

    # LoggingContext gets the log store from Client().active_stack and
    # registers an origin before stdout/stderr writes can be emitted. This
    # fake keeps the test focused on console-prefix behavior without
    # involving the real client, stack, or log storage backend.
    class FakeLogStore:
        def register_origin(
            self,
            name: str,
            log_model: SimpleNamespace,
            metadata: dict[str, Any],
        ) -> object:
            return object()

        def deregister_origin(
            self, origin: object, blocking: bool = True
        ) -> None:
            pass

        def emit(
            self,
            origin: object,
            record: logging.LogRecord,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            pass

    # The production prefixing code discovers the active pipeline step
    # dynamically, so the test provides a stable step context instead of
    # constructing a real pipeline run.
    def get_step_context() -> SimpleNamespace:
        return SimpleNamespace(step_name="trainer")

    # Exercise the legacy env-var contract: unset and "true" hide step
    # prefixes, while "false" opts into showing them in console output.
    if env_value is None:
        monkeypatch.delenv(ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS, raising=False)
    else:
        monkeypatch.setenv(ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS, env_value)
    monkeypatch.setenv(ENV_ZENML_LOGGING_COLORS_DISABLED, "true")

    # CI may run tests with ZENML_DEBUG=1. Pin INFO formatting so this test
    # verifies step-prefix semantics, not the DEBUG structured-log layout.
    monkeypatch.setattr(
        zenml_logger_module,
        "get_logging_level",
        lambda: LoggingLevels.INFO,
    )

    # `terminal_messages` represents the text written to the user-visible
    # stdout stream. It is intentionally separate from the log record emitted to
    # the log store because step prefixes should only affect console output.
    terminal_messages: list[str] = []
    console_record = _make_log_record("training.started", step="trainer")
    fake_client = SimpleNamespace(
        active_stack=SimpleNamespace(log_store=FakeLogStore())
    )
    monkeypatch.setattr(logging_utils, "Client", lambda: fake_client)
    monkeypatch.setattr("zenml.steps.get_step_context", get_step_context)

    with logging_utils.LoggingContext(
        name="test", log_model=cast(Any, SimpleNamespace(id="logs-id"))
    ):
        # Entering LoggingContext enables the same stdout wrapper behavior used
        # during step execution: writes are emitted to the log store and then
        # forwarded to the terminal, optionally with a step prefix.
        wrapped_write = zenml_logger_module._wrapped_write(
            terminal_messages.append, "stdout"
        )

        wrapped_write("hello\n")
        console_message = ZenMLConsoleFormatter().format(console_record)

    # The wrapped stdout path controls raw terminal writes like `print()`.
    assert terminal_messages == [expected_message]

    # The formatter path controls stdlib logger messages. It should follow the
    # same env-var prefix contract while preserving the original LogRecord.
    assert console_message == expected_message.replace(
        "hello\n", "training.started"
    )
    assert console_record.getMessage() == "training.started"


###########################
# Context Variable Logging
###########################


def test_contextvars_filter_copies_bound_context_to_log_record() -> None:
    """Bound logging context is copied onto standard library log records."""
    # Bind the request context.
    bind_log_context(clear=True, request_id="request-1", method="GET")
    record = _make_log_record("request.received")

    # Call the contextvars filter to copy the contextvars onto the log record.
    zenml_logger_module._ContextVarsFilter().filter(record)

    # Assert the contextvars are copied onto the log record.
    assert getattr(record, "request_id") == "request-1"
    assert getattr(record, "method") == "GET"


def test_contextvars_filter_preserves_existing_log_record_fields() -> None:
    """Test _ContextVarsFilter copies contextvars onto log record but preserves existing fields."""
    bind_log_context(clear=True, request_id="bound-request", method="GET")
    # Explicit LogRecord fields should win over bound context. This lets a
    # caller override request-level defaults for a single log line.
    record = _make_log_record("request.received", request_id="record-request")

    zenml_logger_module._ContextVarsFilter().filter(record)

    assert getattr(record, "request_id") == "record-request"
    assert getattr(record, "method") == "GET"


def test_step_name_filter_copies_active_step_to_log_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The active step name is copied onto standard library log records."""

    def get_step_context() -> SimpleNamespace:
        return SimpleNamespace(step_name="trainer")

    monkeypatch.setattr("zenml.steps.get_step_context", get_step_context)
    record = _make_log_record("training.started")

    assert zenml_logger_module._StepNameFilter().filter(record)
    assert getattr(record, "step") == "trainer"


def test_step_name_filter_tolerates_step_context_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Step-name enrichment is best-effort and never filters records out."""

    def get_step_context() -> SimpleNamespace:
        raise RuntimeError("step context unavailable")

    monkeypatch.setattr("zenml.steps.get_step_context", get_step_context)
    record = _make_log_record("training.started")

    assert zenml_logger_module._StepNameFilter().filter(record)
    assert not hasattr(record, "step")


def test_logging_scope_restores_outer_context() -> None:
    """Scoped logging context is removed after leaving the scope."""
    bind_log_context(clear=True, request_id="request-1")

    with logging_context(transaction_id="transaction-1"):
        assert get_logging_context() == {
            "request_id": "request-1",
            "transaction_id": "transaction-1",
        }

    assert get_logging_context() == {"request_id": "request-1"}
