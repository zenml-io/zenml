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

import logging
import os
import re
import sys
import time
from contextlib import nullcontext
from contextvars import ContextVar
from types import TracebackType
from typing import Any, Callable, List, Optional, Type, Union
from uuid import UUID, uuid4

from zenml import get_step_context
from zenml.artifact_stores import BaseArtifactStore
from zenml.artifacts.utils import (
    _load_artifact_store,
    _load_file_from_artifact_store,
    _strip_timestamp_from_multiline_string,
)
from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS,
    handle_bool_env_var,
)
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.logging import (
    STEP_LOGS_STORAGE_INTERVAL_SECONDS,
    STEP_LOGS_STORAGE_MAX_MESSAGES,
    STEP_LOGS_STORAGE_MERGE_INTERVAL_SECONDS,
)
from zenml.models import (
    LogsRequest,
    PipelineDeploymentResponse,
    PipelineRunUpdate,
)
from zenml.utils.io_utils import sanitize_remote_path
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore

# Get the logger
logger = get_logger(__name__)

redirected: ContextVar[bool] = ContextVar("redirected", default=False)

LOGS_EXTENSION = ".log"
PIPELINE_RUN_LOGS_FOLDER = "pipeline_runs"


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
    step_name: Optional[str] = None,
    log_key: Optional[str] = None,
) -> str:
    """Generates and prepares a URI for the log file or folder for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        step_name: Name of the step. Skipped for global pipeline run logs.
        log_key: The unique identification key of the log file.

    Returns:
        The URI of the log storage (file or folder).
    """
    if log_key is None:
        log_key = str(uuid4())

    subfolder = step_name or PIPELINE_RUN_LOGS_FOLDER
    logs_base_uri = os.path.join(artifact_store.path, subfolder, "logs")

    # Create the dir
    if not artifact_store.exists(logs_base_uri):
        artifact_store.makedirs(logs_base_uri)

    # Delete the file if it already exists
    if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
        logs_uri = os.path.join(logs_base_uri, log_key)
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs directory {logs_uri} already exists! Removing old log directory..."
            )
            artifact_store.rmtree(logs_uri)

        artifact_store.makedirs(logs_uri)
    else:
        logs_uri = os.path.join(logs_base_uri, f"{log_key}{LOGS_EXTENSION}")
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs file {logs_uri} already exists! Removing old log file..."
            )
            artifact_store.remove(logs_uri)

    return sanitize_remote_path(logs_uri)


