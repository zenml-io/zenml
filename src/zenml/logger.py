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
from contextvars import ContextVar
from typing import Any, Generator, Optional

import structlog
from rich.traceback import install as rich_tb_install

from zenml.constants import (
    ENABLE_RICH_TRACEBACK,
    ENV_ZENML_CONSOLE_LOGGING_FORMAT,
    ENV_ZENML_LOGGING_COLORS_DISABLED,
    ENV_ZENML_LOGGING_FORMAT,
    ENV_ZENML_SERVER,
    ENV_ZENML_SUPPRESS_LOGS,
    ZENML_LOGGING_VERBOSITY,
    ZENML_STORAGE_LOGGING_VERBOSITY,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels

#####################################
# Constants / Module State Variables
#####################################

_original_stdout_write: Optional[Any] = None
_original_stderr_write: Optional[Any] = None
_stdout_wrapped: bool = False
_stderr_wrapped: bool = False
step_names_in_console: ContextVar[bool] = ContextVar(
    "step_names_in_console", default=False
)

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

#####################
# Public Logging API
#####################


def get_logger(logger_name: str) -> logging.Logger:
    """Returns a stdlib logger by name.

    To attach structured fields to a log record,
    use the stdlib pattern:

        ``logger.info("event", extra={"key": "value"})``
    """
    return logging.getLogger(logger_name)


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


def bind_log_context(*, clear: bool = False, **fields: Any) -> None:
    """Bind fields to the active logging context.

    Use it to propagate common context variables to every downstream
    log record. The extra context persists until the current logging
    context is cleared.

    E.g.: This can be used at request boundaries to propagate context
    like request_id, method, path, etc. to all log records in a request.

    Set ``clear=True`` at request boundaries to avoid leaking context from
    previous requests.

    Args:
        clear: Whether to clear the active context before binding fields.
        **fields: Context fields to bind to the active log context.
    """
    if clear:
        clear_log_context()

    structlog.contextvars.bind_contextvars(**fields)


def clear_log_context() -> None:
    """Clear structured context bound to the active request."""
    structlog.contextvars.clear_contextvars()


@contextmanager
def logging_context(**fields: Any) -> Generator[None, None, None]:
    """Bind extra context to a specific set of log records.

    Use this for narrow scopes inside a request (e.g. a single transaction,
    a step execution, a retry attempt) where you want a few fields to
    propagate to certain downstream log records within a scope.

    E.g.::

        with logging_context(transaction_id=tx_id, attempt=2):
            logger.info("retrying transaction")
            do_something()
            logger.info("transaction attempt succeeded")

        This will propagate extra context (on top of the context bound by
        `bind_log_context`) to the log records emitted within the scope.
    """
    with structlog.contextvars.bound_contextvars(**fields):
        yield


def get_logging_context() -> dict[str, Any]:
    """Return a snapshot of the currently bound logging context.

    Returns a fresh dict (safe to mutate) with all the context
    variables bound via ``bind_log_context`` or ``logging_context``.

    Useful at response/error boundaries that need to surface a single field
    (typically ``request_id``) back to the caller.
    """
    return dict(structlog.contextvars.get_contextvars())


def _collect_extra_fields(
    record: logging.LogRecord,
    exclude_attrs: Optional[set[str]] = None,
) -> dict[str, Any]:
    """Extract structured fields that aren't stdlib LogRecord attrs.

    Args:
        record: The log record whose ``__dict__`` we mine.
        exclude_attrs: Extra attributes to skip, if any.

    Returns:
        Mapping of extra-field name to value.
    """
    exclude_attrs = exclude_attrs or set()
    return {
        k: v
        for k, v in record.__dict__.items()
        if k not in _RESERVED_LOG_RECORD_ATTRS
        and not k.startswith("_")
        and k not in exclude_attrs
    }


class ZenMLConsoleFormatter(logging.Formatter):
    """Stdlib console formatter for all ZenML console output.

    Custom format:
      * User-provided Python `%`-style format string.

    Client Side:
      * ``INFO+`` default: bare log message with extras and highlights.
      * ``DEBUG`` default: structured log format with full context.

    Server Side:
      * Always: structured log format.
        Decides based on whether ``ENV_ZENML_SERVER`` is set to True.
    """

    # Structured log format:
    # <time> | <loglevel> | <name>:<funcName>:<lineno> | <message> | <extras as JSON, if any>
    # [traceback if any in a new line]
    #
    # This format is used for default server logs and client DEBUG logs.
    # Client INFO logs use a compact layout. A custom log format takes
    # precedence for both client and server console output.
    _LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"

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

    _BACKTICK_PATTERN = re.compile(r"`([^`]*)`")
    _URL_PATTERN = re.compile(r"https?://[^\s)\"'>]+")

    def __init__(self, custom_log_format: Optional[str] = None) -> None:
        """Initialize the formatter."""
        super().__init__(fmt=custom_log_format or self._LOG_FORMAT)
        self._custom_log_format = custom_log_format

        # disable colors if the env var is set to true
        self._colors_disabled = handle_bool_env_var(
            ENV_ZENML_LOGGING_COLORS_DISABLED, False
        )

        # using this var, we determine if the log record should be formatted
        # for ZenML server or client.
        self._is_zenml_server: Optional[bool] = None

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record.

        Args:
            record: The log record to render.

        Returns:
            The fully formatted line.
        """
        if self._custom_log_format:
            return self._format_custom_log_format(record)

        # For ZenML server logs, always format logs with default LOG_FORMAT layout.
        if self._use_zenml_server_layout():
            return self._format_structured_console_log(record)

        # If client has not set any custom log format:
        # - for DEBUG logs, use default structured layout
        # - for INFO+ logs, use compact layout
        if get_logging_level() == LoggingLevels.DEBUG:
            return self._format_structured_console_log(record)

        return self._format_compact_client_log(record)

    def _use_zenml_server_layout(self) -> bool:
        """Check whether the record should use the server log layout(LOG_FORMAT).

        The ZenML server sets ``ENV_ZENML_SERVER`` during FastAPI startup, so
        the first formatter call can happen before the env var is available.
        src/zenml/zen_server/utils.py: initialize_zen_store() sets the env var
        during FastAPI app initialization.

        Cache only the positive result and keep re-checking until then.

        Returns:
            True if the server log layout should be used.
        """
        # Only cache once True — before initialize_zen_store() runs
        # the env var isn't set yet, so we must keep re-checking.
        if self._is_zenml_server is None:
            if handle_bool_env_var(ENV_ZENML_SERVER, False):
                self._is_zenml_server = True

        return bool(self._is_zenml_server)

    def _format_custom_log_format(self, record: logging.LogRecord) -> str:
        """Format a record with a user-provided console format."""
        return self._format_with_step_prefix_in_message(record)

    def _format_compact_client_log(self, record: logging.LogRecord) -> str:
        """Format default client INFO logs with a compact layout.

        Log format:
        <message> | <extras as JSON, if any> \n [traceback and stack_info if any]

        Args:
            record: The log record to render.

        Returns:
            Formatted log message string.
        """
        message = record.getMessage()
        if self._should_prefix_step_name(record):
            message = _prefix_step_name(message, str(getattr(record, "step")))

        # Client INFO logs (ZENML_LOGGING_VERBOSITY=INFO) already show step
        # boundaries in ZenML's console messages, so repeating the injected step
        # name in extras adds noise. So we exclude the step attribute from the
        # extras dict in the formatted log message.
        extras_text = self._format_extra_fields(record, exclude_attrs={"step"})

        traceback_text = self._format_traceback_and_stack_info(record)

        # Return the message and traceback text if colors are disabled.
        if self._colors_disabled:
            return message + extras_text + traceback_text

        # Colorize the level and highlights.
        level_color = self._LEVEL_COLORS.get(record.levelno, "")
        colored_message = f"{level_color}{message}{self._RESET}"
        colored_message = self._highlight_message_tokens(
            colored_message, level_color
        )

        # Return the colored message and plain traceback text.
        return colored_message + extras_text + traceback_text

    def _format_structured_console_log(self, record: logging.LogRecord) -> str:
        """Format a record with the structured ``LOG_FORMAT`` layout.

        Args:
            record: The log record to render.

        Returns:
            Fully formatted line.
        """
        # log format:
        # <time> | <loglevel> | <name>:<funcName>:<lineno> | <message> | <extras as JSON, if any>
        # [traceback if present in a new line]

        # Format without traceback/stack info first so extras stay attached to
        # the primary log line and diagnostic details are always appended last.
        exc_info_backup = record.exc_info
        exc_text_backup = record.exc_text
        stack_info_backup = record.stack_info
        try:
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
            formatted_log = self._format_with_step_prefix_in_message(record)
        finally:
            # Restore diagnostic fields for explicit formatting below.
            record.exc_info = exc_info_backup
            record.exc_text = exc_text_backup
            record.stack_info = stack_info_backup

        # If present, get extras dict from log record and format it.
        extras_text = self._format_extra_fields(record)

        traceback_text = self._format_traceback_and_stack_info(record)

        # If colors are disabled, return the formatted log message with extras and traceback.
        if self._colors_disabled:
            return formatted_log + extras_text + traceback_text

        # Colorize the log message based on log level.
        level_color = self._LEVEL_COLORS.get(record.levelno, "")
        formatted_log = f"{level_color}{formatted_log}{self._RESET}"

        # Colorize highlights - backtick-quoted text and URLs.
        formatted_log = self._highlight_message_tokens(
            formatted_log, level_color
        )

        return formatted_log + extras_text + traceback_text

    def _format_with_step_prefix_in_message(
        self, record: logging.LogRecord
    ) -> str:
        """Format a record with the step prefix folded into its message, if enabled."""
        if not self._should_prefix_step_name(record):
            return super().format(record)

        # The step prefix is only for console/stdout rendering. We temporarily
        # fold it into the LogRecord message so custom `%(message)s` layouts
        # keep the prefix in the message position, then restore the original
        # record for other handlers.
        #
        # `args` belongs to stdlib's lazy message interpolation (`msg % args`):
        # `logger.info("Sleeping for %s seconds", 10)` stores
        # `msg="Sleeping for %s seconds"` and `args=(10,)`. Once we replace
        # `msg` with the already-rendered prefixed string, `args` must be
        # cleared during formatting and restored afterwards because Formatter
        # calls `getMessage()` again and would otherwise re-apply the old args.
        msg_backup = record.msg
        args_backup = record.args
        try:
            record.msg = _prefix_step_name(
                record.getMessage(), str(getattr(record, "step"))
            )
            record.args = ()
            return super().format(record)
        finally:
            record.msg = msg_backup
            record.args = args_backup

    @staticmethod
    def _should_prefix_step_name(record: logging.LogRecord) -> bool:
        """Check whether the console message should include pipeline step name prefix."""
        # Only add step prefix if step names are enabled in console and the
        # log record has a step name.
        return step_names_in_console.get() and bool(
            getattr(record, "step", None)
        )

    def _format_extra_fields(
        self,
        record: logging.LogRecord,
        exclude_attrs: Optional[set[str]] = None,
    ) -> str:
        """Format structured fields attached to a log record."""
        extras = _collect_extra_fields(record, exclude_attrs=exclude_attrs)

        if not extras:
            return ""

        extras_text = " | {}".format(
            json.dumps(extras, default=str, separators=(",", ":"))
        )
        # If colors are enabled, grey out the extras.
        if not self._colors_disabled:
            return f"{self._GREY}{extras_text}{self._RESET}"

        return extras_text

    def _format_traceback_and_stack_info(
        self, record: logging.LogRecord
    ) -> str:
        """Format traceback and stack info, if present."""
        if not record.exc_info and not record.stack_info:
            return ""

        traceback_parts = []
        if record.exc_info:
            traceback_parts.append(self.formatException(record.exc_info))
        if record.stack_info:
            traceback_parts.append(self.formatStack(record.stack_info))

        traceback_text = "\n".join(traceback_parts)

        # For DEBUG logs, if colors are enabled,
        # grey out the traceback text, if present for better readability.
        if not self._colors_disabled and record.levelno == logging.DEBUG:
            traceback_text = (
                f"{self._GREY}{traceback_text.lstrip()}{self._RESET}"
            )

        return f"\n{traceback_text}"

    @classmethod
    def _highlight_message_tokens(cls, text: str, base_color: str) -> str:
        """Highlight backtick-quoted text in purple and URLs in blue."""
        for quoted in cls._BACKTICK_PATTERN.findall(text):
            text = text.replace(
                "`" + quoted + "`",
                cls._RESET + cls._PURPLE + quoted + base_color,
            )
        for url in cls._URL_PATTERN.findall(text):
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

        payload.update(
            _collect_extra_fields(record, exclude_attrs=set(payload))
        )

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


def _get_console_logging_format() -> Optional[str]:
    """Get the configured client console logging format."""
    # ZENML_CONSOLE_LOGGING_FORMAT takes precedence over older deprecated ZENML_LOGGING_FORMAT.
    log_format = os.environ.get(
        ENV_ZENML_CONSOLE_LOGGING_FORMAT
    ) or os.environ.get(ENV_ZENML_LOGGING_FORMAT)

    # If no log format is provided, return None.
    # Both Client and Server would default to structured layout.
    if not log_format:
        return None

    # For "json" or "console", return the format directly.
    if log_format.lower() in {"json", "console"}:
        return log_format.lower()

    # Validate if client provided log format is a valid Python logging
    # format string in %-style format. If not, return None
    try:
        logging.Formatter(log_format, validate=True)
    except ValueError:
        get_logger(__name__).warning(
            "Invalid console logging format: %s. Defaulting to console formatter. "
            "Please use a valid Python logging format string in %%-style format.",
            log_format,
        )
        return None

    return log_format


def _select_console_formatter() -> logging.Formatter:
    """Return the configured formatter for terminal output.

    Returns:
        The formatter to attach to the console handler.
    """
    fmt = _get_console_logging_format()

    if fmt == "json":
        return ZenMLJsonFormatter()

    # If no log format is provided, default to console.
    if fmt in (None, "console"):
        return ZenMLConsoleFormatter()

    # If any other valid Python `%`-style logging format string, use it.
    return ZenMLConsoleFormatter(custom_log_format=fmt)


######################
# Step prefix helpers
######################


def _add_step_name_to_message(message: str) -> str:
    """Adds the step name to the message.

    Args:
        message: The message to add the step name to.

    Returns:
        The message with the step name added.
    """
    try:
        if step_names_in_console.get():
            from zenml.steps import get_step_context

            step_context = get_step_context()

            if step_context and message not in ["\n", ""]:
                message = _prefix_step_name(message, step_context.step_name)
    except Exception:
        pass

    return message


def _prefix_step_name(message: str, step_name: str) -> str:
    """Prefix a console/stdout message with the active step name."""
    # Console writes can arrive as blank chunks; prefixing those would turn
    # empty lines into visible "[step]" noise.
    if message in ["\n", ""]:
        return message

    # Progress bars and status updates often use carriage returns to redraw the
    # same line, so place the prefix after each redraw marker.
    if "\r" in message:
        return message.replace("\r", f"\r[{step_name}] ")

    return f"[{step_name}] {message}"


#########################
# Stdout/Stderr Wrapping
#########################


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
            LoggingContext.dispatch(record)

        return original_write(_add_step_name_to_message(text))

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


#################
# Logging Filters
#################


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


###################
# Logging Handlers
###################


class ZenMLLoggingHandler(logging.Handler):
    """Custom handler that routes logs through LoggingContext."""

    def __init__(self) -> None:
        """Initialize the logging handler."""
        super().__init__()
        add_zenml_filters(self)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record through LoggingContext.

        Args:
            record: The log record to emit.
        """
        from zenml.utils.logging_utils import LoggingContext

        LoggingContext.dispatch(record)


class ZenMLConsoleHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Console handler owned by the ZenML logging setup.

    Default stream is ``_ZenMLStdoutStream()`` which writes
    to the original stdout, bypassing the ZenML wrapper.
    """

    def __init__(self, stream: Optional[Any] = None) -> None:
        """Initialize the console handler."""
        # initialize the handler with the provided stream or the default stream
        super().__init__(stream or _ZenMLStdoutStream())

        # set the formatter to the ZenML formatter
        self.setFormatter(_select_console_formatter())

        # add filters to the handler to attach structlog contextvars and step name to the log record
        add_zenml_filters(self)


#############################
# Root Logger Initialization
#############################


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
    # This makes repeated init_logging() calls idempotent.
    #
    # We are following, "remove and re-configure" pattern instead of
    # "add once, and skip later" pattern. On repeated init_logging() calls,
    # this allows us to re-configure the handlers with updated env vars (if any)
    # like ZENML_CONSOLE_LOGGING_FORMAT, ZENML_LOGGING_VERBOSITY, etc.
    _remove_zenml_handlers(root_logger)

    # Add new ZenML handlers to the root logger
    root_logger.addHandler(ZenMLConsoleHandler())
    root_logger.addHandler(ZenMLLoggingHandler())

    # Warn about deprecated logging format variables. We have to handle
    # it separately to avoid circular imports
    if (
        ENV_ZENML_LOGGING_FORMAT in os.environ
        and ENV_ZENML_CONSOLE_LOGGING_FORMAT not in os.environ
    ):
        get_logger(__name__).warning(
            "The `%s` environment variable is deprecated and will be "
            "removed in a future version. Use `%s` instead.",
            ENV_ZENML_LOGGING_FORMAT,
            ENV_ZENML_CONSOLE_LOGGING_FORMAT,
        )

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
