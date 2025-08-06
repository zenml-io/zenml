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

import asyncio
import logging
import os
import queue
import re
import sys
import threading
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
    LOGS_MERGE_INTERVAL_SECONDS,
    LOGS_STORAGE_MAX_QUEUE_SIZE,
    LOGS_STORAGE_QUEUE_TIMEOUT,
    LOGS_WRITE_INTERVAL_SECONDS,
    handle_bool_env_var,
)
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.models import (
    LogsRequest,
    LogsResponse,
    PipelineDeploymentResponse,
    PipelineRunUpdate,
)
from zenml.utils.io_utils import sanitize_remote_path
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore

# Get the logger
logger = get_logger(__name__)

redirected: ContextVar[bool] = ContextVar("redirected", default=False)

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

LOGS_EXTENSION = ".log"
PIPELINE_RUN_LOGS_FOLDER = "pipeline_runs"


def remove_ansi_escape_codes(text: str) -> str:
    """Auxiliary function to remove ANSI escape codes from a given string.

    Args:
        text: the input string

    Returns:
        the version of the input string where the escape codes are removed.
    """
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
    """Helper class which buffers and stores logs to a given URI using a background thread."""

    def __init__(
        self,
        logs_uri: str,
        artifact_store: "BaseArtifactStore",
        max_queue_size: int = LOGS_STORAGE_MAX_QUEUE_SIZE,
        queue_timeout: int = LOGS_STORAGE_QUEUE_TIMEOUT,
        write_interval: int = LOGS_WRITE_INTERVAL_SECONDS,
        merge_files_interval: int = LOGS_MERGE_INTERVAL_SECONDS,
    ) -> None:
        """Initialization.

        Args:
            logs_uri: the URI of the log file or folder.
            artifact_store: Artifact Store from the current step context
            max_queue_size: maximum number of individual messages to queue.
            queue_timeout: timeout in seconds for putting items in queue when full.
                - Positive value: Wait N seconds, then drop logs if queue still full
                - Negative value: Block indefinitely until queue has space (never drop logs)
            write_interval: the amount of seconds before the created files
                get written to the artifact store.
            merge_files_interval: the amount of seconds before the created files
                get merged into a single file.
        """
        # Parameters
        self.logs_uri = logs_uri
        self.max_queue_size = max_queue_size
        self.queue_timeout = queue_timeout
        self.write_interval = write_interval
        self.merge_files_interval = merge_files_interval

        # State
        self.artifact_store = artifact_store

        # Immutable filesystems state
        self.last_merge_time = time.time()

        # Queue and log storage thread for async processing
        self.log_queue: queue.Queue[str] = queue.Queue(maxsize=max_queue_size)
        self.log_storage_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.merge_event = threading.Event()

        # Start the log storage thread
        self._start_log_storage_thread()

    def _start_log_storage_thread(self) -> None:
        """Start the log storage thread for processing log queue."""
        if (
            self.log_storage_thread is None
            or not self.log_storage_thread.is_alive()
        ):
            self.log_storage_thread = threading.Thread(
                target=self._log_storage_worker,
                name="LogsStorage-Worker",
            )
            self.log_storage_thread.start()

    def _process_log_queue(self, force_merge: bool = False) -> None:
        """Write and merge logs to the artifact store using time-based batching.

        Args:
            force_merge: Whether to force merge the logs.
        """
        try:
            messages = []

            # Get first message (blocking with timeout)
            try:
                first_message = self.log_queue.get(timeout=1)
                messages.append(first_message)
            except queue.Empty:
                return

            # Get any remaining messages without waiting (drain quickly)
            while True:
                try:
                    additional_message = self.log_queue.get_nowait()
                    messages.append(additional_message)
                except queue.Empty:
                    break

            # Write the messages to the artifact store
            if messages:
                self.write_buffer(messages)

            # Merge the log files if needed
            if (
                self._is_merge_needed
                or self.merge_event.is_set()
                or force_merge
            ):
                self.merge_event.clear()

                self.merge_log_files(merge_all_files=force_merge)

        except Exception as e:
            logger.error("Error in log storage thread: %s", e)
        finally:
            for _ in messages:
                self.log_queue.task_done()

            # Wait for the next write interval or until shutdown is requested
            self.shutdown_event.wait(timeout=self.write_interval)

    def _log_storage_worker(self) -> None:
        """Log storage thread worker that processes the log queue."""
        # Process the log queue until shutdown is requested
        while not self.shutdown_event.is_set():
            self._process_log_queue()

        # Shutdown requested - drain remaining queue items and merge log files
        self._process_log_queue(force_merge=True)

    def _shutdown_log_storage_thread(self, timeout: int = 5) -> None:
        """Shutdown the log storage thread gracefully.

        Args:
            timeout: Maximum time to wait for thread shutdown.
        """
        if self.log_storage_thread and self.log_storage_thread.is_alive():
            # Then signal the worker to begin graceful shutdown
            self.shutdown_event.set()

            # Wait for thread to finish (it will drain the queue automatically)
            self.log_storage_thread.join(timeout=timeout)

    def write(self, text: str) -> None:
        """Main write method that sends individual messages directly to queue.

        Args:
            text: the incoming string.
        """
        # Skip empty lines
        if text == "\n":
            return

        # If the current thread is the log storage thread, do nothing
        # to prevent recursion when the storage thread itself generates logs
        if (
            self.log_storage_thread
            and threading.current_thread() == self.log_storage_thread
        ):
            return

        # If the current thread is the fsspec IO thread, do nothing
        if self._is_fsspec_io_thread:
            return

        try:
            # Format the message with timestamp
            timestamp = utc_now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = (
                f"[{timestamp} UTC] {remove_ansi_escape_codes(text)}"
            )
            formatted_message = formatted_message.rstrip()

            # Send individual message directly to queue
            if not self.shutdown_event.is_set():
                try:
                    if self.queue_timeout < 0:
                        # Negative timeout = block indefinitely until queue has space
                        # Guarantees no log loss but may hang application
                        self.log_queue.put(formatted_message)
                    else:
                        # Positive timeout = wait specified time then drop logs
                        # Prevents application hanging but may lose logs
                        self.log_queue.put(
                            formatted_message, timeout=self.queue_timeout
                        )
                except queue.Full:
                    # This only happens with positive timeout
                    # Queue is full - just skip this message to avoid blocking
                    # Better to drop logs than hang the application
                    pass

        except Exception:
            # Silently ignore errors to prevent recursion
            pass

    @property
    def _is_merge_needed(self) -> bool:
        """Checks whether the log files need to be merged.

        Returns:
            whether the log files need to be merged.
        """
        return (
            self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM
            and time.time() - self.last_merge_time > self.merge_files_interval
        )

    @property
    def _is_fsspec_io_thread(self) -> bool:
        """Checks if the current thread is the fsspec IO thread.

        Returns:
            whether the current thread is the fsspec IO thread.
        """
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
            return (
                asyncio.events.get_running_loop() is not None
                and threading.current_thread().name == "fsspecIO"
            )
        except RuntimeError:
            # No running loop
            return False

    def _get_timestamped_filename(self, suffix: str = "") -> str:
        """Returns a timestamped filename.

        Args:
            suffix: optional suffix for the file name

        Returns:
            The timestamped filename.
        """
        return f"{time.time()}{suffix}{LOGS_EXTENSION}"

    def write_buffer(self, buffer_to_write: List[str]) -> None:
        """Write the given buffer to file. This runs in the log storage thread.

        Args:
            buffer_to_write: The buffer contents to write to file.
        """
        if not buffer_to_write:
            return

        # The configured logging handler uses a lock to ensure that
        # logs generated by different threads are not interleaved.
        # Given that most artifact stores are based on fsspec, which
        # use a separate thread for async operations, it may happen that
        # the fsspec library itself will log something, which will end
        # up in a deadlock.
        # To avoid this, we temporarily disable the lock in the logging
        # handler while writing to the file.
        logging_handler = None
        logging_lock = None
        try:
            # Only try to access logging handler if it exists
            root_logger = logging.getLogger()
            if root_logger.handlers:
                logging_handler = root_logger.handlers[0]
                logging_lock = getattr(logging_handler, "lock", None)
                if logging_lock:
                    logging_handler.lock = None

            # If the artifact store is immutable, write the buffer to a new file
            if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
                _logs_uri = self._get_timestamped_filename()
                with self.artifact_store.open(
                    os.path.join(
                        self.logs_uri,
                        _logs_uri,
                    ),
                    "w",
                ) as file:
                    for message in buffer_to_write:
                        file.write(f"{message}\n")

            # If the artifact store is mutable, append the buffer to the existing file
            else:
                with self.artifact_store.open(self.logs_uri, "a") as file:
                    for message in buffer_to_write:
                        file.write(f"{message}\n")
                self.artifact_store._remove_previous_file_versions(
                    self.logs_uri
                )

        finally:
            # Re-enable the logging lock
            if logging_handler and logging_lock:
                logging_handler.lock = logging_lock

    def merge_log_files(self, merge_all_files: bool = False) -> None:
        """Merges all log files into one in the given URI.

        Called on the logging context exit.

        Args:
            merge_all_files: whether to merge all files or only raw files
        """
        # If the artifact store is immutable, merge the log files
        if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
            merged_file_suffix = "_merged"
            files_ = self.artifact_store.listdir(self.logs_uri)
            if not merge_all_files:
                # already merged files will not be merged again
                files_ = [
                    f for f in files_ if merged_file_suffix not in str(f)
                ]
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

            # Update the last merge time
            self.last_merge_time = time.time()

    def send_merge_event(self) -> None:
        """Send a merge event to the log storage thread."""
        self.merge_event.set()


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
        self._original_methods_saved = False

    def __enter__(self) -> "PipelineLogsStorageContext":
        """Enter condition of the context manager.

        Wraps the `write` method of both stderr and stdout, so each incoming
        message gets stored in the pipeline logs storage.

        Returns:
            self
        """
        # Save original write methods (flush methods are not wrapped)
        self.stdout_write = getattr(sys.stdout, "write")
        self.stderr_write = getattr(sys.stderr, "write")
        self._original_methods_saved = True

        # Wrap stdout/stderr write methods only
        # Note: We don't wrap flush() as it's unnecessary overhead and the
        # background thread handles log flushing based on time/buffer size
        setattr(sys.stdout, "write", self._wrap_write(self.stdout_write))
        setattr(sys.stderr, "write", self._wrap_write(self.stderr_write))

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
        # Step 1: Restore stdout/stderr FIRST to prevent logging during shutdown
        try:
            if self._original_methods_saved:
                setattr(sys.stdout, "write", self.stdout_write)
                setattr(sys.stderr, "write", self.stderr_write)
                redirected.set(False)
        except Exception:
            pass

        # Step 2: Shutdown thread (it will automatically drain queue and merge files)
        try:
            self.storage._shutdown_log_storage_thread()
        except Exception:
            pass

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


