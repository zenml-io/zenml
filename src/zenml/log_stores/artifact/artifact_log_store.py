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
from datetime import datetime
from typing import (
    Iterator,
    List,
    Optional,
    Union,
    cast,
)
from uuid import UUID

from opentelemetry.sdk._logs.export import LogExporter

from zenml.artifact_stores import BaseArtifactStore
from zenml.artifacts.utils import _load_artifact_store
from zenml.client import Client
from zenml.enums import LoggingLevels
from zenml.exceptions import DoesNotExistException
from zenml.log_stores.artifact.artifact_log_store_flavor import (
    ArtifactLogStoreConfig,
)
from zenml.log_stores.base_log_store import MAX_ENTRIES_PER_REQUEST
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.log_stores.utils import LogEntry
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.utils.io_utils import sanitize_remote_path
from zenml.zen_stores.base_zen_store import BaseZenStore

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

logger = get_logger(__name__)


LOGS_EXTENSION = ".log"


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


def remove_ansi_escape_codes(text: str) -> str:
    """Auxiliary function to remove ANSI escape codes from a given string.

    Args:
        text: the input string

    Returns:
        the version of the input string where the escape codes are removed.
    """
    return ansi_escape.sub("", text)


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


class ArtifactLogStore(OtelLogStore):
    """Log store that saves logs to the artifact store.

    This implementation extends OtelLogStore and uses the ArtifactLogExporter
    to write logs to the artifact store. Inherits all OTEL infrastructure
    including shared BatchLogRecordProcessor and routing.
    """

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

        return ArtifactLogExporter()

    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
        message_size: int = 5120,
    ) -> List["LogEntry"]:
        """Fetch logs from the artifact store.

        Args:
            logs_model: The logs model containing uri and artifact_store_id.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.
            message_size: Maximum size of a single log message in bytes.

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
