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
"""Logger Implementation.

structlog is configured as a ProcessorFormatter for stdlib logging so
that every existing ``logging.getLogger()`` call — including those from
third-party libraries such as uvicorn, SQLAlchemy and FastAPI — flows
through the same processor pipeline.

Output format is controlled by ``ZENML_LOGGING_FORMAT``:
  * ``"console"`` (default for CLI/SDK) — colored key=value via
    ``structlog.dev.ConsoleRenderer``
  * ``"json"`` (default when ``ZENML_SERVER`` is set) — one JSON object
    per line via ``structlog.processors.JSONRenderer``
"""

import logging
import os
import sys
from contextvars import ContextVar
from typing import Any, Optional

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

step_names_in_console: ContextVar[bool] = ContextVar(
    "step_names_in_console", default=False
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


def get_logger(logger_name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog-wrapped logger by name.

    The returned ``BoundLogger`` wraps a stdlib logger, so it supports
    the same API (``info``, ``debug``, ``warning``, ``exception``, …) plus
    structured keyword arguments (``logger.info("event", key=value)``).

    Args:
        logger_name: Name of logger to initialize.

    Returns:
        A structlog BoundLogger backed by the stdlib logger hierarchy.
    """
    return structlog.get_logger(logger_name)


def _add_step_name_processor(
    logger: Any,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Structlog processor that injects the current step name.

    Args:
        logger: The wrapped logger object (unused).
        method_name: The log method called (unused).
        event_dict: The event dictionary being processed.

    Returns:
        The enriched event dict.
    """
    try:
        if step_names_in_console.get():
            from zenml.steps import get_step_context

            step_context = get_step_context()
            if step_context:
                event_dict["step"] = step_context.step_name
    except Exception:
        # If we can't get step context, just use the original message
        pass
    return event_dict


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


def set_root_verbosity() -> None:
    """Set the root verbosity."""
    level = get_logging_level()
    if level != LoggingLevels.NOTSET:
        if ENABLE_RICH_TRACEBACK:
            rich_tb_install(show_locals=(level == LoggingLevels.DEBUG))

        logging.root.setLevel(level=level.value)
        get_logger(__name__).debug(
            f"Logging set to level: {logging.getLevelName(level.value)}"
        )
    else:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True
        get_logger(__name__).debug("Logging NOTSET")


def _is_json_format() -> bool:
    """Decide whether to emit JSON or console output.

    Returns:
        True when the output format should be JSON.
    """
    fmt = os.environ.get(ENV_ZENML_LOGGING_FORMAT, "").lower()
    if fmt == "json":
        return True
    if fmt == "console":
        return False
    return handle_bool_env_var(ENV_ZENML_SERVER, False)


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


class _ContextVarsFilter(logging.Filter):
    """Copies structlog contextvars into LogRecord attributes.

    This bridges the gap between structlog's context binding and handlers
    that read raw LogRecord objects (e.g. OTel's LoggingHandler). Without
    this filter, structured fields like request_id or method would only
    appear in the structlog-formatted console/JSON output but not in OTel
    log exports to any OpenTelemetry-compatible backend.
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
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class ZenMLLoggingHandler(logging.Handler):
    """Custom handler that routes logs through LoggingContext."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record through LoggingContext.

        Args:
            record: The log record to emit.
        """
        from zenml.utils.logging_utils import LoggingContext

        LoggingContext.emit(record)


def get_console_handler() -> logging.Handler:
    """Get a console handler with structlog formatting.

    Useful for attaching to standalone loggers (e.g. alembic) that are
    not children of the root logger.

    Returns:
        A console handler using structlog's ProcessorFormatter.
    """
    shared_processors: list[structlog.types.Processor] = [
        # injects bind_contextvars() fields (request_id, method, etc.)
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    json_mode = _is_json_format()
    if json_mode:
        # JSONRenderer can't handle raw exc_info; pre-format it
        shared_processors.append(structlog.processors.format_exc_info)
        renderer: structlog.types.Processor = (
            structlog.processors.JSONRenderer()
        )
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=not ZENML_LOGGING_COLORS_DISABLED,
        )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        # processes stdlib LogRecords (e.g. from alembic) through the same pipeline
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(_ZenMLStdoutStream())
    handler.setFormatter(formatter)
    return handler


def get_zenml_handler() -> logging.Handler:
    """Get ZenML handler that routes logs through LoggingContext.

    Returns:
        A ZenML handler.
    """
    return ZenMLLoggingHandler()


def init_logging() -> None:
    """Initialize the ZenML logging system using structlog.

    Configures structlog's ProcessorFormatter on the root logger so all
    stdlib log records (ZenML's own and those from third-party libraries)
    pass through the same processor pipeline.

    Output format is JSON when running inside the server (or when
    ``ZENML_LOGGING_FORMAT=json``), otherwise colored console output.
    """
    level = get_logging_level()

    if level == LoggingLevels.NOTSET:
        logging.disable(sys.maxsize)
        logging.getLogger().disabled = True
        return

    if ENABLE_RICH_TRACEBACK:
        rich_tb_install(show_locals=(level == LoggingLevels.DEBUG))

    # Processors shared between structlog-native loggers and Python's logging library.
    shared_processors: list[structlog.types.Processor] = [
        # injects any bind_contextvars() fields (request_id, method, path, etc.) into the event dict automatically
        structlog.contextvars.merge_contextvars,
        # injects step=<name> during step execution
        _add_step_name_processor,
        # interpolates %s-style positional args into the event string. Without this, logger.info("msg %s", arg) would render the literal %s.
        structlog.stdlib.PositionalArgumentsFormatter(),
        # adds the logger name to the event dict, e.g.: logger=zenml.zen_server.middleware field
        structlog.stdlib.add_logger_name,
        # adds the log level to the event dict
        structlog.stdlib.add_log_level,
        # formats timestamps in ISO 8601 format, e.g.: 2026-04-16T12:00:00.000000Z
        structlog.processors.TimeStamper(fmt="iso"),
        # renders stack_info if present
        structlog.processors.StackInfoRenderer(),
    ]

    json_mode = _is_json_format()
    if json_mode:
        # JSONRenderer doesn't handle exc_info; pre-format it.
        shared_processors.append(structlog.processors.format_exc_info)
        renderer: structlog.types.Processor = (
            structlog.processors.JSONRenderer()
        )
    else:
        # ConsoleRenderer handles exc_info itself (with Rich pretty-printing).
        renderer = structlog.dev.ConsoleRenderer(
            colors=not ZENML_LOGGING_COLORS_DISABLED,
        )

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            # stashes the event dict on the LogRecord for ProcessorFormatter
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # BoundLogger mirrors logging.Logger API + structured kwargs
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        # creates real stdlib loggers so records flow through stdlib handlers
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
        # ^^^foreign_pre_chain is used to process logs that come from Python's logging library.
        # processes stdlib LogRecords (uvicorn, SQLAlchemy, etc.) through the same pipeline
    )

    # Console handler — writes to original stdout to bypass the
    # LoggingContext wrapper and prevent duplicate stored-log entries.
    console_handler = logging.StreamHandler(_ZenMLStdoutStream())
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    # routes records to LoggingContext for step log persistence
    root_logger.addHandler(get_zenml_handler())
    # copies structlog contextvars onto LogRecord for OTel export
    root_logger.addFilter(_ContextVarsFilter())
    root_logger.setLevel(level.value)

    # must run after handlers are attached so any init-time stdout
    # writes hit a fully configured logging system
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
