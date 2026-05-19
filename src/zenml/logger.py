#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""Logger Implementation."""

import json
import logging
import os
import re
import sys
import traceback
from contextlib import contextmanager
from typing import Any, Generator, Optional

import structlog
from rich.traceback import install as rich_tb_install

from zenml.constants import (
    ENABLE_RICH_TRACEBACK,
    ENV_ZENML_LOGGING_COLORS_DISABLED,
    ENV_ZENML_LOGGING_FORMAT,
    ENV_ZENML_SERVER,
    ENV_ZENML_SUPPRESS_LOGS,
    ZENML_LOGGING_VERBOSITY,
    ZENML_STORAGE_LOGGING_VERBOSITY,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels

ZENML_LOGGING_COLORS_DISABLED = handle_bool_env_var(
    ENV_ZENML_LOGGING_COLORS_DISABLED, False
)

_original_stdout_write: Optional[Any] = None
_original_stderr_write: Optional[Any] = None
_stdout_wrapped: bool = False
_stderr_wrapped: bool = False


class _ZenMLStdoutStream:
    """Stream that writes to the original stdout, bypassing the ZenML wrapper.

    This ensures console logging doesn't trigger the LoggingContext wrapper,
    preventing duplicate log entries in stored logs.
    """

    def write(self, text: str) -> Any:
        """Write text to the original stdout.

        Args:
            text: The text to write.

        Returns:
            The number of characters written.
        """
        if _original_stdout_write:
            return _original_stdout_write(text)
        return sys.stdout.write(text)

    def flush(self) -> None:
        """Flush the stdout buffer."""
        sys.stdout.flush()


def get_logger(logger_name: str) -> logging.Logger:
    """Returns a stdlib logger by name.

    To attach structured fields to a log record,
    use the stdlib pattern:

        ``logger.info("event", extra={"key": "value"})``
    """
    return logging.getLogger(logger_name)


def bind_request_context(**fields: Any) -> None:
    """Bind extra context variables to the current logging context.

    Use it to propagate common context variables to every downstream
    log record. The extra context persists until the current logging
    context is cleared.

    E.g.: This can be used at request boundaries to propagate context
    like request_id, method, path, etc. to all log records in a request.

    Any previously bound contextvars are cleared first, so this sets a
    fresh set of context variables to the current logging context.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**fields)


@contextmanager
def logging_scope(**fields: Any) -> Generator[None, None, None]:
    """Bind extra context to a specific set of log records.

    Use this for narrow scopes inside a request (e.g. a single transaction,
    a step execution, a retry attempt) where you want a few fields to
    propagate to certain downstream log records within a scope.

    E.g.::

        with logging_scope(transaction_id=tx_id, attempt=2):
            logger.info("retrying transaction")
            do_something()
            logger.info("transaction attempt succeeded")

        This will propagate extra context (on top of the context bound by
        `bind_request_context`) to the log records emitted within the scope.
    """
    with structlog.contextvars.bound_contextvars(**fields):
        yield


def get_logging_context() -> dict[str, Any]:
    """Return a snapshot of the currently bound logging context.

    Returns a fresh dict (safe to mutate) with all the context
    variables bound via ``bind_request_context`` or ``logging_scope``.

    Useful at response/error boundaries that need to surface a single field
    (typically ``request_id``) back to the caller.
    """
    return dict(structlog.contextvars.get_contextvars())


# Stdlib LogRecord attributes plus our derived ones — never rendered
# as "extras". Kept in sync with
# https://docs.python.org/3/library/logging.html#logrecord-attributes
_RESERVED_LOG_RECORD_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class ZenMLConsoleFormatter(logging.Formatter):
    """Stdlib console formatter for all ZenML console output.

    Client Side:
      * ``INFO+``: bare log message with level coloring and backtick / URL highlights.
      * ``DEBUG+``: structured log format

    Server Side:
      * Always: structured log format.
        Decides based on whether ``ENV_ZENML_SERVER`` is set to True.
    """

    # log format:
    # <time> | <loglevel> | <name>:<funcName>:<lineno> | <message> | <extras as JSON, if any> \n [traceback if any]
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"

    _RESET = "\x1b[0m"
    _GREY = "\x1b[90m"
    _WHITE = "\x1b[37m"
    _YELLOW = "\x1b[33m"
    _RED = "\x1b[31m"
    _BOLD_RED = "\x1b[31;1m"
    _PURPLE = "\x1b[38;5;105m"
    _BLUE = "\x1b[34m"

    _LEVEL_COLORS: dict[int, str] = {
        logging.DEBUG: _GREY,
        logging.INFO: _WHITE,
        logging.WARNING: _YELLOW,
        logging.ERROR: _RED,
        logging.CRITICAL: _BOLD_RED,
    }

    _BACKTICK_PATTERN = r"`([^`]*)`"
    _URL_PATTERN = r"https?://[^\s)\"'>]+"

    def __init__(self) -> None:
        """Initialize the formatter."""
        super().__init__(fmt=self.LOG_FORMAT)

        # The ENV_ZENML_SERVER env var is set to True when the ZenML
        # server is running. By default, if the env var is not set,
        # it get initialized at import time.
        # src/zenml/zen_server/utils.py: initialize_zen_store()
        # sets it later during FastAPI startup. Once set, the value
        # never changes.
        self._is_server: Optional[bool] = None

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record.

        Args:
            record: The log record to render.

        Returns:
            The fully formatted line.
        """
        # Show structured log format in the console
        # always on server side, and for client at DEBUG+ log level.
        if self._use_structured_log():
            return self._format_structured_log(record)

        # Show bare log message for client at INFO+ log level.
        return self._format_log_message(record)

    def _use_structured_log(self) -> bool:
        """Check whether to use structured log format in the console.

        Structured log is shown always on server side, and for client at DEBUG+ log level.

        Returns:
            True for structured pipe layout, False for bare messages.
        """
        # Only cache once True — before initialize_zen_store() runs
        # the env var isn't set yet, so we must keep re-checking.
        if self._is_server is None:
            if handle_bool_env_var(ENV_ZENML_SERVER, False):
                self._is_server = True

        # On server side, always show structured log.
        if self._is_server:
            return True

        # If the log level is DEBUG, show structured log.
        return get_logging_level() == LoggingLevels.DEBUG

    def _format_log_message(self, record: logging.LogRecord) -> str:
        """Bare log message with level coloring and highlights.

        Args:
            record: The log record to render.

        Returns:
            Formatted log message string.
        """
        message = record.getMessage()

        # Format the traceback text separately to avoid colorizing the traceback text.
        traceback_text = ""
        if record.exc_info:
            traceback_text = "\n" + self.formatException(record.exc_info)

        # Return the message and traceback text if colors are disabled.
        if ZENML_LOGGING_COLORS_DISABLED:
            return message + traceback_text

        # Colorize the level and highlights.
        level_color = self._LEVEL_COLORS.get(record.levelno, "")
        colored_message = f"{level_color}{message}{self._RESET}"
        colored_message = self._colorize_highlights(
            colored_message, level_color
        )

        # Return the colored message and plain traceback text.
        return colored_message + traceback_text

    def _format_structured_log(self, record: logging.LogRecord) -> str:
        """Uses LOG_FORMAT to format the log record. DEBUG logs are greyed out.

        Args:
            record: The log record to render.

        Returns:
            Fully formatted line.
        """
        # log format:
        # <time> | <loglevel> | <name>:<funcName>:<lineno> | <message> | <extras as JSON, if any> \n [traceback if any]

        # Format without traceback first so we can append extras before the traceback.
        exc_info_backup = record.exc_info
        exc_text_backup = record.exc_text
        record.exc_info = None
        record.exc_text = None

        formatted_log = super().format(record)

        # Restore exc_info and exc_text.
        record.exc_info = exc_info_backup
        record.exc_text = exc_text_backup

        extras = self._collect_extras(record)
        extras_text = ""
        if extras:
            extras_text = " | {}".format(
                json.dumps(extras, default=str, separators=(",", ":"))
            )

        traceback_text = ""
        if record.exc_info:
            traceback_text = "\n{}".format(
                self.formatException(record.exc_info)
            )

        if ZENML_LOGGING_COLORS_DISABLED:
            return formatted_log + extras_text + traceback_text

        if extras_text:
            # Always grey out extras.
            extras_text = f"{self._GREY}{extras_text}{self._RESET}"

        # Grey out DEBUG logs.
        is_debug = record.levelno == logging.DEBUG
        if is_debug:
            formatted_log = f"{self._GREY}{formatted_log}{self._RESET}"
            formatted_log = self._colorize_highlights(
                formatted_log, self._GREY
            )
            if traceback_text:
                traceback_text = (
                    f"\n{self._GREY}{traceback_text.lstrip()}{self._RESET}"
                )
            return formatted_log + extras_text + traceback_text

        # Colorize the log message based on log level.
        level_color = self._LEVEL_COLORS.get(record.levelno, "")
        formatted_log = f"{level_color}{formatted_log}{self._RESET}"

        # Colorize highlights - backtick-quoted text and URLs.
        formatted_log = self._colorize_highlights(formatted_log, level_color)
        return formatted_log + self._RESET + extras_text + traceback_text

    @classmethod
    def _collect_extras(cls, record: logging.LogRecord) -> dict[str, Any]:
        """Extract structured fields that aren't stdlib LogRecord attrs.

        Args:
            record: The log record whose ``__dict__`` we mine.

        Returns:
            Mapping of extra-field name to value.
        """
        return {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED_LOG_RECORD_ATTRS and not k.startswith("_")
        }

    @classmethod
    def _colorize_highlights(cls, text: str, base_color: str) -> str:
        """Highlight backtick-quoted text in purple and URLs in blue."""
        for quoted in re.findall(cls._BACKTICK_PATTERN, text):
            text = text.replace(
                "`" + quoted + "`",
                cls._RESET + cls._PURPLE + quoted + base_color,
            )
        for url in re.findall(cls._URL_PATTERN, text):
            text = text.replace(
                url,
                cls._RESET + cls._BLUE + url + base_color,
            )
        return text


class ZenMLJsonFormatter(logging.Formatter):
    """Format a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        """Render ``record`` as a single-line JSON object.

        Args:
            record: The log record to render.

        Returns:
            A JSON string (no trailing newline; the handler adds one).
        """
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        for k, v in record.__dict__.items():
            # Skip stdlib internals, duplicates, and private attributes.
            if (
                k in _RESERVED_LOG_RECORD_ATTRS
                or k in payload
                or k.startswith("_")
            ):
                continue
            payload[k] = v

        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "stacktrace": "".join(
                    traceback.format_exception(
                        exc_type, exc_value, exc_traceback
                    )
                ),
            }

        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(payload, default=str, separators=(",", ":"))


def _is_json_format() -> bool:
    """Decide whether to emit JSON or console output.

    Returns:
        True when the output format should be JSON.
    """
    fmt = os.environ.get(ENV_ZENML_LOGGING_FORMAT, "").lower()
    if fmt == "json":
        return True

    # Default to console output
    return False


def _select_console_formatter() -> logging.Formatter:
    """Return a JSON or console formatter based on ``ZENML_LOGGING_FORMAT`` env var. Default is console.

    Returns:
        The formatter to attach to the console handler.

    """
    # Return a JSON formatter if the env var is set to "json" or if the server is running.
    if _is_json_format():
        return ZenMLJsonFormatter()

    # Return a console formatter if the env var is set to "console" or for the client.
    return ZenMLConsoleFormatter()


def get_logging_level() -> LoggingLevels:
    """Get logging level from the env variable.

    Returns:
        The logging level.

    Raises:
        KeyError: If the logging level is not found.
    """
    verbosity = ZENML_LOGGING_VERBOSITY.upper()
    if verbosity not in LoggingLevels.__members__:
        raise KeyError(
            f"Verbosity must be one of {list(LoggingLevels.__members__.keys())}"
        )

    if ZENML_STORAGE_LOGGING_VERBOSITY is not None:
        get_logger(__name__).warning(
            "The ZENML_STORAGE_LOGGING_VERBOSITY is no longer supported. "
            "Please use the ZENML_LOGGING_VERBOSITY instead."
        )

    return LoggingLevels[verbosity]


def set_root_verbosity() -> LoggingLevels:
    """Set the root verbosity.

    Returns:
        The active logging level.
    """
    level = get_logging_level()
    if level != LoggingLevels.NOTSET:
        if ENABLE_RICH_TRACEBACK:
            rich_tb_install(show_locals=(level == LoggingLevels.DEBUG))

        logging.root.setLevel(level=level.value)
        logging.getLogger(__name__).debug(
            f"Logging set to level: {logging.getLevelName(level.value)}"
        )
    else:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True
        logging.getLogger(__name__).debug("Logging NOTSET")

    return level


def _wrapped_write(original_write: Any, stream_name: str) -> Any:
    """Wrap stdout/stderr write method to route logs to LoggingContext.

    Args:
        original_write: The original write method.
        stream_name: The name of the stream.

    Returns:
        The wrapped write method.
    """

    def wrapped_write(text: str) -> Any:
        """Write method that routes logs through LoggingContext.

        Args:
            text: The text to write.

        Returns:
            The result of the original write method.
        """
        from zenml.utils.logging_utils import LoggingContext

        level = logging.INFO if stream_name == "stdout" else logging.ERROR

        if logging.root.isEnabledFor(level):
            record = logging.LogRecord(
                name=stream_name,
                level=level,
                pathname="",
                lineno=0,
                msg=text,
                args=(),
                exc_info=None,
                func="",
            )
            LoggingContext.emit(record)

        return original_write(text)

    return wrapped_write


def wrap_stdout_stderr() -> None:
    """Wrap stdout and stderr write methods to route through LoggingContext."""
    global _stdout_wrapped, _stderr_wrapped
    global _original_stdout_write, _original_stderr_write

    if not _stdout_wrapped:
        _original_stdout_write = getattr(sys.stdout, "write")
        setattr(
            sys.stdout,
            "write",
            _wrapped_write(_original_stdout_write, "stdout"),
        )
        _stdout_wrapped = True

    if not _stderr_wrapped:
        _original_stderr_write = getattr(sys.stderr, "write")
        setattr(
            sys.stderr,
            "write",
            _wrapped_write(_original_stderr_write, "stderr"),
        )
        _stderr_wrapped = True


class ZenMLLoggingHandler(logging.Handler):
    """Custom handler that routes logs through LoggingContext."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record through LoggingContext.

        Args:
            record: The log record to emit.
        """
        from zenml.utils.logging_utils import LoggingContext

        LoggingContext.emit(record)


class ZenMLConsoleHandler(logging.StreamHandler[Any]):
    """Console handler owned by the ZenML logging setup."""


class _StepNameFilter(logging.Filter):
    """Inject pipeline step name into the log record when available."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Set ``record.step`` to the active step name when available.

        Args:
            record: The log record to enrich.

        Returns:
            Always True (never filters records out).
        """
        try:
            from zenml.steps import get_step_context

            step_context = get_step_context()
            if step_context is not None:
                record.step = step_context.step_name
        except Exception:
            pass
        return True


class _ContextVarsFilter(logging.Filter):
    """Copy structlog contextvars onto every log record.

    If the attribute already exists, it is left untouched.

    This bridges the gap between the structlog contextvars and the log
    record. Without this filter, the structlog contextvars would not be
    available to the log record and neither the formatter nor the OTel handler
    would be able to access them.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich a LogRecord with structlog contextvars.

        Args:
            record: The log record to enrich.

        Returns:
            Always True (never filters out records).
        """
        ctx = structlog.contextvars.get_contextvars()
        for key, value in ctx.items():
            # Set the attribute on the log record if it doesn't already exist
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


def add_zenml_filters(handler: logging.Handler) -> logging.Handler:
    """Add filters to logging handler to attach structlog contextvars and step name to the log record.

    Args:
        handler: The logging handler to enrich.

    Returns:
        The same handler, with the filters attached.
    """
    # Copies bound contextvars (request_id, method, etc.) onto each LogRecord
    handler.addFilter(_ContextVarsFilter())
    # Injects step name onto LogRecords emitted during step execution
    handler.addFilter(_StepNameFilter())
    return handler


def get_console_handler() -> logging.Handler:
    """Get console handler that writes to stdout and is configured with ZenML formatter and filters."""
    handler = ZenMLConsoleHandler(_ZenMLStdoutStream())
    handler.setFormatter(_select_console_formatter())
    return add_zenml_filters(handler)


def get_zenml_handler() -> logging.Handler:
    """Get ZenML handler that routes logs through LoggingContext."""
    handler = ZenMLLoggingHandler()
    return add_zenml_filters(handler)


def _remove_zenml_handlers(root_logger: logging.Logger) -> None:
    """Remove handlers owned by the ZenML logging setup."""
    for handler in root_logger.handlers[:]:
        if isinstance(handler, (ZenMLConsoleHandler, ZenMLLoggingHandler)):
            root_logger.removeHandler(handler)
            handler.close()


def init_logging() -> None:
    """Initialize the ZenML logging system."""
    level = set_root_verbosity()

    # If the root verbosity is NOTSET, return early.
    if level == LoggingLevels.NOTSET:
        return

    root_logger = logging.getLogger()

    # Clear existing ZenML handlers to avoid duplicates
    _remove_zenml_handlers(root_logger)

    # Add new ZenML handlers to the root logger
    root_logger.addHandler(get_console_handler())
    root_logger.addHandler(get_zenml_handler())

    # Wraps stdout/stderr after handlers are attached so the
    # wrapped writes flow through a fully configured pipeline.
    wrap_stdout_stderr()

    # Mute tensorflow cuda warnings
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    # logging capture warnings
    logging.captureWarnings(True)

    # Enable logs if environment variable SUPPRESS_ZENML_LOGS is not set to True
    suppress_zenml_logs: bool = handle_bool_env_var(
        ENV_ZENML_SUPPRESS_LOGS, True
    )
    if suppress_zenml_logs:
        # suppress logger info messages
        suppressed_logger_names = [
            "urllib3",
            "azure.core.pipeline.policies.http_logging_policy",
            "grpc",
            "requests",
            "kfp",
            "tensorflow",
        ]
        for logger_name in suppressed_logger_names:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

        # disable logger messages
        disabled_logger_names = [
            "rdbms_metadata_access_object",
            "backoff",
            "segment",
        ]
        for logger_name in disabled_logger_names:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
            logging.getLogger(logger_name).disabled = True
