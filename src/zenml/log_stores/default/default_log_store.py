#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Default log store implementation."""

import asyncio
import logging
import os
import queue
import re
import threading
import time
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Iterator,
    List,
    Optional,
    Union,
    cast,
)
from uuid import UUID, uuid4

from zenml.artifact_stores import BaseArtifactStore
from zenml.artifacts.utils import _load_artifact_store
from zenml.client import Client
from zenml.constants import (
    LOGS_MERGE_INTERVAL_SECONDS,
    LOGS_STORAGE_MAX_QUEUE_SIZE,
    LOGS_STORAGE_QUEUE_TIMEOUT,
    LOGS_WRITE_INTERVAL_SECONDS,
)
from zenml.enums import LoggingLevels
from zenml.exceptions import DoesNotExistException
from zenml.log_stores.base_log_store import BaseLogStore
from zenml.log_stores.default.default_log_store_flavor import (
    DefaultLogStoreConfig,
)
from zenml.logger import (
    get_logger,
    get_storage_log_level,
    logging_handlers,
)
from zenml.logging.step_logging import (
    DEFAULT_MESSAGE_SIZE,
    MAX_ENTRIES_PER_REQUEST,
    LogEntry,
)
from zenml.models import (
    LogsRequest,
    LogsResponse,
)
from zenml.utils.io_utils import sanitize_remote_path
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.logging.step_logging import (
        ArtifactStoreHandler,
        LogEntry,
        PipelineLogsStorage,
    )

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

logger = get_logger(__name__)


LOGS_EXTENSION = ".log"


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
    log_id: UUID,
) -> str:
    """Generates and prepares a URI for the log file or folder for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        log_id: The ID of the logs entity

    Returns:
        The URI of the log storage (file or folder).
    """
    logs_base_uri = os.path.join(artifact_store.path, "logs")

    if not artifact_store.exists(logs_base_uri):
        artifact_store.makedirs(logs_base_uri)

    if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
        logs_uri = os.path.join(logs_base_uri, log_id)
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs directory {logs_uri} already exists! Removing old log directory..."
            )
            artifact_store.rmtree(logs_uri)

        artifact_store.makedirs(logs_uri)
    else:
        logs_uri = os.path.join(logs_base_uri, f"{log_id}{LOGS_EXTENSION}")
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs file {logs_uri} already exists! Removing old log file..."
            )
            artifact_store.remove(logs_uri)

    return sanitize_remote_path(logs_uri)


def fetch_log_records(
    zen_store: "BaseZenStore",
    artifact_store_id: Union[str, UUID],
    logs_uri: str,
) -> List[LogEntry]:
    """Fetches log entries.

    Args:
        zen_store: The store in which the artifact is stored.
        artifact_store_id: The ID of the artifact store.
        logs_uri: The URI of the artifact (file or directory).

    Returns:
        List of log entries.
    """
    log_entries = []

    for line in _stream_logs_line_by_line(
        zen_store, artifact_store_id, logs_uri
    ):
        if log_entry := parse_log_entry(line):
            log_entries.append(log_entry)

        if len(log_entries) >= MAX_ENTRIES_PER_REQUEST:
            break

    return log_entries


def _stream_logs_line_by_line(
    zen_store: "BaseZenStore",
    artifact_store_id: Union[str, UUID],
    logs_uri: str,
) -> Iterator[str]:
    """Stream logs line by line without loading the entire file into memory.

    This generator yields log lines one by one, handling both single files
    and directories with multiple log files.

    Args:
        zen_store: The store in which the artifact is stored.
        artifact_store_id: The ID of the artifact store.
        logs_uri: The URI of the log file or directory.

    Yields:
        Individual log lines as strings.

    Raises:
        DoesNotExistException: If the artifact does not exist in the artifact store.
    """
    artifact_store = _load_artifact_store(artifact_store_id, zen_store)

    try:
        if not artifact_store.isdir(logs_uri):
            # Single file case
            with artifact_store.open(logs_uri, "r") as file:
                for line in file:
                    yield line.rstrip("\n\r")
        else:
            # Directory case - may contain multiple log files
            files = artifact_store.listdir(logs_uri)
            if not files:
                raise DoesNotExistException(
                    f"Folder '{logs_uri}' is empty in artifact store "
                    f"'{artifact_store.name}'."
                )

            # Sort files to read them in order
            files.sort()

            for file in files:
                file_path = os.path.join(logs_uri, str(file))
                with artifact_store.open(file_path, "r") as f:
                    for line in f:
                        yield line.rstrip("\n\r")
    finally:
        artifact_store.cleanup()


