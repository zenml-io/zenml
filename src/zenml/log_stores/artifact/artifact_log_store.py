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
import io
import json
import os
import re
from collections import deque
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

from opentelemetry.sdk._logs.export import LogExporter
from pydantic import BaseModel, ConfigDict, Field

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


class ArtifactLogStoreCursorPos(BaseModel):
    """Cursor position within artifact log files."""

    file_index: int = Field(ge=0)
    line_index: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ArtifactLogStoreCursor(BaseModel):
    """Cursor payload for artifact log store pagination tokens."""

    v: int = 1
    backend: Literal["artifact"] = "artifact"
    logs_id: str
    pos: ArtifactLogStoreCursorPos

    model_config = ConfigDict(extra="forbid")


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


def _matches_filter(entry: LogEntry, filter_: LogsEntriesFilter) -> bool:
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


def _is_seekable_binary_file(f: io.BufferedIOBase) -> bool:
    try:
        if not hasattr(f, "seek") or not hasattr(f, "tell"):
            return False
        f.seek(0, os.SEEK_END)
        f.tell()
        return True
    except Exception:
        return False


def _iter_lines_reverse_seekable(
    f: io.BufferedIOBase, *, chunk_size: int = 64 * 1024
) -> Generator[str, None, None]:
    """Iterate lines in reverse order for a seekable binary file."""
    f.seek(0, os.SEEK_END)
    position = f.tell()
    buffer = b""

    while position > 0:
        read_size = min(chunk_size, position)
        position -= read_size
        f.seek(position, os.SEEK_SET)
        chunk = f.read(read_size)
        buffer = chunk + buffer

        while True:
            idx = buffer.rfind(b"\n")
            if idx == -1:
                break
            line = buffer[idx + 1 :]
            buffer = buffer[:idx]
            yield line.rstrip(b"\r").decode("utf-8", errors="replace")

    if buffer:
        yield buffer.rstrip(b"\r").decode("utf-8", errors="replace")


