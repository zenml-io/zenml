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
"""Logger implementation."""

import json
import logging
import os
import sys
from contextvars import ContextVar
from typing import Any, Optional

from rich.traceback import install as rich_tb_install

from zenml.constants import (
    ENABLE_RICH_TRACEBACK,
    ENV_ZENML_LOGGING_COLORS_DISABLED,
    ENV_ZENML_SUPPRESS_LOGS,
    ZENML_LOGGING_VERBOSITY,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels

step_names_in_console: ContextVar[bool] = ContextVar(
    "step_names_in_console", default=False
)

_original_stdout_write: Optional[Any] = None
_original_stderr_write: Optional[Any] = None
_stdout_wrapped: bool = False
_stderr_wrapped: bool = False


def get_logger(logger_name: str) -> logging.Logger:
    """Main function to get logger name,.

    Args:
        logger_name: Name of logger to initialize.

    Returns:
        A logger object.
    """
    return logging.getLogger(logger_name)


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
                # For progress bar updates (with \r), inject the step name after the \r
                if "\r" in message:
                    message = message.replace(
                        "\r", f"\r[{step_context.step_name}] "
                    )
                else:
                    message = f"[{step_context.step_name}] {message}"
    except Exception:
        # If we can't get step context, just use the original message
        pass

    return message


def format_console_message(
    message: str, level: LoggingLevels = LoggingLevels.INFO
) -> str:
    """Format a message for console output with colors and step names.

    This function applies:
    1. Step name prefixing (if step_names_in_console is True)
    2. Color formatting (unless ZENML_LOGGING_COLORS_DISABLED)
    3. Special formatting for quoted text (purple) and URLs (blue)

    Args:
        message: The message to format.
        level: The logging level for color selection.

    Returns:
        The formatted message.
    """
    import re

    try:
        if step_names_in_console.get():
            message = _add_step_name_to_message(message)
    except Exception:
        pass

    if handle_bool_env_var(ENV_ZENML_LOGGING_COLORS_DISABLED, False):
        return message

    grey = "\x1b[90m"
    white = "\x1b[37m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    purple = "\x1b[38;5;105m"
    blue = "\x1b[34m"
    reset = "\x1b[0m"

    COLORS = {
        LoggingLevels.DEBUG: grey,
        LoggingLevels.INFO: white,
        LoggingLevels.WARN: yellow,
        LoggingLevels.ERROR: red,
        LoggingLevels.CRITICAL: bold_red,
    }

    level_color = COLORS.get(level, white)

    formatted_message = f"{level_color}{message}{reset}"

    quoted_groups = re.findall("`([^`]*)`", formatted_message)
    for quoted in quoted_groups:
        formatted_message = formatted_message.replace(
            "`" + quoted + "`",
            f"{reset}{purple}{quoted}{level_color}",
        )

    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    urls = re.findall(url_pattern, formatted_message)
    for url in urls:
        formatted_message = formatted_message.replace(
            url,
            f"{reset}{blue}{url}{level_color}",
        )

    return formatted_message


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


class ZenMLFormatter(logging.Formatter):
    """Formats logs according to custom specifications."""

    def format(self, record: logging.LogRecord) -> str:
        """Converts a log record to a (colored) string or structured JSON.

        Args:
            record: LogRecord generated by the code.

        Returns:
            A string formatted according to specifications.
        """
        data = {
            "zenml": True,
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
        }

        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(data, ensure_ascii=False)


def _wrapped_write(original_write: Any, stream_name: str) -> Any:
    """Wrap stdout/stderr write method to parse and route logs."""

    def wrapped_write(text: str) -> int:
        """Wrap the write method to parse and route logs."""
        from zenml.logging.logging import get_active_log_store

        message = text
        name = "unknown"
        level = (
            LoggingLevels.INFO
            if stream_name == "info"
            else LoggingLevels.ERROR
        )
        level_int = getattr(logging, level.name)
        pathname = ""
        lineno = 0
        funcName = ""

        has_newline = text.endswith("\n")

        stripped_text = text.strip()
        if stripped_text.startswith("{") and stripped_text.endswith("}"):
            try:
                data = json.loads(stripped_text)
                if "zenml" in data and data["zenml"] is True:
                    message = data.get("msg", text)
                    name = data.get("name", name)
                    level_str = data.get("level", level.name)
                    if hasattr(LoggingLevels, level_str):
                        level = getattr(LoggingLevels, level_str)
                        level_int = getattr(logging, level.name)
                    pathname = data.get("filename", pathname)
                    lineno = data.get("lineno", lineno)
                    funcName = data.get("module", funcName)
            except Exception:
                pass

        log_store = get_active_log_store()
        if log_store:
            record = logging.LogRecord(
                name=name,
                level=level_int,
                pathname=pathname,
                lineno=lineno,
                msg=message,
                args=(),
                exc_info=None,
                func=funcName,
            )
            log_store.emit(record)

        formatted_message = format_console_message(message, level)
        if has_newline:
            formatted_message += "\n"

        return original_write(formatted_message)

    return wrapped_write


def wrap_stdout_stderr() -> None:
    """Wrap stdout and stderr write methods."""
    global _stdout_wrapped, _stderr_wrapped
    global _original_stdout_write, _original_stderr_write

    if not _stdout_wrapped:
        _original_stdout_write = getattr(sys.stdout, "write")
        setattr(
            sys.stdout,
            "write",
            _wrapped_write(_original_stdout_write, "info"),
        )
        _stdout_wrapped = True

    if not _stderr_wrapped:
        _original_stderr_write = getattr(sys.stderr, "write")
        setattr(
            sys.stderr,
            "write",
            _wrapped_write(_original_stderr_write, "error"),
        )
        _stderr_wrapped = True


def get_zenml_handler() -> Any:
    """Get console handler for logging.

    Returns:
        A console handler.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ZenMLFormatter())
    return handler


def init_logging() -> None:
    """Initialize the logging system."""
    set_root_verbosity()
    wrap_stdout_stderr()

    # Add the ZenML handler to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(get_zenml_handler())

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
