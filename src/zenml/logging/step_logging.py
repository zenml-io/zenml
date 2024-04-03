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

import os
import re
import sys
import time
from contextvars import ContextVar
from types import TracebackType
from typing import Any, Callable, List, Optional, Type
from uuid import uuid4

from zenml.artifact_stores import BaseArtifactStore
from zenml.client import Client
from zenml.logger import get_logger
from zenml.logging import (
    STEP_LOGS_STORAGE_INTERVAL_SECONDS,
    STEP_LOGS_STORAGE_MAX_MESSAGES,
)

# Get the logger
logger = get_logger(__name__)

redirected: ContextVar[bool] = ContextVar("redirected", default=False)


def remove_ansi_escape_codes(text: str) -> str:
    """Auxiliary function to remove ANSI escape codes from a given string.

    Args:
        text: the input string

    Returns:
        the version of the input string where the escape codes are removed.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


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
    if not artifact_store.exists(logs_base_uri):
        artifact_store.makedirs(logs_base_uri)

    # Delete the file if it already exists
    logs_uri = os.path.join(logs_base_uri, f"{log_key}.log")
    if artifact_store.exists(logs_uri):
        logger.warning(
            f"Logs file {logs_uri} already exists! Removing old log file..."
        )
        artifact_store.remove(logs_uri)
    return logs_uri


class StepLogsStorage:
    """Helper class which buffers and stores logs to a given URI."""

    def __init__(
        self,
        logs_uri: str,
        max_messages: int = STEP_LOGS_STORAGE_MAX_MESSAGES,
        time_interval: int = STEP_LOGS_STORAGE_INTERVAL_SECONDS,
    ) -> None:
        """Initialization.

        Args:
            logs_uri: the target URI to store the logs.
            max_messages: the maximum number of messages to save in the buffer.
            time_interval: the amount of seconds before the buffer gets saved
                automatically.
        """
        # Parameters
        self.logs_uri = logs_uri
        self.max_messages = max_messages
        self.time_interval = time_interval

        # State
        self.buffer: List[str] = []
        self.disabled_buffer: List[str] = []
        self.last_save_time = time.time()
        self.disabled = False

    def write(self, text: str) -> None:
        """Main write method.

        Args:
            text: the incoming string.
        """
        if text == "\n":
            return

        if not self.disabled:
            self.buffer.append(text)

            if (
                len(self.buffer) >= self.max_messages
                or time.time() - self.last_save_time >= self.time_interval
            ):
                self.save_to_file()

    def save_to_file(self) -> None:
        """Method to save the buffer to the given URI."""
        artifact_store = Client().active_stack.artifact_store
        if not self.disabled:
            try:
                self.disabled = True

                if self.buffer:
                    with artifact_store.open(self.logs_uri, "a") as file:
                        for message in self.buffer:
                            file.write(
                                remove_ansi_escape_codes(message) + "\n"
                            )

            except (OSError, IOError) as e:
                # This exception can be raised if there are issues with the
                # underlying system calls, such as reaching the maximum number
                # of open files, permission issues, file corruption, or other
                # I/O errors.
                logger.error(f"Error while trying to write logs: {e}")
            finally:
                self.buffer = []
                self.last_save_time = time.time()

                self.disabled = False


class StepLogsStorageContext:
    """Context manager which patches stdout and stderr during step execution."""

    def __init__(self, logs_uri: str) -> None:
        """Initializes and prepares a storage object.

        Args:
            logs_uri: the URI of the logs file.
        """
        self.storage = StepLogsStorage(logs_uri=logs_uri)

    def __enter__(self) -> "StepLogsStorageContext":
        """Enter condition of the context manager.

        Wraps the `write` method of both stderr and stdout, so each incoming
        message gets stored in the step logs storage.

        Returns:
            self
        """
        self.stdout_write = getattr(sys.stdout, "write")
        self.stdout_flush = getattr(sys.stdout, "flush")

        self.stderr_write = getattr(sys.stderr, "write")
        self.stderr_flush = getattr(sys.stderr, "flush")

        setattr(sys.stdout, "write", self._wrap_write(self.stdout_write))
        setattr(sys.stdout, "flush", self._wrap_flush(self.stdout_flush))

        setattr(sys.stderr, "write", self._wrap_write(self.stdout_write))
        setattr(sys.stderr, "flush", self._wrap_flush(self.stdout_flush))

        redirected.set(True)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit condition of the context manager.

        Args:
            exc_type: The class of the exception
            exc_val: The instance of the exception
            exc_tb: The traceback of the exception

        Restores the `write` method of both stderr and stdout.
        """
        self.storage.save_to_file()

        setattr(sys.stdout, "write", self.stdout_write)
        setattr(sys.stdout, "flush", self.stdout_flush)

        setattr(sys.stderr, "write", self.stderr_write)
        setattr(sys.stderr, "flush", self.stderr_flush)

        redirected.set(False)

    def _wrap_write(self, method: Callable[..., Any]) -> Callable[..., Any]:
        """Wrapper function that utilizes the storage object to store logs.

        Args:
            method: the original write method

        Returns:
            the wrapped write method.
        """

        def wrapped_write(*args: Any, **kwargs: Any) -> Any:
            output = method(*args, **kwargs)
            if args:
                self.storage.write(args[0])
            return output

        return wrapped_write

    def _wrap_flush(self, method: Callable[..., Any]) -> Callable[..., Any]:
        """Wrapper function that flushes the buffer of the storage object.

        Args:
            method: the original flush method

        Returns:
            the wrapped flush method.
        """

        def wrapped_flush(*args: Any, **kwargs: Any) -> Any:
            output = method(*args, **kwargs)
            self.storage.save_to_file()
            return output

        return wrapped_flush
