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
from typing import Optional
from uuid import uuid4

from zenml.artifact_stores import BaseArtifactStore
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.logging import (
    STEP_LOGS_STORAGE_INTERVAL_SECONDS,
    STEP_LOGS_STORAGE_MAX_MESSAGES,
)

# Get the logger
logger = get_logger(__name__)

redirected: ContextVar[bool] = ContextVar("redirected", default=False)


def remove_ansi_escape_codes(text):
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


class StepLogsStorage:
    def __init__(
        self,
        logs_uri: str,
        max_messages: int = STEP_LOGS_STORAGE_MAX_MESSAGES,
        time_interval: int = STEP_LOGS_STORAGE_INTERVAL_SECONDS,
    ):
        self.logs_uri = logs_uri

        self.max_messages = max_messages
        self.time_interval = time_interval

        self.buffer = []
        self.last_save_time = time.time()

        self.disabled = False

    def write(self, text):
        if text == "\n":
            return

        self.buffer.append(text)
        if (
            len(self.buffer) >= self.max_messages
            or time.time() - self.last_save_time >= self.time_interval
        ):
            self.save_to_file()

    def save_to_file(self):
        if not self.disabled:
            try:
                self.disabled = True

                if self.buffer:
                    with fileio.open(self.logs_uri, "a") as file:
                        for message in self.buffer:
                            file.write(
                                remove_ansi_escape_codes(message) + "\n"
                            )
                    self.buffer = []
                    self.last_save_time = time.time()

            except (OSError, IOError) as e:
                # This exception can be raised if there are issues with the
                # underlying system calls, such as reaching the maximum number
                # of open files, permission issues, file corruption, or other
                # I/O errors.
                logger.error(f"Error while trying to write logs: {e}")
            finally:
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
        self.stderr_write = getattr(sys.stderr, "write")

        setattr(sys.stdout, "write", self._wrap_write(self.stdout_write))
        setattr(sys.stderr, "write", self._wrap_write(self.stdout_write))
        redirected.set(True)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit condition of the context manager.

        Restores the `write` method of both stderr and stdout.
        """
        self.storage.save_to_file()

        setattr(sys.stdout, "write", self.stdout_write)
        setattr(sys.stderr, "write", self.stderr_write)
        redirected.set(False)

    def _wrap_write(self, method):
        """Wrapper function that utilizes the storage object to store logs.

        Args:
            method: the original write method

        Returns:
            the wrapped write method.
        """

        def wrapped_write(*args, **kwargs):
            if args:
                self.storage.write(args[0])
            return method(*args, **kwargs)

        return wrapped_write