def setup_orchestrator_logging(
    run_id: UUID,
    deployment: "PipelineDeploymentResponse",
    logs_response: Optional[LogsResponse] = None,
) -> Any:
    """Set up logging for an orchestrator environment.

    This function can be reused by different orchestrators to set up
    consistent logging behavior.

    Args:
        run_id: The pipeline run ID.
        deployment: The deployment of the pipeline run.
        logs_response: The logs response to continue from.

    Returns:
        The logs context (PipelineLogsStorageContext)
    """
    try:
        logging_enabled = True

        if handle_bool_env_var(ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False):
            logging_enabled = False
        else:
            if (
                deployment.pipeline_configuration.enable_pipeline_logs
                is not None
            ):
                logging_enabled = (
                    deployment.pipeline_configuration.enable_pipeline_logs
                )

        if not logging_enabled:
            return nullcontext()

        # Fetch the active stack
        client = Client()
        active_stack = client.active_stack

        if logs_response:
            logs_uri = logs_response.uri
        else:
            logs_uri = prepare_logs_uri(
                artifact_store=active_stack.artifact_store,
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
                    run_id=run_id, run_update=run_update
                )
            except Exception as e:
                logger.error(
                    f"Failed to add orchestrator logs to the run {run_id}: {e}"
                )
                raise e

        return PipelineLogsStorageContext(
            logs_uri=logs_uri,
            artifact_store=active_stack.artifact_store,
            prepend_step_name=False,
        )
    except Exception as e:
        logger.error(
            f"Failed to setup orchestrator logging for run {run_id}: {e}"
        )
        return nullcontext()
