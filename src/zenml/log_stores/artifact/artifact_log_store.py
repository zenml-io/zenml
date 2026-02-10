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
"""Artifact log store implementation."""

import base64
import json
import os
import re
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

from opentelemetry.sdk._logs.export import LogExporter

from zenml.artifact_stores import BaseArtifactStore
from zenml.enums import LoggingLevels, StackComponentType
from zenml.exceptions import DoesNotExistException
from zenml.log_stores import BaseLogStore
from zenml.log_stores.base_log_store import BaseLogStoreOrigin
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.log_stores.otel.otel_log_store import (
    OtelLogStore,
    OtelLogStoreOrigin,
)
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.models.v2.misc.log_models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
)
from zenml.utils.io_utils import sanitize_remote_path

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

logger = get_logger(__name__)


LOGS_EXTENSION = ".log"
END_OF_STREAM_MESSAGE = "END_OF_STREAM"
CHUNK_SIZE = 256 * 1024  # 256KB


class CursorToken(NamedTuple):
    """Cursor token payload for artifact-store logs.

    `offset` is a byte offset pointing to the start of a log line within the
    referenced file.
    """

    file_idx: int
    offset: int


def _encode_cursor(*, pos: "CursorToken") -> str:
    """Encode a cursor position into a base64 string.

    Since the token is used to paginate logs, it needs to be URL-safe.

    Args:
        pos: The cursor position.

    Returns:
        The base64 encoded string.
    """
    payload = {
        "file_idx": int(pos.file_idx),
        "offset": int(pos.offset),
    }
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("ascii")


def _decode_cursor(*, token: str) -> "CursorToken":
    """Decode a cursor position from a base64 string.

    Args:
        token: The base64 encoded string.

    Returns:
        The cursor position.
    """
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    decoded = json.loads(raw.decode("utf-8"))

    file_idx = int(decoded["file_idx"])
    offset = int(decoded["offset"])
    if file_idx < 0 or offset < 0:
        raise ValueError("Invalid cursor position.")

    return CursorToken(file_idx=file_idx, offset=offset)


def _matches_filter(entry: LogEntry, filter_: LogsEntriesFilter) -> bool:
    """Check if a log entry matches the filter.

    Args:
        entry: The log entry to check.
        filter_: The filter to apply.

    Returns:
        True if the log entry matches the filter, False otherwise.
    """
    if filter_.level is not None:
        if entry.level is None or entry.level != filter_.level:
            return False

    if filter_.since is not None:
        if entry.timestamp is None or entry.timestamp < filter_.since:
            return False

    if filter_.until is not None:
        if entry.timestamp is None or entry.timestamp > filter_.until:
            return False

    if filter_.search is not None:
        needle = filter_.search.lower().strip()
        if needle and needle not in entry.message.lower():
            return False

    return True


def _get_logs_file_paths(
    artifact_store: "BaseArtifactStore", logs_uri: str
) -> List[str]:
    """Get the paths of the log files in the artifact store.

    Args:
        artifact_store: The artifact store.
        logs_uri: The URI of the log file or directory.

    Returns:
        A list of paths of the log files in the artifact store.
    """
    if not artifact_store.exists(logs_uri):
        return []

    if not artifact_store.isdir(logs_uri):
        return [logs_uri]

    files = artifact_store.listdir(logs_uri)
    files.sort()
    return [os.path.join(logs_uri, str(f)) for f in files]


def iterate_forward(
    artifact_store: "BaseArtifactStore",
    paths: Sequence[str],
    starting_position: Optional[CursorToken],
) -> Generator[Tuple[CursorToken, str], None, None]:
    """Iterate log lines forward (oldest to newest).

    Args:
        artifact_store: The artifact store.
        paths: The paths of the log files.
        starting_position: The starting position of the iteration.

    Returns:
        A generator of tuples containing the cursor token and the log line.

    Raises:
        ValueError: If the starting position is out of range.
    """
    start_file_idx = (
        starting_position.file_idx if starting_position is not None else 0
    )
    if start_file_idx < 0 or start_file_idx >= len(paths):
        raise ValueError("Cursor file index is out of range.")

    for file_idx in range(start_file_idx, len(paths)):
        path = paths[file_idx]
        with artifact_store.open(path, "rb") as f:
            if (
                starting_position is not None
                and file_idx == starting_position.file_idx
            ):
                f.seek(starting_position.offset, 0)
                f.readline()

            while True:
                offset = int(f.tell())
                raw = f.readline()
                if not raw:
                    break

                line = raw.rstrip(b"\n\r").decode("utf-8", errors="replace")
                yield (CursorToken(file_idx=file_idx, offset=offset), line)