def fetch_logs(
    zen_store: "BaseZenStore",
    artifact_store_id: Union[str, UUID],
    logs_uri: str,
    offset: int = 0,
    length: int = 1024 * 1024 * 16,  # Default to 16MiB of data
    strip_timestamp: bool = False,
) -> str:
    """Fetches the logs from the artifact store.

    Args:
        zen_store: The store in which the artifact is stored.
        artifact_store_id: The ID of the artifact store.
        logs_uri: The URI of the artifact.
        offset: The offset from which to start reading.
        length: The amount of bytes that should be read.
        strip_timestamp: Whether to strip timestamps in logs or not

    Returns:
        The logs as a string.

    Raises:
        DoesNotExistException: If the artifact does not exist in the artifact
            store.
    """

    def _read_file(
        uri: str,
        offset: int = 0,
        length: Optional[int] = None,
        strip_timestamp: bool = False,
    ) -> str:
        file_content = str(
            _load_file_from_artifact_store(
                uri,
                artifact_store=artifact_store,
                mode="rb",
                offset=offset,
                length=length,
            ).decode()
        )
        if strip_timestamp:
            file_content = _strip_timestamp_from_multiline_string(file_content)
        return file_content

    artifact_store = _load_artifact_store(artifact_store_id, zen_store)
    try:
        if not artifact_store.isdir(logs_uri):
            return _read_file(logs_uri, offset, length, strip_timestamp)
        else:
            files = artifact_store.listdir(logs_uri)
            if len(files) == 1:
                return _read_file(
                    os.path.join(logs_uri, str(files[0])),
                    offset,
                    length,
                    strip_timestamp,
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
                            strip_timestamp,
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


class PipelineLogsStorage:
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
            # Add timestamp to the message when it's received
            timestamp = utc_now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = (
                f"[{timestamp} UTC] {remove_ansi_escape_codes(text)}"
            )
            self.buffer.append(formatted_message.rstrip())
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
        import asyncio
        import threading

        # Most artifact stores are based on fsspec, which converts between
        # sync and async operations by using a separate AIO thread.
        # It may happen that the fsspec call itself will log something,
        # which will trigger this method, which may then use fsspec again,
        # causing a "Calling sync() from within a running loop" error, because
        # the fsspec library does not expect sync calls being made as a result
        # of a logging call made by itself.
        # To avoid this, we simply check if we're running in the fsspec AIO
        # thread and skip the save if that's the case.
        try:
            if (
                asyncio.events.get_running_loop() is not None
                and threading.current_thread().name == "fsspecIO"
            ):
                return
        except RuntimeError:
            # No running loop
            pass

        if not self.disabled and (self._is_write_needed or force):
            # IMPORTANT: keep this as the first code line in this method! The
            # code that follows might still emit logging messages, which will
            # end up triggering this method again, causing an infinite loop.
            self.disabled = True

            try:
                # The configured logging handler uses a lock to ensure that
                # logs generated by different threads are not interleaved.
                # Given that most artifact stores are based on fsspec, which
                # use a separate thread for async operations, it may happen that
                # the fsspec library itself will log something, which will end
                # up in a deadlock.
                # To avoid this, we temporarily disable the lock in the logging
                # handler while writing to the file.
                logging_handler = logging.getLogger().handlers[0]
                logging_lock = logging_handler.lock
                logging_handler.lock = None

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
                                file.write(f"{message}\n")
                    else:
                        with self.artifact_store.open(
                            self.logs_uri, "a"
                        ) as file:
                            for message in self.buffer:
                                file.write(f"{message}\n")
                        self.artifact_store._remove_previous_file_versions(
                            self.logs_uri
                        )

            except (OSError, IOError) as e:
                # This exception can be raised if there are issues with the
                # underlying system calls, such as reaching the maximum number
                # of open files, permission issues, file corruption, or other
                # I/O errors.
                logger.error(f"Error while trying to write logs: {e}")
            finally:
                # Restore the original logging handler lock
                logging_handler.lock = logging_lock

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


class PipelineLogsStorageContext:
    """Context manager which patches stdout and stderr during pipeline run execution."""

    def __init__(
        self,
        logs_uri: str,
        artifact_store: "BaseArtifactStore",
        prepend_step_name: bool = True,
    ) -> None:
        """Initializes and prepares a storage object.

        Args:
            logs_uri: the URI of the logs file.
            artifact_store: Artifact Store from the current pipeline run context.
            prepend_step_name: Whether to prepend the step name to the logs.
        """
        self.storage = PipelineLogsStorage(
            logs_uri=logs_uri, artifact_store=artifact_store
        )
        self.prepend_step_name = prepend_step_name

    def __enter__(self) -> "PipelineLogsStorageContext":
        """Enter condition of the context manager.

        Wraps the `write` method of both stderr and stdout, so each incoming
        message gets stored in the pipeline logs storage.

        Returns:
            self
        """
        self.stdout_write = getattr(sys.stdout, "write")
        self.stdout_flush = getattr(sys.stdout, "flush")

        self.stderr_write = getattr(sys.stderr, "write")
        self.stderr_flush = getattr(sys.stderr, "flush")

        setattr(sys.stdout, "write", self._wrap_write(self.stdout_write))
        setattr(sys.stdout, "flush", self._wrap_flush(self.stdout_flush))

        setattr(sys.stderr, "write", self._wrap_write(self.stderr_write))
        setattr(sys.stderr, "flush", self._wrap_flush(self.stderr_flush))

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
            step_names_disabled = (
                handle_bool_env_var(
                    ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS, default=False
                )
                or not self.prepend_step_name
            )

            if step_names_disabled:
                output = method(*args, **kwargs)
            else:
                message = args[0]
                # Try to get step context if not available yet
                step_context = None
                try:
                    step_context = get_step_context()
                except Exception:
                    pass

                if step_context and args[0] not in ["\n", ""]:
                    # For progress bar updates (with \r), inject the step name after the \r
                    if "\r" in message:
                        message = message.replace(
                            "\r", f"\r[{step_context.step_name}] "
                        )
                    else:
                        message = f"[{step_context.step_name}] {message}"

                output = method(message, *args[1:], **kwargs)

            # Save the original message without step name prefix to storage
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


def setup_orchestrator_logging(
    run_id: str, deployment: "PipelineDeploymentResponse"
) -> Any:
    """Set up logging for an orchestrator environment.

    This function can be reused by different orchestrators to set up
    consistent logging behavior.

    Args:
        run_id: The pipeline run ID.
        deployment: The deployment of the pipeline run.

    Returns:
        The logs context (PipelineLogsStorageContext)
    """
    try:
        step_logging_enabled = True

        # Check whether logging is enabled
        if handle_bool_env_var(ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False):
            step_logging_enabled = False
        else:
            if (
                deployment.pipeline_configuration.enable_pipeline_logs
                is not None
            ):
                step_logging_enabled = (
                    deployment.pipeline_configuration.enable_pipeline_logs
                )

        if not step_logging_enabled:
            return nullcontext()

        # Fetch the active stack
        client = Client()
        active_stack = client.active_stack

        # Configure the logs
        logs_uri = prepare_logs_uri(
            artifact_store=active_stack.artifact_store,
        )

        logs_context = PipelineLogsStorageContext(
            logs_uri=logs_uri,
            artifact_store=active_stack.artifact_store,
            prepend_step_name=False,
        )

        logs_model = LogsRequest(
            uri=logs_uri,
            source="orchestrator",
            artifact_store_id=active_stack.artifact_store.id,
        )

        # Add orchestrator logs to the pipeline run
        try:
            run_update = PipelineRunUpdate(add_logs=[logs_model])
            client.zen_store.update_run(
                run_id=UUID(run_id), run_update=run_update
            )
        except Exception as e:
            logger.error(
                f"Failed to add orchestrator logs to the run {run_id}: {e}"
            )
            raise e
        return logs_context
    except Exception as e:
        logger.error(
            f"Failed to setup orchestrator logging for run {run_id}: {e}"
        )
        return nullcontext()