def parse_log_entry(log_line: str) -> Optional[LogEntry]:
    """Parse a single log entry into a LogEntry object.

    Handles two formats:
    1. JSON format: {"timestamp": "...", "level": "...", "message": "...", "location": "..."}
       Uses Pydantic's model_validate_json for automatic parsing and validation.
    2. Plain text: Any other text (defaults to INFO level)

    Args:
        log_line: A single log line to parse

    Returns:
        LogEntry object. For JSON logs, all fields are validated and parsed automatically.
        For plain text logs, only message is populated with INFO level default.
        Returns None only for empty lines.
    """
    line = log_line.strip()
    if not line:
        return None

    if line.startswith("{") and line.endswith("}"):
        try:
            return LogEntry.model_validate_json(line)
        except Exception:
            pass

    old_format = re.search(
        r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+UTC\]", line
    )

    timestamp = None
    if old_format:
        timestamp = old_format.group(1) + "Z"
        line = line.replace(old_format.group(0), "").strip()

    return LogEntry(
        message=line,
        name=None,
        level=LoggingLevels.INFO,
        timestamp=timestamp,
    )


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
            # Send individual message directly to queue
            if not self.shutdown_event.is_set():
                try:
                    if self.queue_timeout < 0:
                        # Negative timeout = block indefinitely until queue has space
                        # Guarantees no log loss but may hang application
                        self.log_queue.put(text)
                    else:
                        # Positive timeout = wait specified time then drop logs
                        # Prevents application hanging but may lose logs
                        self.log_queue.put(text, timeout=self.queue_timeout)
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

        try:
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

        except Exception as e:
            logger.error("Error in log storage thread: %s", e)

    def merge_log_files(self, merge_all_files: bool = False) -> None:
        """Merges all log files into one in the given URI.

        Called on the logging context exit.

        Args:
            merge_all_files: whether to merge all files or only raw files
        """
        from zenml.artifacts.utils import (
            _load_file_from_artifact_store,
        )

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


