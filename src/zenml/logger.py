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

import logging
import os
import re
import sys
from logging import getLevelName
from typing import Any, Callable, Dict, List, Optional

from rich.traceback import install as rich_tb_install

from zenml.constants import (
    ENABLE_RICH_TRACEBACK,
    ENV_ZENML_LOGGING_COLORS_DISABLED,
    ENV_ZENML_LOGGING_FORMAT,
    ENV_ZENML_SUPPRESS_LOGS,
    ZENML_LOGGING_VERBOSITY,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels

ZENML_LOGGING_COLORS_DISABLED = handle_bool_env_var(
    ENV_ZENML_LOGGING_COLORS_DISABLED, False
)


class LogCollectorRegistry:
    """Singleton registry for log collectors."""

    _instance: Optional["LogCollectorRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "LogCollectorRegistry":
        """Create a new instance of the LogCollectorRegistry.

        Returns:
            The singleton instance of the LogCollectorRegistry.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the LogCollectorRegistry.

        Returns:
            The singleton instance of the LogCollectorRegistry.
        """
        if not self._initialized:
            self.collectors: List[Callable[[str, bool], Any]] = []
            self.original_stdout_write: Optional[Callable] = None
            self.original_stderr_write: Optional[Callable] = None
            self.original_stdout_flush: Optional[Callable] = None
            self.original_stderr_flush: Optional[Callable] = None
            self._stdout_stderr_wrapped: bool = False
            self._initialized = True

            self._setup_stdout_stderr_wrapping()

    def add_collector(self, collector: Callable[[str, bool], Any]) -> None:
        """Add a collector to handle log messages.

        Args:
            collector: A callable that takes (message: str, is_stderr: bool) and processes it.
        """
        if collector not in self.collectors:
            self.collectors.append(collector)

    def remove_collector(self, collector: Callable[[str, bool], Any]) -> None:
        """Remove a collector from the registry.

        Args:
            collector: The collector to remove.
        """
        if collector in self.collectors:
            self.collectors.remove(collector)

    def _default_collector(self, message: str, is_stderr: bool) -> Any:
        """Default collector that writes to original stdout/stderr.

        Args:
            message: The message to write.
            is_stderr: Whether this is stderr output.

        Returns:
            The result of the original write method.
        """
        # Parse out log level tokens before writing to console
        clean_message = self._parse_and_clean_message(message)

        if is_stderr and self.original_stderr_write:
            return self.original_stderr_write(clean_message)
        elif not is_stderr and self.original_stdout_write:
            return self.original_stdout_write(clean_message)
        return None

    def _parse_and_clean_message(self, message: str) -> str:
        """Parse and clean ZenML log format tokens from message.

        Args:
            message: The original message that may contain log level tokens.

        Returns:
            The cleaned message with log level tokens and location info removed.
        """
        clean_message = message
        for level in LoggingLevels:
            level_token = f"[{getLevelName(level.value)}] "
            if level_token in clean_message:
                clean_message = clean_message.replace(level_token, "", 1)
        return clean_message

    def _wrapped_write(self, is_stderr: bool = False) -> Callable:
        """Create a wrapped write function.

        Args:
            is_stderr: Whether this is for stderr.

        Returns:
            The wrapped write function.
        """

        def wrapped_write(*args: Any, **kwargs: Any) -> Any:
            message = args[0]
            result = None

            # Call all collectors in sequence
            for collector in self.collectors:
                try:
                    result = collector(message, is_stderr)
                except Exception as e:
                    # If a collector fails, log the error but continue
                    print(f"Error in log collector: {e}", file=sys.stderr)

            return result

        return wrapped_write

    def _wrapped_flush(self, is_stderr: bool = False) -> Callable:
        """Create a wrapped flush function.

        Args:
            is_stderr: Whether this is for stderr.

        Returns:
            The wrapped flush function.
        """

        def wrapped_flush(*args: Any, **kwargs: Any) -> Any:
            original_flush = (
                self.original_stderr_flush
                if is_stderr
                else self.original_stdout_flush
            )
            if original_flush:
                return original_flush(*args, **kwargs)
            return None

        return wrapped_flush

    def _setup_stdout_stderr_wrapping(self) -> None:
        """Set up stdout and stderr wrapping."""
        if not self._stdout_stderr_wrapped:
            # Store original methods
            self.original_stdout_write = getattr(sys.stdout, "write")
            self.original_stdout_flush = getattr(sys.stdout, "flush")
            self.original_stderr_write = getattr(sys.stderr, "write")
            self.original_stderr_flush = getattr(sys.stderr, "flush")

            # Add default collector directly to avoid recursion
            self.collectors.append(self._default_collector)

            # Wrap stdout and stderr
            setattr(sys.stdout, "write", self._wrapped_write(is_stderr=False))
            setattr(sys.stdout, "flush", self._wrapped_flush(is_stderr=False))
            setattr(sys.stderr, "write", self._wrapped_write(is_stderr=True))
            setattr(sys.stderr, "flush", self._wrapped_flush(is_stderr=True))

            self._stdout_stderr_wrapped = True


class CustomFormatter(logging.Formatter):
    """Formats logs according to custom specifications."""

    grey: str = "\x1b[38;21m"
    pink: str = "\x1b[35m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    red: str = "\x1b[31m"
    cyan: str = "\x1b[1;36m"
    bold_red: str = "\x1b[31;1m"
    purple: str = "\x1b[1;35m"
    blue: str = "\x1b[34m"
    reset: str = "\x1b[0m"

    format_template: str = (
        "[%(levelname)s] %(message)s (%(name)s:%(filename)s:%(lineno)d)"
    )

    COLORS: Dict[LoggingLevels, str] = {
        LoggingLevels.DEBUG: grey,
        LoggingLevels.INFO: purple,
        LoggingLevels.WARN: yellow,
        LoggingLevels.ERROR: red,
        LoggingLevels.CRITICAL: bold_red,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Converts a log record to a (colored) string.

        Args:
            record: LogRecord generated by the code.

        Returns:
            A string formatted according to specifications.
        """
        if ZENML_LOGGING_COLORS_DISABLED:
            # If color formatting is disabled, use the default format without colors
            formatter = logging.Formatter(self.format_template)
            return formatter.format(record)
        else:
            # Use color formatting
            log_fmt = (
                self.COLORS[LoggingLevels(record.levelno)]
                + self.format_template
                + self.reset
            )
            formatter = logging.Formatter(log_fmt)
            formatted_message = formatter.format(record)
            quoted_groups = re.findall("`([^`]*)`", formatted_message)
            for quoted in quoted_groups:
                formatted_message = formatted_message.replace(
                    "`" + quoted + "`",
                    self.reset
                    + self.cyan
                    + quoted
                    + self.COLORS.get(LoggingLevels(record.levelno)),
                )

            # Format URLs
            url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
            urls = re.findall(url_pattern, formatted_message)
            for url in urls:
                formatted_message = formatted_message.replace(
                    url,
                    self.reset
                    + self.blue
                    + url
                    + self.COLORS.get(LoggingLevels(record.levelno)),
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


def get_formatter() -> logging.Formatter:
    """Get a configured logging formatter.

    Returns:
        The formatter.
    """
    if log_format := os.environ.get(ENV_ZENML_LOGGING_FORMAT, None):
        return logging.Formatter(fmt=f"[%(levelname)s] {log_format}")
    else:
        return CustomFormatter()


def get_console_handler() -> Any:
    """Get console handler for logging.

    Returns:
        A console handler.
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(get_formatter())
    return console_handler


def get_logger(logger_name: str) -> logging.Logger:
    """Main function to get logger name,.

    Args:
        logger_name: Name of logger to initialize.

    Returns:
        A logger object.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(get_logging_level().value)
    logger.addHandler(get_console_handler())

    logger.propagate = False
    return logger


def init_logging() -> None:
    """Initialize logging with default levels."""
    # Mute tensorflow cuda warnings
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    set_root_verbosity()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(get_formatter())
    logging.root.addHandler(console_handler)

    # Initialize the singleton registry (wrapping is set up automatically)
    LogCollectorRegistry()

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
