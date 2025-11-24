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
from typing import TYPE_CHECKING, Dict, List, Sequence
from uuid import UUID, uuid4

from opentelemetry import context as otel_context
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

from zenml.artifacts.utils import _load_artifact_store
from zenml.client import Client
from zenml.enums import LoggingLevels
from zenml.log_stores.artifact.artifact_log_store import (
    remove_ansi_escape_codes,
)
from zenml.log_stores.otel.otel_log_store import LOGGING_CONTEXT_KEY
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.utils.logging_utils import LogEntry
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData


DEFAULT_MESSAGE_SIZE = 5 * 1024

logger = get_logger(__name__)


class ArtifactLogExporter(LogExporter):
    """OpenTelemetry exporter that writes logs to ZenML artifact store."""

    def __init__(self) -> None:
        """Initialize the exporter with file counters per context."""
        self.file_counters: Dict[UUID, int] = {}

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
            logs_by_context: Dict[UUID, List[str]] = defaultdict(list)
            log_models: Dict[UUID, "LogsResponse"] = {}

            for log_data in batch:
                if not log_data.log_record.context:
                    continue

                log_model = otel_context.get_value(
                    LOGGING_CONTEXT_KEY, log_data.log_record.context
                )
                if not log_model:
                    continue

                log_id = log_model.id
                log_models[log_id] = log_model

                entries = self._otel_record_to_log_entries(log_data.log_record)
                for entry in entries:
                    json_line = entry.model_dump_json(exclude_none=True)
                    logs_by_context[log_id].append(json_line)

            for log_id, log_lines in logs_by_context.items():
                if log_lines:
                    log_model = log_models[log_id]
                    self._write_to_artifact_store(log_lines, log_model)

            return LogExportResult.SUCCESS

        except Exception:
            logger.exception("Failed to export logs to artifact store")
            return LogExportResult.FAILURE

    def _otel_record_to_log_entries(
        self, log_record: "LogData"
    ) -> List[LogEntry]:
        """Convert an OTEL log record to ZenML LogEntry objects.

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

    def _write_to_artifact_store(
        self,
        log_lines: List[str],
        log_model: "LogsResponse",
    ) -> None:
        """Write log lines to the artifact store.

        Args:
            log_lines: List of JSON-serialized log entries.
            log_model: The log model.
            log_id: The log ID for tracking file counters.
        """
        if not log_model.uri or not log_model.artifact_store_id:
            logger.warning(
                f"Skipping log write: missing uri or artifact_store_id for log {log_model.id}"
            )
            return

        client = Client()
        artifact_store = _load_artifact_store(
            log_model.artifact_store_id, client.zen_store
        )

        try:
            content = "\n".join(log_lines) + "\n"

            if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
                timestamp = int(time.time() * 1000)
                if log_model.id not in self.file_counters:
                    self.file_counters[log_model.id] = 0
                self.file_counters[log_model.id] += 1

                file_uri = os.path.join(
                    log_model.uri,
                    f"{timestamp}_{self.file_counters[log_model.id]}.jsonl",
                )

                with artifact_store.open(file_uri, "w") as f:
                    f.write(content)
            else:
                with artifact_store.open(log_model.uri, "a") as f:
                    f.write(content)
        except Exception as e:
            logger.error(f"Failed to write logs to {log_model.uri}: {e}")
            raise
        finally:
            artifact_store.cleanup()

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass
