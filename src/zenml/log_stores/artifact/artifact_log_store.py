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

import os
import re
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Type,
    cast,
)
from uuid import UUID

from opentelemetry.sdk._logs.export import LogExporter
from pydantic import Field

from zenml.artifact_stores import BaseArtifactStore
from zenml.constants import LOGS_MAX_ENTRIES_PER_REQUEST
from zenml.enums import LoggingLevels, StackComponentType
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
CHUNK_SIZE = 1024 * 1024 * 5  # 5MB


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


def iterate_backward_lines(
    artifact_store: "BaseArtifactStore",
    paths: Sequence[str],
) -> Generator[str, None, None]:
    """Iterate log lines backward (newest to oldest).

    Args:
        artifact_store: The artifact store.
        paths: The paths of the log files.

    Yields:
        Log lines ordered from newest to oldest.
    """
    for path in reversed(paths):
        with artifact_store.open(path, "rb") as f:
            f.seek(0, 2)
            file_size = int(f.tell())
            pos = file_size

            buffer = b""
            buffer_start = pos

            while True:
                nl = buffer.rfind(b"\n")
                if nl != -1:
                    raw = buffer[nl + 1 :]
                    buffer = buffer[:nl]

                    raw = raw.rstrip(b"\r")
                    if raw:
                        line = raw.decode("utf-8", errors="replace")
                        yield line
                    continue

                if buffer_start == 0:
                    raw = buffer.rstrip(b"\r")
                    if raw:
                        line = raw.decode("utf-8", errors="replace")
                        yield line
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

    default_query_size: int = Field(
        default=LOGS_MAX_ENTRIES_PER_REQUEST,
        description="Maximum number of log entries to fetch with one request.",
    )


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
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional["LogsEntriesFilter"] = None,
    ) -> "LogsEntriesResponse":
        """Fetch log entries from the artifact store.

        Args:
            logs_model: The logs model containing uri and artifact_store_id.
            limit: Maximum number of log entries to return, capped at
                `LOGS_MAX_ENTRIES_PER_REQUEST`.
            before: Unused pagination cursor for artifact log stores.
            after: Unused pagination cursor for artifact log stores.
            filter_: Unused server-side filter for artifact log stores.

        Returns:
            A response containing log entries without pagination tokens.

        Raises:
            ValueError: If the logs model is invalid or the limit is not
                positive.
        """
        if limit is None:
            effective_limit = LOGS_MAX_ENTRIES_PER_REQUEST
        else:
            if limit <= 0:
                raise ValueError("`limit` must be positive.")
            effective_limit = min(limit, LOGS_MAX_ENTRIES_PER_REQUEST)

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

        if before is not None:
            logger.warning(
                "Ignoring `before` argument in ArtifactLogStore.fetch(). "
                "Artifact log pagination is no longer supported."
            )
        if after is not None:
            logger.warning(
                "Ignoring `after` argument in ArtifactLogStore.fetch(). "
                "Artifact log pagination is no longer supported."
            )
        if filter_ is not None:
            logger.warning(
                "Ignoring `filter_` argument in ArtifactLogStore.fetch(). "
                "Artifact log filtering moved to the client side."
            )

        items: List[LogEntry] = []
        for line in iterate_backward_lines(self._artifact_store, paths):
            entry = parse_log_entry(line)
            if entry is None:
                continue

            items.append(entry)
            if len(items) >= effective_limit:
                break

        return LogsEntriesResponse(items=items, before=None, after=None)

    def cleanup(self) -> None:
        """Cleanup the artifact log store.

        This method is called to ensure that the artifact log store is cleaned up.
        """
        self._artifact_store.cleanup()
