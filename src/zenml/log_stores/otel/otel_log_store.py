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
"""OpenTelemetry log store implementation."""

import logging
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, cast

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from zenml import __version__
from zenml.log_stores.base_log_store import BaseLogStore
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.logger import get_logger
from zenml.models import LogsResponse

if TYPE_CHECKING:
    from opentelemetry.sdk._logs.export import LogExporter

    from zenml.logging.logging import LogEntry

logger = get_logger(__name__)


class OtelLogStore(BaseLogStore):
    """Log store that exports logs using OpenTelemetry.

    Each instance creates its own BatchLogRecordProcessor and background thread.
    This is simpler than shared infrastructure but means more threads when
    multiple log stores are active simultaneously.

    Subclasses should implement `get_exporter()` to provide the specific
    log exporter for their backend (e.g., ArtifactStoreExporter, DatadogLogExporter).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the OpenTelemetry log store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)

        self._resource: Optional["Resource"] = None
        self._exporter: Optional["LogExporter"] = None
        self._provider: Optional["LoggerProvider"] = None
        self._processor: Optional["BatchLogRecordProcessor"] = None

    @property
    def config(self) -> OtelLogStoreConfig:
        """Returns the configuration of the OTel log store.

        Returns:
            The configuration.
        """
        return cast(OtelLogStoreConfig, self._config)

    @abstractmethod
    def get_exporter(self) -> "LogExporter":
        """Get the log exporter for this log store.

        Subclasses must implement this method to provide the appropriate
        exporter for their backend.

        Returns:
            The log exporter instance.
        """

    def activate(self) -> None:
        """Activate log collection with OpenTelemetry."""
        from zenml.logging.logging import get_active_log_model

        log_model = get_active_log_model()
        if not log_model:
            raise RuntimeError(
                "activate() called outside of an active logging context. "
                "This should not happen."
            )

        self._exporter = self.get_exporter()
        self._processor = BatchLogRecordProcessor(self._exporter)

        self._resource = Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": __version__,
                "zenml.log_id": str(log_model.id),
            }
        )

        self._provider = LoggerProvider(resource=self._resource)
        self._provider.add_log_record_processor(self._processor)

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record by sending to OpenTelemetry.

        Args:
            record: The log record to process.
        """
        if not self._provider:
            return

        try:
            otel_logger = self._provider.get_logger(
                record.name or "unknown",
                schema_url=None,
            )
            otel_logger.emit(
                timestamp=int(record.created * 1e9),
                observed_timestamp=int(record.created * 1e9),
                severity_number=self._get_severity_number(record.levelno),
                severity_text=record.levelname,
                body=record.getMessage(),
                attributes={
                    "code.filepath": record.pathname,
                    "code.lineno": record.lineno,
                    "code.function": record.funcName,
                },
            )

        except Exception:
            pass

    def _get_severity_number(self, levelno: int) -> int:
        """Map Python log level to OTEL severity number.

        Args:
            levelno: Python logging level number.

        Returns:
            OTEL severity number.
        """
        if levelno >= logging.CRITICAL:
            return SeverityNumber.FATAL.value
        elif levelno >= logging.ERROR:
            return SeverityNumber.ERROR.value
        elif levelno >= logging.WARNING:
            return SeverityNumber.WARN.value
        elif levelno >= logging.INFO:
            return SeverityNumber.INFO.value
        elif levelno >= logging.DEBUG:
            return SeverityNumber.DEBUG.value
        else:
            return SeverityNumber.UNSPECIFIED.value

    def deactivate(self) -> None:
        """Deactivate log collection and shut down the processor.

        Flushes any pending logs and shuts down the processor's background thread.
        """
        if self._processor:
            try:
                # Force flush any pending logs
                self._processor.force_flush(timeout_millis=5000)
                logger.debug("Flushed pending logs")
            except Exception as e:
                logger.warning(f"Error flushing logs: {e}")

            try:
                self._processor.shutdown()
                logger.debug("Shut down log processor and background thread")
            except Exception as e:
                logger.warning(f"Error shutting down processor: {e}")

        logger.debug("OtelLogStore deactivated")

    @abstractmethod
    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
        message_size: int = 5120,
    ) -> List["LogEntry"]:
        """Fetch logs from the OpenTelemetry backend.

        This method should be overridden by subclasses to implement
        backend-specific log retrieval. The base implementation returns
        an empty list.

        Args:
            logs_model: The logs model containing run and step metadata.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.
            message_size: Maximum size of a single log message in bytes.

        Returns:
            List of log entries from the backend.
        """