def iterate_backward(
    artifact_store: "BaseArtifactStore",
    paths: Sequence[str],
    starting_position: Optional[CursorToken],
) -> Generator[Tuple[CursorToken, str], None, None]:
    """Iterate log lines backward (newest to oldest).

    Args:
        artifact_store: The artifact store.
        paths: The paths of the log files.
        starting_position: The starting position of the iteration.

    Returns:
        A generator of tuples containing the cursor token and the log line.

    Raises:
        ValueError: If the starting position is out of range.
    """
    start_file_idx = (
        starting_position.file_idx
        if starting_position is not None
        else len(paths) - 1
    )
    if start_file_idx < 0 or start_file_idx >= len(paths):
        raise ValueError("Cursor file index is out of range.")

    for file_idx in range(start_file_idx, -1, -1):
        path = paths[file_idx]

        with artifact_store.open(path, "rb") as f:
            f.seek(0, 2)
            file_size = int(f.tell())

            if (
                starting_position is not None
                and file_idx == starting_position.file_idx
            ):
                pos = min(int(starting_position.offset), file_size)
            else:
                pos = file_size

            buffer = b""
            buffer_start = pos

            while True:
                nl = buffer.rfind(b"\n")
                if nl != -1:
                    line_start = buffer_start + nl + 1
                    raw = buffer[nl + 1 :]
                    buffer = buffer[:nl]

                    raw = raw.rstrip(b"\r")
                    if raw:
                        line = raw.decode("utf-8", errors="replace")
                        yield (
                            CursorToken(file_idx=file_idx, offset=line_start),
                            line,
                        )
                    continue

                if buffer_start == 0:
                    raw = buffer.rstrip(b"\r")
                    if raw:
                        line = raw.decode("utf-8", errors="replace")
                        yield (CursorToken(file_idx=file_idx, offset=0), line)
                    break

                read_start = max(0, buffer_start - CHUNK_SIZE)
                read_len = buffer_start - read_start
                f.seek(read_start, 0)
                chunk = f.read(read_len)
                buffer = chunk + buffer
                buffer_start = read_start


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

    if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
        logs_uri = os.path.join(logs_base_uri, str(log_id))
    else:
        logs_uri = os.path.join(logs_base_uri, f"{log_id}{LOGS_EXTENSION}")

    return sanitize_remote_path(logs_uri)


def remove_ansi_escape_codes(text: str) -> str:
    """Auxiliary function to remove ANSI escape codes from a given string.

    Args:
        text: the input string

    Returns:
        the version of the input string where the escape codes are removed.
    """
    return ansi_escape.sub("", text)


def fetch_log_records(
    artifact_store: "BaseArtifactStore",
    logs_uri: str,
    limit: int,
) -> List[LogEntry]:
    """Fetches log entries.

    Args:
        artifact_store: The artifact store.
        logs_uri: The URI of the artifact (file or directory).
        limit: Maximum number of log entries to return.

    Returns:
        List of log entries.
    """
    log_entries = []

    for line in _stream_logs_line_by_line(artifact_store, logs_uri):
        if log_entry := parse_log_entry(line):
            log_entries.append(log_entry)

        if len(log_entries) >= limit:
            break

    return log_entries


def _stream_logs_line_by_line(
    artifact_store: "BaseArtifactStore",
    logs_uri: str,
) -> Generator[str, None, None]:
    """Stream logs line by line without loading the entire file into memory.

    This generator yields log lines one by one, handling both single files
    and directories with multiple log files.

    Args:
        artifact_store: The artifact store.
        logs_uri: The URI of the log file or directory.

    Yields:
        Individual log lines as strings.

    Raises:
        DoesNotExistException: If the artifact does not exist in the artifact store.
    """
    if not artifact_store.exists(logs_uri):
        return

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


class ArtifactLogStoreConfig(OtelLogStoreConfig):
    """Configuration for the artifact log store."""


class ArtifactLogStoreOrigin(OtelLogStoreOrigin):
    """Artifact log store origin."""

    def __init__(
        self,
        name: str,
        log_store: "BaseLogStore",
        log_model: LogsResponse,
        metadata: Dict[str, Any],
    ) -> None:
        """Initialize a log store origin.

        Args:
            name: The name of the origin.
            log_store: The log store to emit logs to.
            log_model: The log model associated with the origin.
            metadata: Additional metadata to attach to all log entries that will
                be emitted by this origin.
        """
        super().__init__(name, log_store, log_model, metadata)

        if log_model.uri:
            self.metadata["zenml.log.uri"] = log_model.uri


