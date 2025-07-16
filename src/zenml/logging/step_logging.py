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
from datetime import datetime
from types import TracebackType
from typing import Any, List, Optional, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.artifact_stores import BaseArtifactStore
from zenml.artifacts.utils import (
    _load_artifact_store,
    _load_file_from_artifact_store,
    _strip_timestamp_from_multiline_string,
)
from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_CAPTURE_PRINTS,
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger, get_storage_log_level
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
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# Context variables
redirected: ContextVar[bool] = ContextVar("redirected", default=False)
step_names_in_console: ContextVar[bool] = ContextVar(
    "step_names_in_console", default=False
)

# Context variable for logging handlers
logging_handlers: ContextVar[List[logging.Handler]] = ContextVar(
    "logging_handlers", default=[]
)

LOGS_EXTENSION = ".log"
PIPELINE_RUN_LOGS_FOLDER = "pipeline_runs"
MAX_LOG_ENTRIES = 100  # Maximum number of log entries to return in a single request
MAX_MESSAGE_SIZE = 10 * 1024  # Maximum size of a single log message in bytes (10KB)


class LogEntry(BaseModel):
    """A structured log entry with parsed information."""

    message: str = Field(description="The log message content")
    name: Optional[str] = Field(
        default=None,
        description="The name of the logger",
    )
    level: Optional[LoggingLevels] = Field(
        default=None,
        description="The log level",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the log was created",
    )
    module: Optional[str] = Field(
        default=None, description="The module that generated this log entry"
    )
    filename: Optional[str] = Field(
        default=None,
        description="The name of the file that generated this log entry",
    )
    lineno: Optional[int] = Field(
        default=None, description="The fileno that generated this log entry"
    )


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
            message = record.getMessage()

            # Check if message needs to be chunked
            message_bytes = message.encode("utf-8")
            if len(message_bytes) <= MAX_MESSAGE_SIZE:
                # Message is small enough, emit as-is
                log_record = LogEntry(
                    message=message,
                    name=record.name,
                    level=level,
                    timestamp=utc_now(),
                    module=record.module,
                    filename=record.filename,
                    lineno=record.lineno,
                )
                json_line = log_record.model_dump_json(exclude_none=True)
                self.storage.write(json_line)
            else:
                # Message is too large, split into chunks and emit each one
                chunks = self._split_to_chunks(message)
                for i, chunk in enumerate(chunks):
                    chunk_message = f"{chunk} (chunk {i + 1}/{len(chunks)})"

                    log_record = LogEntry(
                        message=chunk_message,
                        name=record.name,
                        level=level,
                        module=record.module,
                        filename=record.filename,
                        lineno=record.lineno,
                        timestamp=utc_now(),
                    )

                    json_line = log_record.model_dump_json(exclude_none=True)
                    self.storage.write(json_line)
        except Exception:
            # Don't let storage errors break logging
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
        chunk_count = (
            len(message_bytes) + MAX_MESSAGE_SIZE - 1
        ) // MAX_MESSAGE_SIZE

        # Split the message into chunks
        chunks = []
        start = 0
        for i in range(chunk_count):
            # Calculate the end position for this chunk
            end = min(start + MAX_MESSAGE_SIZE, len(message_bytes))

            # Extract the chunk and decode it
            chunk_bytes = message_bytes[start:end]

            # Handle potential UTF-8 boundary issues
            try:
                chunk_text = chunk_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # If we cut in the middle of a UTF-8 character, back off until we find a valid boundary
                while len(chunk_bytes) > 0:
                    try:
                        chunk_text = chunk_bytes.decode("utf-8")
                        break
                    except UnicodeDecodeError:
                        chunk_bytes = chunk_bytes[:-1]
                        end -= 1
                else:
                    # If we can't decode anything, skip this chunk
                    start = end
                    continue

            chunks.append(chunk_text)
            start = end

        return chunks


