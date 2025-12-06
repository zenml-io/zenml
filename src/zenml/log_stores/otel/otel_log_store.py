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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from opentelemetry.sdk._logs import (
    Logger,
    LoggerProvider,
    LoggingHandler,
)
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from zenml.log_stores.base_log_store import (
    MAX_ENTRIES_PER_REQUEST,
    BaseLogStore,
)
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.logger import get_logger
from zenml.models import LogsResponse

if TYPE_CHECKING:
    from opentelemetry.sdk._logs.export import LogExporter

    from zenml.utils.logging_utils import LogEntry

logger = get_logger(__name__)


class OtelLogStore(BaseLogStore):
    """Log store that exports logs using OpenTelemetry.

    Subclasses should implement `get_exporter()` to provide the specific
    log exporter for their backend.
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
        self._logger: Optional["Logger"] = None
        self._handler: Optional["LoggingHandler"] = None

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
        self._exporter = self.get_exporter()
        self._processor = BatchLogRecordProcessor(
            self._exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=self.config.schedule_delay_millis,
            max_export_batch_size=self.config.max_export_batch_size,
            export_timeout_millis=self.config.export_timeout_millis,
        )

        self._resource = Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
            }
        )

        self._provider = LoggerProvider(resource=self._resource)
        self._provider.add_log_record_processor(self._processor)

        self._logger = self._provider.get_logger(
            "zenml.log_store.emit",
        )
        self._handler = LoggingHandler(logger_provider=self._provider)

    def emit(
        self,
        record: logging.LogRecord,
        log_model: "LogsResponse",
        metadata: Dict[str, Any],
    ) -> None:
        """Process a log record by sending to OpenTelemetry.

        Args:
            record: The log record to process.
            log_model: The log model to emit the log record to.
            metadata: Additional metadata to attach to the log entry.

        Raises:
            RuntimeError: If the OpenTelemetry provider is not initialized.
        """
        with self._lock:
            if not self._provider:
                self.activate()

        if (
            self._provider is None
            or self._logger is None
            or self._handler is None
        ):
            raise RuntimeError("OpenTelemetry provider is not initialized")

        emit_kwargs = self._handler._translate(record)

        attributes = emit_kwargs.get("attributes", {})

        attributes.update(
            {
                "zenml.log_store_id": str(self.id),
                "zenml.log_model.id": str(log_model.id),
                "zenml.log_model.uri": str(log_model.uri),
                "zenml.log_model.artifact_store_id": str(
                    log_model.artifact_store_id
                ),
                "zenml.log_model.source": log_model.source,
                **{f"zenml.{key}": value for key, value in metadata.items()},
            }
        )

        self._logger.emit(**emit_kwargs)

    def finalize(
        self,
        log_model: LogsResponse,
    ) -> None:
        """Finalize the stream of log records associated with a log model.

        Args:
            log_model: The log model to finalize.
        """
        pass

    def flush(self) -> None:
        """Flush the log store.

        This method is called to ensure that all logs are flushed to the backend.
        """
        if self._processor:
            self._processor.force_flush()

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
                self._processor.shutdown()  # type: ignore[no-untyped-call]
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
        limit: int = MAX_ENTRIES_PER_REQUEST,
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

        Returns:
            List of log entries from the backend.
        """