class ArtifactStoreHandler(logging.Handler):
    """Handler that writes log messages to artifact store storage."""

    def __init__(self, storage: "PipelineLogsStorage"):
        """Initialize the handler with a storage instance.

        Args:
            storage: The PipelineLogsStorage instance to write to.
        """
        super().__init__()
        self.storage = storage

        # Get storage log level from environment
        self.setLevel(get_storage_log_level().value)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the storage.

        Args:
            record: The log record to emit.
        """
        try:
            # Get level enum
            level = LoggingLevels.__members__.get(record.levelname.upper())

            # Get the message
            message = self.format(record)
            message = remove_ansi_escape_codes(message).rstrip()

            # Check if message needs to be chunked
            message_bytes = message.encode("utf-8")
            if len(message_bytes) <= DEFAULT_MESSAGE_SIZE:
                # Message is small enough, emit as-is
                log_record = LogEntry.model_construct(
                    message=message,
                    name=record.name,
                    level=level,
                    timestamp=utc_now(tz_aware=True),
                    module=record.module,
                    filename=record.filename,
                    lineno=record.lineno,
                )
                json_line = log_record.model_dump_json(exclude_none=True)
                self.storage.write(json_line)
            else:
                # Message is too large, split into chunks and emit each one
                chunks = self._split_to_chunks(message)
                entry_id = uuid4()
                for i, chunk in enumerate(chunks):
                    log_record = LogEntry.model_construct(
                        message=chunk,
                        name=record.name,
                        level=level,
                        module=record.module,
                        filename=record.filename,
                        lineno=record.lineno,
                        timestamp=utc_now(tz_aware=True),
                        chunk_index=i,
                        total_chunks=len(chunks),
                        id=entry_id,
                    )

                    json_line = log_record.model_dump_json(exclude_none=True)
                    self.storage.write(json_line)
        except Exception:
            pass

    def _split_to_chunks(self, message: str) -> List[str]:
        """Split a large message into chunks.

        Args:
            message: The message to split.

        Returns:
            A list of message chunks.
        """
        # Calculate how many chunks we need
        message_bytes = message.encode("utf-8")

        # Split the message into chunks, handling UTF-8 boundaries
        chunks = []
        start = 0

        while start < len(message_bytes):
            # Calculate the end position for this chunk
            end = min(start + DEFAULT_MESSAGE_SIZE, len(message_bytes))

            # Try to decode the chunk, backing up if we hit a UTF-8 boundary issue
            while end > start:
                chunk_bytes = message_bytes[start:end]
                try:
                    chunk_text = chunk_bytes.decode("utf-8")
                    chunks.append(chunk_text)
                    break
                except UnicodeDecodeError:
                    # If we can't decode, try a smaller chunk
                    end -= 1
            else:
                # If we can't decode anything, use replacement characters
                end = min(start + DEFAULT_MESSAGE_SIZE, len(message_bytes))
                chunks.append(
                    message_bytes[start:end].decode("utf-8", errors="replace")
                )

            start = end

        return chunks


class DefaultLogStore(BaseLogStore):
    """Log store that saves logs to the artifact store.

    This implementation uses the artifact store as the backend for log storage,
    maintaining backward compatibility with existing ZenML behavior. Logs are
    written to the artifact store using a background thread and queue for
    efficient batching.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the default log store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        client = Client()
        self._artifact_store = client.active_stack.artifact_store

        self.storage: Optional["PipelineLogsStorage"] = None
        self.handler: Optional["ArtifactStoreHandler"] = None

        self.uri: Optional[str] = None
        self.artifact_store_id: Optional[UUID] = None

        self._original_root_level: Optional[int] = None

    @property
    def config(self) -> DefaultLogStoreConfig:
        """Returns the configuration of the default log store.

        Returns:
            The configuration.
        """
        return cast(DefaultLogStoreConfig, self._config)

    def activate(
        self,
        log_request: "LogsRequest",
    ) -> None:
        """Activate log collection to the artifact store.

        Args:
            log_request: The log request model.
        """
        logs_uri = prepare_logs_uri(
            log_id=log_request.id,
            artifact_store=self._artifact_store,
        )

        # Create storage and handler
        self.storage = PipelineLogsStorage(
            logs_uri=logs_uri,
            artifact_store=self._artifact_store,
        )
        self.handler = ArtifactStoreHandler(self.storage)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.handler)

        # Set root logger level to minimum of all handlers
        self._original_root_level = root_logger.level
        handler_levels = [handler.level for handler in root_logger.handlers]
        min_level = min(handler_levels)
        if min_level < root_logger.level:
            root_logger.setLevel(min_level)

        # Add to context variables for print capture
        logging_handlers.add(self.handler)

    def deactivate(self) -> None:
        """Deactivate log collection and flush remaining logs."""
        if not self.handler:
            return

        # Remove handler from root logger
        root_logger = logging.getLogger()
        if self.handler in root_logger.handlers:
            root_logger.removeHandler(self.handler)

        # Restore original root logger level
        if self._original_root_level is not None:
            root_logger.setLevel(self._original_root_level)

        # Remove from context variables
        logging_handlers.remove(self.handler)

        # Shutdown storage thread (flushes and merges logs)
        if self.storage:
            try:
                self.storage._shutdown_log_storage_thread()
            except Exception as e:
                logger.warning(f"Error shutting down log storage: {e}")

        logger.debug("DefaultLogStore deactivated")

    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List["LogEntry"]:
        """Fetch logs from the artifact store.

        Args:
            logs_model: The logs model containing uri and artifact_store_id.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries from the artifact store.

        Raises:
            ValueError: If logs_model.uri is not provided.
        """
        from zenml.logging.step_logging import fetch_log_records

        if not logs_model.uri:
            raise ValueError(
                "logs_model.uri is required for DefaultLogStore.fetch()"
            )

        if not logs_model.artifact_store_id:
            raise ValueError(
                "logs_model.artifact_store_id is required for DefaultLogStore.fetch()"
            )

        client = Client()
        log_entries = fetch_log_records(
            zen_store=client.zen_store,
            artifact_store_id=logs_model.artifact_store_id,
            logs_uri=logs_model.uri,
        )

        if start_time or end_time:
            filtered_entries = []
            for entry in log_entries:
                if entry.timestamp:
                    if start_time and entry.timestamp < start_time:
                        continue
                    if end_time and entry.timestamp > end_time:
                        continue
                filtered_entries.append(entry)
            log_entries = filtered_entries

        return log_entries[:limit]
