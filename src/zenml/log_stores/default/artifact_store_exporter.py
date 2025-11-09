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
"""OpenTelemetry exporter that writes logs to ZenML artifact store.

This implementation reuses the proven logic from the original step_logging.py
implementation, including message chunking and JSON line formatting.
"""

import time
from typing import TYPE_CHECKING, List, Sequence
from uuid import uuid4

from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData

    from zenml.artifact_stores import BaseArtifactStore

from zenml.enums import LoggingLevels

# Import from default_log_store to avoid duplication
from zenml.log_stores.default.default_log_store import remove_ansi_escape_codes
from zenml.logger import get_logger
from zenml.logging.logging import DEFAULT_MESSAGE_SIZE, LogEntry
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)


class ArtifactStoreExporter(LogExporter):
    """OpenTelemetry exporter that writes logs to ZenML artifact store.

    This exporter adapts OpenTelemetry log records to the ZenML LogEntry format
    and writes them as JSON lines to the artifact store.
    """

    def __init__(
        self,
        logs_uri: str,
        artifact_store: "BaseArtifactStore",
    ):
        """Initialize the artifact store exporter.

        Args:
            logs_uri: URI where logs should be written.
            artifact_store: The artifact store to write to.
        """
        self.logs_uri = logs_uri
        self.artifact_store = artifact_store
        self.file_counter = 0

    def export(self, batch: Sequence["LogData"]) -> LogExportResult:
        """Export a batch of logs to the artifact store.

        Converts OTEL log records to ZenML LogEntry format with proper
        message chunking and writes them as JSON lines.

        Args:
            batch: Sequence of LogData to export.

        Returns:
            LogExportResult indicating success or failure.
        """
        if not batch:
            return LogExportResult.SUCCESS

        try:
            log_lines = []
            for log_data in batch:
                log_record = log_data.log_record

                entries = self._otel_record_to_log_entries(log_record)
                for entry in entries:
                    json_line = entry.model_dump_json(exclude_none=True)
                    log_lines.append(json_line)

            if log_lines:
                self._write_to_artifact_store(log_lines)

            return LogExportResult.SUCCESS

        except Exception as e:
            logger.error(f"Failed to export logs to artifact store: {e}")
            return LogExportResult.FAILURE

    def _otel_record_to_log_entries(
        self, log_record: "LogData"
    ) -> List[LogEntry]:
        """Convert an OTEL log record to one or more ZenML LogEntry objects.

        Handles message chunking for large messages and extracts all relevant
        metadata from the OTEL record.

        Args:
            log_record: The OpenTelemetry log record.

        Returns:
            List of LogEntry objects (multiple if message was chunked).
        """
        message = str(log_record.body) if log_record.body else ""
        message = remove_ansi_escape_codes(message).rstrip()

        level = self._map_severity_to_level(log_record.severity_text)


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
        """Split a large message into chunks.

        Properly handles UTF-8 boundaries to avoid breaking multi-byte characters.
        This is the same logic from the original step_logging.py implementation.

        Args:
            message: The message to split.

        Returns:
            A list of message chunks.
        """
        message_bytes = message.encode("utf-8")
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

    def _write_to_artifact_store(self, log_lines: List[str]) -> None:
        """Write log lines to the artifact store.

        Generates a unique timestamped filename for each batch and writes
        the log lines as newline-delimited JSON.

        Args:
            log_lines: List of JSON-serialized log entries.
        """
        # Generate unique filename with timestamp and counter
        # This matches the pattern from the original implementation
        timestamp = int(time.time() * 1000)
        self.file_counter += 1

        # Use the logs_uri as the base - append timestamp and counter
        base_uri = self.logs_uri
        if base_uri.endswith(".log"):
            base_uri = base_uri[:-4]

        file_uri = f"{base_uri}_{timestamp}_{self.file_counter}.jsonl"

        # Join lines and write (one JSON object per line)
        content = "\n".join(log_lines) + "\n"

        try:
            # Write to artifact store
            with self.artifact_store.open(file_uri, "w") as f:
                f.write(content)

            logger.debug(f"Wrote {len(log_lines)} log lines to {file_uri}")
        except Exception as e:
            logger.error(f"Failed to write logs to {file_uri}: {e}")
            raise

    def shutdown(self) -> None:
        """Shutdown the exporter and cleanup artifact store resources.

        This is important to prevent memory leaks by cleaning up any
        cached connections or file handles held by the artifact store.
        """
        if hasattr(self, "artifact_store") and self.artifact_store:
            try:
                self.artifact_store.cleanup()
                logger.debug("Artifact store cleanup completed")
            except Exception as e:
                logger.warning(f"Error during artifact store cleanup: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered logs.

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful (always true - no buffering at this level).
        """
        # No-op - OTEL BatchLogRecordProcessor handles all flushing
        return True