def setup_global_print_wrapping() -> None:
    """Set up global print() wrapping with context-aware handlers."""
    # Check if we should capture prints
    capture_prints = handle_bool_env_var(
        ENV_ZENML_CAPTURE_PRINTS, default=True
    )

    if not capture_prints:
        return

    # Check if already wrapped to avoid double wrapping
    if hasattr(__builtins__, "_zenml_original_print"):
        return

    import builtins

    original_print = builtins.print

    def wrapped_print(*args, **kwargs):
        # Convert print arguments to message
        message = " ".join(str(arg) for arg in args)

        # Determine if this should go to stderr or stdout based on file argument
        file_arg = kwargs.get("file", sys.stdout)

        # Call active handlers first (for storage)
        if message.strip():
            if file_arg == sys.stderr:
                handlers = logging_handlers.get()
                level = logging.ERROR
            else:
                handlers = logging_handlers.get()
                level = logging.INFO

            for handler in handlers:
                try:
                    # Create a LogRecord for the handler
                    record = logging.LogRecord(
                        name="print",
                        level=level,
                        pathname="",
                        lineno=0,
                        msg=message,
                        args=(),
                        exc_info=None,
                    )
                    # Check if handler's level would accept this record
                    if record.levelno >= handler.level:
                        handler.emit(record)
                except Exception:
                    # Don't let handler errors break print
                    pass

        # Then call original print for console display
        return original_print(*args, **kwargs)

    # Store original and replace print
    setattr(builtins, '_zenml_original_print', original_print)
    builtins.print = wrapped_print


