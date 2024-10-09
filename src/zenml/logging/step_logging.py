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

import datetime
import os
import re
import sys
import time
from contextvars import ContextVar
from types import TracebackType
from typing import Any, Callable, List, Optional, Type, Union
from uuid import UUID, uuid4

from zenml.artifact_stores import BaseArtifactStore
from zenml.artifacts.utils import (
    _load_artifact_store,
    _load_file_from_artifact_store,
)
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.logging import (
    STEP_LOGS_STORAGE_INTERVAL_SECONDS,
    STEP_LOGS_STORAGE_MAX_MESSAGES,
    STEP_LOGS_STORAGE_MERGE_INTERVAL_SECONDS,
)
from zenml.zen_stores.base_zen_store import BaseZenStore

# Get the logger
logger = get_logger(__name__)

redirected: ContextVar[bool] = ContextVar("redirected", default=False)

LOGS_EXTENSION = ".log"


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
    """Generates and prepares a URI for the log file or folder for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        step_name: Name of the step.
        log_key: The unique identification key of the log file.

    Returns:
        The URI of the log storage (file or folder).
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
    if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
        logs_uri_folder = os.path.join(logs_base_uri, log_key)
        if artifact_store.exists(logs_uri_folder):
            logger.warning(
                f"Logs directory {logs_uri_folder} already exists! Removing old log directory..."
            )
            artifact_store.rmtree(logs_uri_folder)

        artifact_store.makedirs(logs_uri_folder)
        return logs_uri_folder
    else:
        logs_uri = os.path.join(logs_base_uri, f"{log_key}{LOGS_EXTENSION}")
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs file {logs_uri} already exists! Removing old log file..."
            )
            artifact_store.remove(logs_uri)
        return logs_uri


def fetch_logs(
    zen_store: "BaseZenStore",
    artifact_store_id: Union[str, UUID],
    logs_uri: str,
    offset: int = 0,
    length: int = 1024 * 1024 * 16,  # Default to 16MiB of data
) -> str:
    """Fetches the logs from the artifact store.

    Args:
        zen_store: The store in which the artifact is stored.
        artifact_store_id: The ID of the artifact store.
        logs_uri: The URI of the artifact.
        offset: The offset from which to start reading.
        length: The amount of bytes that should be read.

    Returns:
        The logs as a string.

    Raises:
        DoesNotExistException: If the artifact does not exist in the artifact
            store.
    """

    def _read_file(
        uri: str, offset: int = 0, length: Optional[int] = None
    ) -> str:
        return str(
            _load_file_from_artifact_store(
                uri,
                artifact_store=artifact_store,
                mode="rb",
                offset=offset,
                length=length,
            ).decode()
        )

    artifact_store = _load_artifact_store(artifact_store_id, zen_store)
    try:
        if not artifact_store.isdir(logs_uri):
            return _read_file(logs_uri, offset, length)
        else:
            files = artifact_store.listdir(logs_uri)
            if len(files) == 1:
                return _read_file(
                    os.path.join(logs_uri, str(files[0])), offset, length
                )
            else:
                is_negative_offset = offset < 0
                files.sort(reverse=is_negative_offset)

                # search for the first file we need to read
                latest_file_id = 0
                for i, file in enumerate(files):
                    file_size: int = artifact_store.size(
                        os.path.join(logs_uri, str(file))
                    )  # type: ignore[assignment]

                    if is_negative_offset:
                        if file_size >= -offset:
                            latest_file_id = -(i + 1)
                            break
                        else:
                            offset += file_size
                    else:
                        if file_size > offset:
                            latest_file_id = i
                            break
                        else:
                            offset -= file_size

                # read the files according to pre-filtering
                files.sort()
                ret = []
                for file in files[latest_file_id:]:
                    ret.append(
                        _read_file(
                            os.path.join(logs_uri, str(file)),
                            offset,
                            length,
                        )
                    )
                    offset = 0
                    length -= len(ret[-1])
                    if length <= 0:
                        # stop further reading, if the whole length is already read
                        break

                if not ret:
                    raise DoesNotExistException(
                        f"Folder '{logs_uri}' is empty in artifact store "
                        f"'{artifact_store.name}'."
                    )
                return "".join(ret)
    finally:
        artifact_store.cleanup()


class StepLogsStorage:
    """Helper class which buffers and stores logs to a given URI."""

    def __init__(
        self,
        logs_uri: str,
        artifact_store: "BaseArtifactStore",
        max_messages: int = STEP_LOGS_STORAGE_MAX_MESSAGES,
        time_interval: int = STEP_LOGS_STORAGE_INTERVAL_SECONDS,
        merge_files_interval: int = STEP_LOGS_STORAGE_MERGE_INTERVAL_SECONDS,
    ) -> None:
        """Initialization.

        Args:
            logs_uri: the URI of the log file or folder.
            artifact_store: Artifact Store from the current step context
            max_messages: the maximum number of messages to save in the buffer.
            time_interval: the amount of seconds before the buffer gets saved
                automatically.
            merge_files_interval: the amount of seconds before the created files
                get merged into a single file.
        """
        # Parameters
        self.logs_uri = logs_uri
        self.max_messages = max_messages
        self.time_interval = time_interval
        self.merge_files_interval = merge_files_interval

        # State
        self.buffer: List[str] = []
        self.disabled_buffer: List[str] = []
        self.last_save_time = time.time()
        self.disabled = False
        self.artifact_store = artifact_store

        # Immutable filesystems state
        self.last_merge_time = time.time()

    def write(self, text: str) -> None:
        """Main write method.

        Args:
            text: the incoming string.
        """
        if text == "\n":
            return

        if not self.disabled:
            self.buffer.append(text)
            self.save_to_file()

    @property
    def _is_write_needed(self) -> bool:
        """Checks whether the buffer needs to be written to disk.

        Returns:
            whether the buffer needs to be written to disk.
        """
        return (
            len(self.buffer) >= self.max_messages
            or time.time() - self.last_save_time >= self.time_interval
        )

    def _get_timestamped_filename(self, suffix: str = "") -> str:
        """Returns a timestamped filename.

        Args:
            suffix: optional suffix for the file name

        Returns:
            The timestamped filename.
        """
        return f"{time.time()}{suffix}{LOGS_EXTENSION}"

    def save_to_file(self, force: bool = False) -> None:
        """Method to save the buffer to the given URI.

        Args:
            force: whether to force a save even if the write conditions not met.
        """
        if not self.disabled and (self._is_write_needed or force):
            # IMPORTANT: keep this as the first code line in this method! The
            # code that follows might still emit logging messages, which will
            # end up triggering this method again, causing an infinite loop.
            self.disabled = True

            try:
                if self.buffer:
                    if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
                        _logs_uri = self._get_timestamped_filename()
                        with self.artifact_store.open(
                            os.path.join(
                                self.logs_uri,
                                _logs_uri,
                            ),
                            "w",
                        ) as file:
                            for message in self.buffer:
                                timestamp = datetime.datetime.now(
                                    datetime.timezone.utc
                                ).strftime("%Y-%m-%d %H:%M:%S")
                                file.write(
                                    f"[{timestamp} UTC] {remove_ansi_escape_codes(message)}\n"
                                )
                    else:
                        with self.artifact_store.open(
                            self.logs_uri, "a"
                        ) as file:
                            for message in self.buffer:
                                timestamp = datetime.datetime.now(
                                    datetime.timezone.utc
                                ).strftime("%Y-%m-%d %H:%M:%S")
                                file.write(
                                    f"[{timestamp} UTC] {remove_ansi_escape_codes(message)}\n"
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
        # merge created files on a given interval (defaults to 10 minutes)
        # only runs on Immutable Filesystems
        if (
            self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM
            and time.time() - self.last_merge_time > self.merge_files_interval
        ):
            try:
                self.merge_log_files()
            except (OSError, IOError) as e:
                logger.error(f"Error while trying to roll up logs: {e}")
            finally:
                self.last_merge_time = time.time()

    def merge_log_files(self, merge_all_files: bool = False) -> None:
        """Merges all log files into one in the given URI.

        Called on the logging context exit.

        Args:
            merge_all_files: whether to merge all files or only raw files
        """
        if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
            merged_file_suffix = "_merged"
            files_ = self.artifact_store.listdir(self.logs_uri)
            if not merge_all_files:
                # already merged files will not be merged again
                files_ = [f for f in files_ if merged_file_suffix not in f]
            file_name_ = self._get_timestamped_filename(
                suffix=merged_file_suffix
            )
            if len(files_) > 1:
                files_.sort()
                logger.debug("Log files count: %s", len(files_))

                missing_files = set()
                # dump all logs to a local file first
                with self.artifact_store.open(
                    os.path.join(self.logs_uri, file_name_), "w"
                ) as merged_file:
                    for file in files_:
                        try:
                            merged_file.write(
                                str(
                                    _load_file_from_artifact_store(
                                        os.path.join(self.logs_uri, str(file)),
                                        artifact_store=self.artifact_store,
                                        mode="r",
                                    )
                                )
                            )
                        except DoesNotExistException:
                            missing_files.add(file)

                # clean up left over files
                for file in files_:
                    if file not in missing_files:
                        self.artifact_store.remove(
                            os.path.join(self.logs_uri, str(file))
                        )


class StepLogsStorageContext:
    """Context manager which patches stdout and stderr during step execution."""

    def __init__(
        self, logs_uri: str, artifact_store: "BaseArtifactStore"
    ) -> None:
        """Initializes and prepares a storage object.

        Args:
            logs_uri: the URI of the logs file.
            artifact_store: Artifact Store from the current step context.
        """
        self.storage = StepLogsStorage(
            logs_uri=logs_uri, artifact_store=artifact_store
        )

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
        self.storage.save_to_file(force=True)

        setattr(sys.stdout, "write", self.stdout_write)
        setattr(sys.stdout, "flush", self.stdout_flush)

        setattr(sys.stderr, "write", self.stderr_write)
        setattr(sys.stderr, "flush", self.stderr_flush)

        redirected.set(False)

        try:
            self.storage.merge_log_files(merge_all_files=True)
        except (OSError, IOError) as e:
            logger.warning(f"Step logs roll-up failed: {e}")

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
