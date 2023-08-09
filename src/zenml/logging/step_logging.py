#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""ZenML logging handler."""

import io
import logging
import os
import time
from io import StringIO
from logging import LogRecord
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from uuid import uuid4

from zenml.artifact_stores import BaseArtifactStore
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.logging import (
    LOGS_HANDLER_INTERVAL_SECONDS,
    LOGS_HANDLER_MAX_MESSAGES,
    STEP_STDERR_LOGGER_NAME,
    STEP_STDOUT_LOGGER_NAME,
)
from zenml.utils.io_utils import is_remote

# Get the logger
logger = get_logger(__name__)


def prepare_logs_uri(
    artifact_store: "BaseArtifactStore",
    step_name: str,
    log_key: Optional[str] = None,
) -> str:
    """Generates and prepares a URI for the log file for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        step_name: Name of the step.
        log_key: The unique identification key of the log file.

    Returns:
        The URI of the logs file.
    """
    if log_key is None:
        log_key = str(uuid4())

    logs_base_uri = os.path.join(
        artifact_store.path,
        step_name,
        "logs",
    )

    # Create the dir
    if not fileio.exists(logs_base_uri):
        fileio.makedirs(logs_base_uri)

    # Delete the file if it already exists
    logs_uri = os.path.join(logs_base_uri, f"{log_key}.log")
    if fileio.exists(logs_uri):
        logger.warning(
            f"Logs file {logs_uri} already exists! Removing old log file..."
        )
        fileio.remove(logs_uri)
    return logs_uri


class StepStdOut(StringIO):
    """A replacement for the sys.stdout to turn outputs into logging entries.

    When used in combination with the ZenHandler, this class allows us to
    capture any print statements or third party outputs as logs and store them
    in the artifact store.

    Right now, this is only used during the execution of a ZenML step.
    """

    stdout_logger = logging.getLogger(STEP_STDOUT_LOGGER_NAME)

    def write(self, message: str) -> int:
        """Write the incoming string as an info log entry.

        Args:
            message: the incoming message string

        Returns:
            the length of the message string
        """
        if message != "\n":
            self.stdout_logger.info(message)
        return len(message)


class StepStdErr(StringIO):
    """A replacement for the sys.stderr to turn outputs into logging entries.

    When used in combination with the ZenHandler, this class allows us to
    capture any stderr outputs as logs and store them in the artifact store.

    Right now, this is only used during the execution of a ZenML step.
    """

    stderr_logger = logging.getLogger(STEP_STDERR_LOGGER_NAME)

    def write(self, message: str) -> int:
        """Write the incoming string as an info log entry.

        Args:
            message: the incoming message string

        Returns:
            the length of the message string
        """
        if message != "\n":
            self.stderr_logger.info(message)
        return len(message)


class StepLoggingFormatter(logging.Formatter):
    """Specialized formatter changing the level name if step handler is used."""

    def format(self, record: logging.LogRecord) -> str:
        """Specialized format method to distinguish between logs and stdout.

        Args:
            record: the incoming log record

        Returns:
            the formatted string
        """
        if record.name == STEP_STDOUT_LOGGER_NAME:
            record.levelname = "STDOUT"

        if record.name == STEP_STDERR_LOGGER_NAME:
            record.levelname = "STDERR"

        return super().format(record)


class StepLoggingHandler(TimedRotatingFileHandler):
    """Specialized handler that stores ZenML step logs in artifact stores."""

    def __init__(self, logs_uri: str):
        """Initializes the handler.

        Args:
            logs_uri: URI of the logs file.
        """
        self.logs_uri = logs_uri
        self.max_messages = LOGS_HANDLER_MAX_MESSAGES
        self.buffer = io.StringIO()
        self.message_count = 0
        self.last_upload_time = time.time()
        self.local_temp_file: Optional[str] = None
        self.disabled = False

        # set local_logging_file to self.logs_uri if self.logs_uri is a
        # local path otherwise, set local_logging_file to a temporary file
        if is_remote(self.logs_uri):
            # We log to a temporary file first, because
            # TimedRotatingFileHandler does not support writing
            # to a remote file, but still needs a file to get going
            local_logging_file = f".zenml_tmp_logs_{int(time.time())}"
            self.local_temp_file = local_logging_file
        else:
            local_logging_file = self.logs_uri

        super().__init__(
            local_logging_file,
            when="s",
            interval=LOGS_HANDLER_INTERVAL_SECONDS,
        )

    def emit(self, record: LogRecord) -> None:
        """Emits the log record.

        Args:
            record: Log record to emit.
        """
        msg = self.format(record)
        self.buffer.write(msg + "\n")
        self.message_count += 1

        current_time = time.time()
        time_elapsed = current_time - self.last_upload_time

        if (
            self.message_count >= self.max_messages
            or time_elapsed >= self.interval
        ):
            self.flush()

    def flush(self) -> None:
        """Flushes the buffer to the artifact store."""
        if not self.disabled:
            try:
                self.disabled = True
                with fileio.open(self.logs_uri, mode="wb") as log_file:
                    log_file.write(self.buffer.getvalue().encode("utf-8"))
            except (OSError, IOError) as e:
                # This exception can be raised if there are issues with the
                # underlying system calls, such as reaching the maximum number
                # of open files, permission issues, file corruption, or other
                # I/O errors.
                logger.error(f"Error while trying to write logs: {e}")
            finally:
                self.disabled = False

        self.message_count = 0
        self.last_upload_time = time.time()

    def doRollover(self) -> None:
        """Flushes the buffer and performs a rollover."""
        self.flush()
        super().doRollover()

    def close(self) -> None:
        """Tidy up any resources used by the handler."""
        self.flush()
        super().close()

        if not self.disabled:
            try:
                self.disabled = True
                if self.local_temp_file and fileio.exists(
                    self.local_temp_file
                ):
                    fileio.remove(self.local_temp_file)
            except (OSError, IOError) as e:
                # This exception can be raised if there are issues with the
                # underlying system calls, such as reaching the maximum number
                # of open files, permission issues, file corruption, or other
                # I/O errors.
                logger.error(f"Error while close the logger: {e}")
            finally:
                self.disabled = False


def get_step_logging_handler(logs_uri: str) -> StepLoggingHandler:
    """Sets up a logging handler for the artifact store.

    Args:
        logs_uri: The URI of the output artifact.

    Returns:
        The logging handler.
    """
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"  # ISO 8601 format
    handler = StepLoggingHandler(logs_uri)
    handler.setFormatter(StepLoggingFormatter(log_format, datefmt=date_format))
    return handler
