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
"""OpenTelemetry exporter that writes logs to ZenML artifact store."""

import os
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, cast
from uuid import UUID, uuid4

from opentelemetry import context as otel_context
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import LoggingLevels
from zenml.log_stores.artifact.artifact_log_store import (
    remove_ansi_escape_codes,
)
from zenml.log_stores.otel.otel_log_store import (
    ZENML_OTEL_LOG_STORE_CONTEXT_KEY,
    ZENML_OTEL_LOG_STORE_FLUSH_KEY,
)
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.utils.logging_utils import LogEntry
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData


DEFAULT_MESSAGE_SIZE = 5 * 1024
LOGS_EXTENSION = ".log"

logger = get_logger(__name__)


class ArtifactLogExporter(LogExporter):
    """OpenTelemetry exporter that writes logs to ZenML artifact store."""

    def __init__(self, artifact_store: "BaseArtifactStore") -> None:
        """Initialize the exporter.

        Args:
            artifact_store: The artifact store to write logs to.
        """
        self.artifact_store = artifact_store

    def export(self, batch: Sequence["LogData"]) -> LogExportResult:
        """Export a batch of logs to the artifact store.

        Args:
            batch: Sequence of LogData to export (can be from multiple contexts).

        Returns:
            LogExportResult indicating success or failure.
        """
        if not batch:
            return LogExportResult.SUCCESS

        try:
            entries_by_id: Dict[UUID, List[str]] = defaultdict(list)
            responses_by_id: Dict[UUID, "LogsResponse"] = {}
            finalized_log_streams: List["LogsResponse"] = []

            for log_data in batch:
                log_model = cast(
                    Optional["LogsResponse"],
                    otel_context.get_value(
                        key=ZENML_OTEL_LOG_STORE_CONTEXT_KEY,
                        context=log_data.log_record.context,
                    ),
                )
                flush = otel_context.get_value(
                    key=ZENML_OTEL_LOG_STORE_FLUSH_KEY,
                    context=log_data.log_record.context,
                )
                if not log_model:
                    continue

                if flush:
                    finalized_log_streams.append(log_model)
                    continue

                responses_by_id[log_model.id] = log_model

                entries = self._otel_record_to_log_entries(log_data)
                for entry in entries:
                    json_line = entry.model_dump_json(exclude_none=True)
                    entries_by_id[log_model.id].append(json_line)

            for log_id, log_lines in entries_by_id.items():
                if log_lines:
                    log_model = responses_by_id[log_id]
                    self._write(log_lines, log_model)

            for log_model in finalized_log_streams:
                self._finalize(log_model)

            return LogExportResult.SUCCESS

        except Exception:
            logger.exception("Failed to export logs to artifact store")
            return LogExportResult.FAILURE

    def _otel_record_to_log_entries(
        self, log_data: "LogData"
    ) -> List[LogEntry]:
        """Convert an OTEL log record to ZenML LogEntry objects.

        Args:
            log_data: The OpenTelemetry log data.

        Returns:
            List of LogEntry objects (multiple if message was chunked).
        """
        log_record = log_data.log_record
        message = str(log_record.body) if log_record.body else ""
        message = remove_ansi_escape_codes(message).rstrip()

        level = (
            self._map_severity_to_level(log_record.severity_text)
            if log_record.severity_text
            else None
        )

        name = "unknown"
        module = None
        filename = None
        lineno = None

        if log_record.attributes:
            attrs = dict(log_record.attributes)
            filename = attrs.get("code.filepath", None)
            lineno = attrs.get("code.lineno", None)
            module = attrs.get("code.function", None)

        message_bytes = message.encode("utf-8")
        if len(message_bytes) <= DEFAULT_MESSAGE_SIZE:
            return [
                LogEntry(
                    message=message,
                    name=name,
                    level=level,
                    timestamp=utc_now(tz_aware=True),
                    module=module,
                    filename=filename,
                    lineno=lineno,
                )
            ]
        else:
            chunks = self._split_to_chunks(message)
            entry_id = uuid4()
            entries = []

            for i, chunk in enumerate(chunks):
                entries.append(
                    LogEntry(
                        message=chunk,
                        name=name,
                        level=level,
                        timestamp=utc_now(tz_aware=True),
                        module=module,
                        filename=filename,
                        lineno=lineno,
                        chunk_index=i,
                        total_chunks=len(chunks),
                        id=entry_id,
                    )
                )

            return entries

    def _map_severity_to_level(self, severity_text: str) -> LoggingLevels:
        """Map OTEL severity text to ZenML LoggingLevels enum.

        Args:
            severity_text: The OTEL severity text.

        Returns:
            The corresponding LoggingLevels enum value.
        """
        if not severity_text:
            return LoggingLevels.INFO

        severity_upper = severity_text.upper()

        if severity_upper in ["DEBUG", "TRACE"]:
            return LoggingLevels.DEBUG
        elif severity_upper in ["INFO", "INFORMATION"]:
            return LoggingLevels.INFO
        elif severity_upper in ["WARN", "WARNING"]:
            return LoggingLevels.WARN
        elif severity_upper == "ERROR":
            return LoggingLevels.ERROR
        elif severity_upper in ["CRITICAL", "FATAL", "EMERGENCY"]:
            return LoggingLevels.CRITICAL
        else:
            return LoggingLevels.INFO

    def _split_to_chunks(self, message: str) -> List[str]:
        """Split a large message into chunks, handling UTF-8 boundaries.

        Args:
            message: The message to split.

        Returns:
            A list of message chunks.
        """
        message_bytes = message.encode("utf-8")
        chunks = []
        start = 0

        while start < len(message_bytes):
            end = min(start + DEFAULT_MESSAGE_SIZE, len(message_bytes))

            while end > start:
                chunk_bytes = message_bytes[start:end]
                try:
                    chunk_text = chunk_bytes.decode("utf-8")
                    chunks.append(chunk_text)
                    break
                except UnicodeDecodeError:
                    end -= 1
            else:
                end = min(start + DEFAULT_MESSAGE_SIZE, len(message_bytes))
                chunks.append(
                    message_bytes[start:end].decode("utf-8", errors="replace")
                )

            start = end

        return chunks

    def _write(
        self,
        log_lines: List[str],
        log_model: "LogsResponse",
    ) -> None:
        """Write log lines to the artifact store.

        Args:
            log_lines: List of JSON-serialized log entries.
            log_model: The log model.

        Raises:
            Exception: If the log lines cannot be written to the artifact store.
        """
        if not log_model.uri or not log_model.artifact_store_id:
            logger.warning(
                f"Skipping log write: missing uri or artifact_store_id for log {log_model.id}"
            )
            return

        try:
            content = "\n".join(log_lines) + "\n"

            if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
                if not self.artifact_store.exists(log_model.uri):
                    self.artifact_store.makedirs(log_model.uri)

                timestamp = time.time()
                file_uri = os.path.join(
                    log_model.uri,
                    f"{timestamp}{LOGS_EXTENSION}",
                )

                with self.artifact_store.open(file_uri, "w") as f:
                    f.write(content)
            else:
                logs_base_uri = os.path.dirname(log_model.uri)
                if not self.artifact_store.exists(logs_base_uri):
                    self.artifact_store.makedirs(logs_base_uri)

                with self.artifact_store.open(log_model.uri, "a") as f:
                    f.write(content)

        except Exception as e:
            logger.error(f"Failed to write logs to {log_model.uri}: {e}")
            raise

    def _finalize(
        self,
        log_model: "LogsResponse",
    ) -> None:
        """Finalize the logs for a given log model by merging all log files into one.

        Args:
            log_model: The log model.

        Raises:
            Exception: If the logs cannot be finalized.
        """
        if not log_model.uri or not log_model.artifact_store_id:
            logger.warning(
                f"Skipping log finalize: missing uri or artifact_store_id for log {log_model.id}"
            )
            return

        try:
            if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
                self._merge(log_model)
            else:
                self.artifact_store._remove_previous_file_versions(
                    log_model.uri
                )

        except Exception as e:
            logger.error(f"Failed to finalize logs for {log_model.uri}: {e}")
            raise

    def _merge(self, log_model: "LogsResponse") -> None:
        """Merges all log files into one in the given URI.

        Called on the logging context exit.

        Args:
            log_model: The log model.

        Raises:
            RuntimeError: If the log model has no URI, cannot merge logs.
        """
        # If the artifact store is immutable, merge the log files
        if self.artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
            from zenml.artifacts.utils import _load_file_from_artifact_store
            from zenml.exceptions import DoesNotExistException

            if not log_model.uri:
                raise RuntimeError("Log model has no URI, cannot merge logs.")

            files_ = self.artifact_store.listdir(log_model.uri)
            if len(files_) > 1:
                files_.sort()

                missing_files = set()
                # dump all logs to a local file first
                with self.artifact_store.open(
                    os.path.join(
                        log_model.uri, f"{time.time()}_merged{LOGS_EXTENSION}"
                    ),
                    "w",
                ) as merged_file:
                    for file in files_:
                        try:
                            merged_file.write(
                                str(
                                    _load_file_from_artifact_store(
                                        os.path.join(log_model.uri, str(file)),
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
                            os.path.join(log_model.uri, str(file))
                        )

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        self.artifact_store.cleanup()