def _count_lines_text(artifact_store: "BaseArtifactStore", uri: str) -> int:
    count = 0
    with artifact_store.open(uri, "r") as f:
        for _ in f:
            count += 1
    return count


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
        logs_model: LogsResponse,
        limit: int,
        before: Optional[str],
        after: Optional[str],
        filter_: LogsEntriesFilter,
    ) -> LogsEntriesResponse:
        """Fetch log entries.

        Args:
            logs_model: The logs model containing metadata about the logs.
            limit: Maximum number of log entries to return.
            before: Cursor token pointing to older entries.
            after: Cursor token pointing to newer entries.
            filter_: Filters that must be applied during retrieval.

        Returns:
            A response containing log entries and pagination tokens.
        """
        if not logs_model.uri:
            raise ValueError(
                "logs_model.uri is required for ArtifactLogStore.fetch_entries()."
            )

        if not logs_model.artifact_store_id:
            raise ValueError(
                "logs_model.artifact_store_id is required for "
                "ArtifactLogStore.fetch_entries()."
            )

        if logs_model.artifact_store_id != self._artifact_store.id:
            raise ValueError(
                "logs_model.artifact_store_id does not match the artifact store id "
                "of the log store."
            )

        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        logs_uri = logs_model.uri
        if not self._artifact_store.exists(logs_uri):
            return LogsEntriesResponse(items=[])

        if self._artifact_store.isdir(logs_uri):
            files = self._artifact_store.listdir(logs_uri)
            files = [str(f) for f in files]
            files.sort()
            file_uris = [os.path.join(logs_uri, f) for f in files]
        else:
            file_uris = [logs_uri]

        if not file_uris:
            return LogsEntriesResponse(items=[])

        if before is None and after is None:
            items, before_pos, after_pos = self._fetch_latest_page_from_files(
                file_uris=file_uris, limit=limit, filter_=filter_
            )
        elif before is not None:
            boundary = self._decode_cursor(
                token=before,
                logs_id=str(logs_model.id),
            )
            items, before_pos, after_pos = self._fetch_before_page_from_files(
                file_uris=file_uris,
                limit=limit,
                filter_=filter_,
                boundary=boundary,
            )
        else:
            boundary = self._decode_cursor(
                token=after,
                logs_id=str(logs_model.id),
            )
            items, before_pos, after_pos = self._fetch_after_page_from_files(
                file_uris=file_uris,
                limit=limit,
                filter_=filter_,
                boundary=boundary,
            )

        before_token = (
            self._encode_cursor(
                logs_id=str(logs_model.id),
                pos=before_pos,
            )
            if before_pos is not None
            else None
        )
        after_token = (
            self._encode_cursor(
                logs_id=str(logs_model.id),
                pos=after_pos,
            )
            if after_pos is not None
            else None
        )
        return LogsEntriesResponse(
            items=items, before=before_token, after=after_token
        )

    def _encode_cursor(self, *, logs_id: str, pos: Dict[str, Any]) -> str:
        cursor = ArtifactLogStoreCursor(
            logs_id=logs_id,
            pos=ArtifactLogStoreCursorPos.model_validate(pos),
        )
        data = json.dumps(
            cursor.model_dump(mode="json"),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    def _decode_cursor(
        self, *, token: str, logs_id: str
    ) -> ArtifactLogStoreCursorPos:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
        cursor = ArtifactLogStoreCursor.model_validate(decoded)
        if cursor.logs_id != logs_id:
            raise ValueError("Cursor logs ID does not match.")
        return cursor.pos

    def _fetch_latest_page_from_files(
        self,
        *,
        file_uris: List[str],
        limit: int,
        filter_: LogsEntriesFilter,
    ) -> Tuple[
        List[LogEntry], Optional[Dict[str, Any]], Optional[Dict[str, Any]]
    ]:
        # Try a reverse-reader first (seekable only), falling back to a forward
        # scan when the artifact store doesn't provide seekable handles.
        newest_first: List[Tuple[int, int, LogEntry]] = []
        used_files: Set[int] = set()

        seekable = True
        for file_index in range(len(file_uris) - 1, -1, -1):
            uri = file_uris[file_index]
            try:
                with self._artifact_store.open(uri, "rb") as bf:
                    if not _is_seekable_binary_file(bf):
                        seekable = False
                        break

                    reverse_offset = 0
                    for line in _iter_lines_reverse_seekable(bf):
                        reverse_offset += 1
                        entry = parse_log_entry(line)
                        if entry is None or not _matches_filter(
                            entry, filter_
                        ):
                            continue
                        used_files.add(file_index)
                        newest_first.append(
                            (file_index, reverse_offset - 1, entry)
                        )
                        if len(newest_first) >= limit:
                            break
            except Exception:
                seekable = False
                break

            if len(newest_first) >= limit:
                break

        if seekable and newest_first:
            # Convert reverse offsets to forward line indices.
            total_lines_by_file: Dict[int, int] = {}
            for file_index in used_files:
                total_lines_by_file[file_index] = _count_lines_text(
                    self._artifact_store, file_uris[file_index]
                )

            items: List[Tuple[int, int, LogEntry]] = []
            for file_index, reverse_offset, entry in newest_first:
                total = total_lines_by_file[file_index]
                line_index = total - 1 - reverse_offset
                items.append((file_index, line_index, entry))

            # items already newest->oldest
            before_pos = {
                "file_index": items[-1][0],
                "line_index": items[-1][1],
            }
            after_pos = {
                "file_index": items[0][0],
                "line_index": items[0][1],
            }
            return ([e for _, _, e in items], before_pos, after_pos)

        # Fallback: forward scan newest files first, keeping only the tail.
        newest_first = []
        remaining = limit
        for file_index in range(len(file_uris) - 1, -1, -1):
            uri = file_uris[file_index]
            file_entries: List[Tuple[int, LogEntry]] = []
            with self._artifact_store.open(uri, "r") as f:
                for line_index, line in enumerate(f):
                    entry = parse_log_entry(line)
                    if entry is None or not _matches_filter(entry, filter_):
                        continue
                    file_entries.append((line_index, entry))

            if not file_entries:
                continue

            take = min(remaining, len(file_entries))
            for line_index, entry in reversed(file_entries[-take:]):
                newest_first.append((file_index, line_index, entry))
            remaining -= take
            if remaining <= 0:
                break

        if not newest_first:
            return ([], None, None)

        before_pos = {
            "file_index": newest_first[-1][0],
            "line_index": newest_first[-1][1],
        }
        after_pos = {
            "file_index": newest_first[0][0],
            "line_index": newest_first[0][1],
        }
        return ([e for _, _, e in newest_first], before_pos, after_pos)

    def _fetch_before_page_from_files(
        self,
        *,
        file_uris: List[str],
        limit: int,
        filter_: LogsEntriesFilter,
        boundary: ArtifactLogStoreCursorPos,
    ) -> Tuple[
        List[LogEntry], Optional[Dict[str, Any]], Optional[Dict[str, Any]]
    ]:
        boundary_file_index = boundary.file_index
        boundary_line_index = boundary.line_index

        window: "deque[Tuple[int, int, LogEntry]]" = deque(maxlen=limit)

        for file_index, uri in enumerate(file_uris):
            if file_index > boundary_file_index:
                break

            with self._artifact_store.open(uri, "r") as f:
                for line_index, line in enumerate(f):
                    if (
                        file_index == boundary_file_index
                        and line_index >= boundary_line_index
                    ):
                        break
                    entry = parse_log_entry(line)
                    if entry is None or not _matches_filter(entry, filter_):
                        continue
                    window.append((file_index, line_index, entry))

        if not window:
            return ([], None, None)

        items = list(window)  # oldest->newest
        items.reverse()  # newest->oldest
        before_pos = {
            "file_index": items[-1][0],
            "line_index": items[-1][1],
        }
        after_pos = {
            "file_index": items[0][0],
            "line_index": items[0][1],
        }
        return ([e for _, _, e in items], before_pos, after_pos)

    def _fetch_after_page_from_files(
        self,
        *,
        file_uris: List[str],
        limit: int,
        filter_: LogsEntriesFilter,
        boundary: ArtifactLogStoreCursorPos,
    ) -> Tuple[
        List[LogEntry], Optional[Dict[str, Any]], Optional[Dict[str, Any]]
    ]:
        boundary_file_index = boundary.file_index
        boundary_line_index = boundary.line_index

        items_forward: List[Tuple[int, int, LogEntry]] = []

        for file_index, uri in enumerate(file_uris):
            if file_index < boundary_file_index:
                continue

            with self._artifact_store.open(uri, "r") as f:
                for line_index, line in enumerate(f):
                    if (
                        file_index == boundary_file_index
                        and line_index <= boundary_line_index
                    ):
                        continue
                    entry = parse_log_entry(line)
                    if entry is None or not _matches_filter(entry, filter_):
                        continue
                    items_forward.append((file_index, line_index, entry))
                    if len(items_forward) >= limit:
                        break
            if len(items_forward) >= limit:
                break

        if not items_forward:
            # Keep the caller polling from the existing position.
            return ([], None, boundary)

        # items_forward is oldest->newest; return newest->oldest
        items_forward.reverse()
        before_pos = {
            "file_index": items_forward[-1][0],
            "line_index": items_forward[-1][1],
        }
        after_pos = {
            "file_index": items_forward[0][0],
            "line_index": items_forward[0][1],
        }
        return ([e for _, _, e in items_forward], before_pos, after_pos)

    def cleanup(self) -> None:
        """Cleanup the artifact log store.

        This method is called to ensure that the artifact log store is cleaned up.
        """
        self._artifact_store.cleanup()
