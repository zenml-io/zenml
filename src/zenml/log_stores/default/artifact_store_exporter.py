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

import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Sequence

from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData

    from zenml.artifact_stores import BaseArtifactStore

from zenml.logger import get_logger

logger = get_logger(__name__)


class ArtifactStoreExporter(LogExporter):
    """OpenTelemetry exporter that writes logs to ZenML artifact store.

    Replaces the custom LogsStorage implementation with a standard
    OpenTelemetry exporter. Logs are batched by BatchLogRecordProcessor
    and written to the artifact store.
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
        self.log_buffer: list[str] = []
        self.file_counter = 0

    def export(self, batch: Sequence["LogData"]) -> LogExportResult:
        """Export a batch of logs to the artifact store.

        Args:
            batch: Sequence of LogData to export.

        Returns:
            LogExportResult indicating success or failure.
        """
        if not batch:
            return LogExportResult.SUCCESS

        try:
            # Format logs
            log_lines = []
            for log_data in batch:
                log_record = log_data.log_record

                # Format as ZenML log entry
                log_line = self._format_log_entry(
                    message=str(log_record.body) if log_record.body else "",
                    level=log_record.severity_text,
                    timestamp_ns=log_record.timestamp,
                )
                log_lines.append(log_line)

            # Write to artifact store
            if log_lines:
                self._write_to_artifact_store(log_lines)

            return LogExportResult.SUCCESS

        except Exception as e:
            logger.error(f"Failed to export logs to artifact store: {e}")
            return LogExportResult.FAILURE

    def _format_log_entry(
        self,
        message: str,
        level: Optional[str],
        timestamp_ns: Optional[int],
    ) -> str:
        """Format a log entry in ZenML format.

        Args:
            message: The log message.
            level: The log level (DEBUG, INFO, etc.).
            timestamp_ns: Timestamp in nanoseconds.

        Returns:
            Formatted log line.
        """
        # Convert timestamp
        if timestamp_ns:
            timestamp = datetime.fromtimestamp(timestamp_ns / 1e9)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        else:
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[
                :-3
            ]

        # Map OTel severity to ZenML level
        zenml_level = self._map_severity_to_level(level)

        # Format: timestamp|level|message
        return f"{timestamp_str}|{zenml_level}|{message}"

    def _map_severity_to_level(self, severity: Optional[str]) -> str:
        """Map OpenTelemetry severity to ZenML log level.

        Args:
            severity: OTel severity text.

        Returns:
            ZenML log level string.
        """
        if not severity:
            return "INFO"

        severity_upper = severity.upper()
        if "DEBUG" in severity_upper or "TRACE" in severity_upper:
            return "DEBUG"
        elif "INFO" in severity_upper:
            return "INFO"
        elif "WARN" in severity_upper:
            return "WARNING"
        elif "ERROR" in severity_upper:
            return "ERROR"
        elif (
            "CRITICAL" in severity_upper
            or "FATAL" in severity_upper
            or "EMERGENCY" in severity_upper
        ):
            return "CRITICAL"
        else:
            return "INFO"

    def _write_to_artifact_store(self, log_lines: list[str]) -> None:
        """Write log lines to the artifact store.

        Args:
            log_lines: List of formatted log lines.
        """
        # Create unique file name with timestamp
        timestamp = int(time.time() * 1000)
        self.file_counter += 1
        file_uri = f"{self.logs_uri}.{timestamp}.{self.file_counter}"

        # Join lines and write
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
        """Shutdown the exporter and flush any remaining logs."""
        if self.log_buffer:
            try:
                self._write_to_artifact_store(self.log_buffer)
                self.log_buffer.clear()
            except Exception as e:
                logger.warning(f"Error during shutdown flush: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered logs.

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful.
        """
        try:
            if self.log_buffer:
                self._write_to_artifact_store(self.log_buffer)
                self.log_buffer.clear()
            return True
        except Exception as e:
            logger.warning(f"Force flush failed: {e}")
            return False