def remove_ansi_escape_codes(text: str) -> str:
    """Auxiliary function to remove ANSI escape codes from a given string.

    Args:
        text: the input string

    Returns:
        the version of the input string where the escape codes are removed.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


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
    stripped_line = log_line.strip()
    if not stripped_line:
        return None

    # Try to parse JSON format first
    if stripped_line.startswith("{") and stripped_line.endswith("}"):
        try:
            return LogEntry.model_validate_json(stripped_line)
        except Exception:
            # If JSON parsing or validation fails, treat as plain text
            pass

    # For any other format (plain text), create LogEntry with defaults
    return LogEntry(
        message=stripped_line,
        name=None,  # No logger name available for plain text logs
        level=LoggingLevels.INFO,  # Default level for plain text logs
        timestamp=None,  # No timestamp available for plain text logs
    )


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


def fetch_log_records(
    zen_store: "BaseZenStore",
    artifact_store_id: Union[str, UUID],
    logs_uri: str,
    offset: int = 0,
    count: int = MAX_LOG_ENTRIES,  # Number of entries to return
    level: Optional[str] = None,
    search: Optional[str] = None,
) -> List[LogEntry]:
    """Fetches the logs from the artifact store and parses them into LogEntry objects.

    This implementation uses streaming to efficiently handle large log files by:
    
    1. Reading logs line by line instead of loading everything into memory
    2. Applying filters as we go to avoid processing unnecessary data  
    3. Stopping once we have the required number of filtered entries

    Args:
        zen_store: The store in which the artifact is stored.
        artifact_store_id: The ID of the artifact store.
        logs_uri: The URI of the artifact.
        offset: The entry index from which to start reading (0-based) from filtered results.
        count: The number of entries to return (max MAX_LOG_ENTRIES).
        level: Optional log level filter. Returns messages at this level and above.
        search: Optional search string. Only returns messages containing this string.

    Returns:
        A list of LogEntry objects starting from the specified offset in the filtered results.

    Raises:
        DoesNotExistException: If the artifact does not exist in the artifact
            store.
    """
    # We need to find (offset + count) matching entries total
    target_total = offset + count
    matching_entries = []
    entries_found = 0
    
    # Stream logs line by line instead of reading everything
    try:
        for line in _stream_logs_line_by_line(
            zen_store=zen_store,
            artifact_store_id=artifact_store_id, 
            logs_uri=logs_uri,
        ):
            if not line.strip():
                continue
                
            log_entry = parse_log_entry(line)
            if not log_entry:
                continue
                
            # Check if this entry matches our filters
            if _entry_matches_filters(log_entry, level, search):
                entries_found += 1
                
                # Only start collecting after we've skipped 'offset' entries
                if entries_found > offset:
                    matching_entries.append(log_entry)
                    
                # Stop reading once we have enough entries
                if entries_found >= target_total:
                    break
                    
        return matching_entries
        
    except DoesNotExistException:
        # Re-raise DoesNotExistException as-is
        raise
    except Exception as e:
        # For any other errors during streaming, fall back to empty result
        logger.warning(f"Error streaming logs from {logs_uri}: {e}")
        return []


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


def _stream_logs_line_by_line(
    zen_store: "BaseZenStore",
    artifact_store_id: Union[str, UUID],
    logs_uri: str,
) -> Any:
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


def _entry_matches_filters(
    entry: LogEntry, 
    level: Optional[str] = None, 
    search: Optional[str] = None
) -> bool:
    """Check if a log entry matches the given filters.
    
    Args:
        entry: The log entry to check.
        level: Optional log level filter. Returns messages at this level and above.
        search: Optional search string. Only returns messages containing this string.
        
    Returns:
        True if the entry matches all filters, False otherwise.
    """
    # Apply level filter
    if level:
        try:
            min_level = LoggingLevels[level.upper()]
            if not entry.level or entry.level.value < min_level.value:
                return False
        except KeyError:
            # If invalid level provided, ignore the filter
            pass
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        if search_lower not in entry.message.lower():
            return False
    
    return True



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
            self.buffer.append(remove_ansi_escape_codes(text).rstrip())
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


class PipelineLogsStorageContext:
    """Context manager which collects logs during pipeline run execution."""

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
        self.artifact_store_handler: Optional[ArtifactStoreHandler] = None
        self.prepend_step_name = prepend_step_name

    def __enter__(self) -> "PipelineLogsStorageContext":
        """Enter condition of the context manager.

        Creates and registers an ArtifactStoreHandler for log storage.

        Returns:
            self
        """
        # Create storage handler
        self.artifact_store_handler = ArtifactStoreHandler(self.storage)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.artifact_store_handler)

        # Set root logger level to minimum of all active handlers
        # This ensures records can reach any handler that needs them
        self.original_root_level = root_logger.level
        handler_levels = [handler.level for handler in root_logger.handlers]

        # Set root logger to the minimum level among all handlers
        min_level = min(handler_levels)
        if min_level < root_logger.level:
            root_logger.setLevel(min_level)

        # Add handler to context variables for print() capture
        handlers = logging_handlers.get().copy()
        handlers.append(self.artifact_store_handler)
        logging_handlers.set(handlers)

        # Set the step names context variable
        step_names_disabled = handle_bool_env_var(
            ENV_ZENML_DISABLE_STEP_NAMES_IN_LOGS, default=False
        )

        if step_names_disabled or not self.prepend_step_name:
            # Step names are disabled through the env or they are disabled in the config
            step_names_in_console.set(False)
        else:
            # Otherwise, set it True (default)
            step_names_in_console.set(True)

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

        Removes the handler from loggers and context variables.
        """
        # Remove handler from root logger and restore original level
        if self.artifact_store_handler:
            root_logger = logging.getLogger()
            # Check if handler is still in the root logger before removing
            if self.artifact_store_handler in root_logger.handlers:
                root_logger.removeHandler(self.artifact_store_handler)
            # Restore original root logger level
            if hasattr(self, "original_root_level"):
                root_logger.setLevel(self.original_root_level)

        # Remove handler from context variables
        handlers = logging_handlers.get().copy()
        if self.artifact_store_handler in handlers:
            handlers.remove(self.artifact_store_handler)
        logging_handlers.set(handlers)

        # Force save any remaining logs
        self.storage.save_to_file(force=True)

        # Clean up handler reference
        self.artifact_store_handler = None

        redirected.set(False)

        try:
            self.storage.merge_log_files(merge_all_files=True)
        except (OSError, IOError) as e:
            logger.warning(f"Step logs roll-up failed: {e}")

        # Reset the step names context to default
        step_names_in_console.set(False)


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