class ArtifactLogStore(OtelLogStore):
    """Log store that saves logs to the artifact store.

    This implementation extends OtelLogStore and uses the ArtifactLogExporter
    to write logs to the artifact store. Inherits all OTEL infrastructure
    including shared BatchLogRecordProcessor and routing.
    """

    def __init__(
        self, artifact_store: "BaseArtifactStore", *args: Any, **kwargs: Any
    ) -> None:
        """Initialize the artifact log store.

        Args:
            artifact_store: The artifact store to use for logging.
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._artifact_store = artifact_store

    @property
    def origin_class(self) -> Type[ArtifactLogStoreOrigin]:
        """Class of the origin.

        Returns:
            The class of the origin.
        """
        return ArtifactLogStoreOrigin

    @classmethod
    def from_artifact_store(
        cls, artifact_store: "BaseArtifactStore"
    ) -> "ArtifactLogStore":
        """Creates an artifact log store from an artifact store.

        Args:
            artifact_store: The artifact store to create the log store from.

        Returns:
            The created artifact log store.
        """
        return cls(
            artifact_store=artifact_store,
            id=artifact_store.id,
            name="default",
            config=ArtifactLogStoreConfig(endpoint=artifact_store.path),
            flavor="artifact",
            type=StackComponentType.LOG_STORE,
            user=artifact_store.user,
            created=artifact_store.created,
            updated=artifact_store.updated,
        )

    @property
    def config(self) -> ArtifactLogStoreConfig:
        """Returns the configuration of the artifact log store.

        Returns:
            The configuration.
        """
        return cast(ArtifactLogStoreConfig, self._config)

    def get_exporter(self) -> "LogExporter":
        """Get the artifact log exporter for this log store.

        Returns:
            The ArtifactLogExporter instance.
        """
        from zenml.log_stores.artifact.artifact_log_exporter import (
            ArtifactLogExporter,
        )

        return ArtifactLogExporter(artifact_store=self._artifact_store)

    def _release_origin(
        self,
        origin: BaseLogStoreOrigin,
    ) -> None:
        """Finalize the stream of log records associated with an origin.

        Args:
            origin: The origin to finalize.
        """
        assert isinstance(origin, ArtifactLogStoreOrigin)
        with self._lock:
            origin.logger.emit(
                body=END_OF_STREAM_MESSAGE,
            )

    def fetch(
        self,
        logs_model: "LogsResponse",
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
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
        if not logs_model.uri:
            raise ValueError(
                "logs_model.uri is required for ArtifactLogStore.fetch()"
            )

        if not logs_model.artifact_store_id:
            raise ValueError(
                "logs_model.artifact_store_id is required "
                "for ArtifactLogStore.fetch()"
            )

        if logs_model.artifact_store_id != self._artifact_store.id:
            raise ValueError(
                "logs_model.artifact_store_id does not match the artifact store "
                "id of the log store."
            )

        if start_time or end_time:
            logger.warning(
                "start_time and end_time are not supported for "
                "ArtifactLogStore.fetch(). Both parameters will be ignored."
            )

        log_entries = fetch_log_records(
            artifact_store=self._artifact_store,
            logs_uri=logs_model.uri,
            limit=limit,
        )

        return log_entries

    def fetch_entries(
        self,
        logs_model: "LogsResponse",
        limit: int,
        before: Optional[str],
        after: Optional[str],
        filter_: "LogsEntriesFilter",
    ) -> "LogsEntriesResponse":
        """Fetch log entries from the artifact store.

        Args:
            logs_model: The logs model containing uri and artifact_store_id.
            limit: Maximum number of log entries to return.
            before: Cursor token pointing to older entries.
            after: Cursor token pointing to newer entries.
            filter_: Filters that must be applied during retrieval.
        """
        if limit <= 0:
            raise ValueError("`limit` must be positive.")

        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        if not logs_model.uri:
            raise ValueError(
                "logs_model.uri is required for ArtifactLogStore.fetch_entries()"
            )

        if not logs_model.artifact_store_id:
            raise ValueError(
                "logs_model.artifact_store_id is required for "
                "ArtifactLogStore.fetch_entries()"
            )

        if logs_model.artifact_store_id != self._artifact_store.id:
            raise ValueError(
                "logs_model.artifact_store_id does not match the artifact store "
                "id of the log store."
            )

        paths = _get_logs_file_paths(
            artifact_store=self._artifact_store, logs_uri=logs_model.uri
        )
        if not paths:
            return LogsEntriesResponse(items=[], before=None, after=None)

        items: List[LogEntry] = []
        end_pos: Optional[CursorToken] = None

        if after is not None:
            start_pos = _decode_cursor(token=after)

            for pos, line in iterate_forward(
                self._artifact_store,
                paths,
                starting_position=start_pos,
            ):
                entry = parse_log_entry(line)
                if entry is None or not _matches_filter(entry, filter_):
                    continue

                items.append(entry)
                end_pos = pos
                if len(items) >= limit:
                    break

            items.reverse()

            before = start_pos
            after = end_pos

        else:
            items: List[LogEntry] = []

            if before is None:
                last_path = paths[-1]
                with self._artifact_store.open(last_path, "rb") as f:
                    f.seek(0, 2)
                    eof = int(f.tell())
                start_pos = CursorToken(file_idx=len(paths) - 1, offset=eof)
            else:
                start_pos = _decode_cursor(token=before)

            gen = iterate_backward(
                self._artifact_store,
                paths,
                starting_position=start_pos,
            )
            for pos, line in gen:
                entry = parse_log_entry(line)
                if entry is None or not _matches_filter(entry, filter_):
                    continue

                items.append(entry)
                end_pos = pos

                if len(items) >= limit:
                    break

            before = end_pos
            after = start_pos

        return LogsEntriesResponse(
            items=items,
            before=_encode_cursor(pos=before) if before else None,
            after=_encode_cursor(pos=after) if after else None,
        )

    def cleanup(self) -> None:
        """Cleanup the artifact log store.

        This method is called to ensure that the artifact log store is cleaned up.
        """
        self._artifact_store.cleanup()
