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
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast

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
    BaseLogStoreOrigin,
)
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.logger import get_logger
from zenml.models import LogsResponse

if TYPE_CHECKING:
    from opentelemetry.sdk._logs.export import LogExporter

    from zenml.utils.logging_utils import LogEntry

logger = get_logger(__name__)


class OtelBatchLogRecordProcessor(BatchLogRecordProcessor):
    """OpenTelemetry batch log record processor.

    This is a subclass of the BatchLogRecordProcessor that allows for a
    non-blocking flush.
    """

    def flush(self, blocking: bool = True) -> bool:
        """Force flush the batch log record processor.

        Args:
            blocking: Whether to block until the flush is complete.

        Returns:
            True if the flush is successful, False otherwise.
        """
        if not blocking:
            # For a non-blocking flush, we simply need to wake up the worker
            # thread and it will handle the flush in the background.
            self._batch_processor._worker_awaken.set()
            return True
        else:
            return self.force_flush()


class OtelLogStoreOrigin(BaseLogStoreOrigin):
    """OpenTelemetry log store origin."""

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
        metadata = {f"zenml.{key}": value for key, value in metadata.items()}

        metadata.update(
            {
                "zenml.log.id": str(log_model.id),
                "zenml.log.source": log_model.source,
                "zenml.log_store.id": str(log_store.id),
                "zenml.log_store.name": log_store.name,
            }
        )

        super().__init__(name, log_store, log_model, metadata)
        assert isinstance(log_store, OtelLogStore)

        self._logger = log_store.provider.get_logger(name)

    @property
    def logger(self) -> "Logger":
        """Returns the OpenTelemetry logger for this origin.

        Returns:
            The logger.
        """
        return self._logger


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
        self._processor: Optional["OtelBatchLogRecordProcessor"] = None
        self._handler: Optional["LoggingHandler"] = None

    @property
    def config(self) -> OtelLogStoreConfig:
        """Returns the configuration of the OTel log store.

        Returns:
            The configuration.
        """
        return cast(OtelLogStoreConfig, self._config)

    @property
    def origin_class(self) -> Type[OtelLogStoreOrigin]:
        """Class of the origin.

        Returns:
            The class of the origin.
        """
        return OtelLogStoreOrigin

    @property
    def provider(self) -> "LoggerProvider":
        """Returns the OpenTelemetry logger provider.

        Returns:
            The logger provider.

        Raises:
            RuntimeError: If the OpenTelemetry log store is not initialized.
        """
        if not self._provider:
            raise RuntimeError("OpenTelemetry log store is not initialized")
        return self._provider

    def get_exporter(self) -> "LogExporter":
        """Get the Datadog log exporter.

        Returns:
            OTLPLogExporter configured with API key and site.
        """
        if not self._exporter:
            self._exporter = OTLPLogExporter(
                endpoint=self.config.endpoint,
                headers=self.config.headers,
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )

        return self._exporter

    def _activate(self) -> None:
        """Activate log collection with OpenTelemetry."""
        self._exporter = self.get_exporter()
        self._processor = OtelBatchLogRecordProcessor(
            exporter=self._exporter,
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
        self._handler = LoggingHandler(logger_provider=self._provider)

    def register_origin(
        self, name: str, log_model: LogsResponse, metadata: Dict[str, Any]
    ) -> BaseLogStoreOrigin:
        """Register an origin for the log store.

        Args:
            name: The name of the origin.
            log_model: The log model associated with the origin.
            metadata: Additional metadata to attach to the log entry.

        Returns:
            The origin.
        """
        with self._lock:
            if not self._provider:
                self._activate()

        return super().register_origin(name, log_model, metadata)

    def emit(
        self,
        origin: BaseLogStoreOrigin,
        record: logging.LogRecord,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Process a log record by sending to OpenTelemetry.

        Args:
            origin: The origin used to send the log record.
            record: The log record to process.
            metadata: Additional metadata to attach to the log entry.

        Raises:
            RuntimeError: If the OpenTelemetry provider is not initialized.
        """
        assert isinstance(origin, OtelLogStoreOrigin)
        with self._lock:
            if not self._provider:
                self._activate()

            if self._handler is None:
                raise RuntimeError("OpenTelemetry provider is not initialized")

            emit_kwargs = self._handler._translate(record)
            emit_kwargs["attributes"].update(origin.metadata)
            if metadata:
                emit_kwargs["attributes"].update(metadata)

            origin.logger.emit(**emit_kwargs)

    def _release_origin(
        self,
        origin: BaseLogStoreOrigin,
    ) -> None:
        """Finalize the stream of log records associated with an origin.

        Args:
            origin: The origin to finalize.
        """
        pass

    def flush(self, blocking: bool = True) -> None:
        """Flush the log store.

        Args:
            blocking: Whether to block until the flush is complete.

        This method is called to ensure that all logs are flushed to the backend.
        """
        with self._lock:
            if self._processor:
                self._processor.flush(blocking=blocking)

    def deactivate(self) -> None:
        """Deactivate log collection and shut down the processor.

        Flushes any pending logs and shuts down the processor's background thread.
        """
        with self._lock:
            if self._processor:
                try:
                    # Force flush any pending logs
                    self._processor.flush(blocking=True)
                    logger.debug("Flushed pending logs")
                except Exception as e:
                    logger.warning(f"Error flushing logs: {e}")

                try:
                    self._processor.shutdown()  # type: ignore[no-untyped-call]
                    logger.debug(
                        "Shut down log processor and background thread"
                    )
                except Exception as e:
                    logger.warning(f"Error shutting down processor: {e}")
                else:
                    self._processor = None
                    self._handler = None
                    self._provider = None
                    self._resource = None
                    self._exporter = None

        logger.debug("OtelLogStore deactivated")

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

        Raises:
            NotImplementedError: Log fetching is not supported by the OTEL log
                store.
        """
        raise NotImplementedError(
            "Log fetching is not supported by the OTEL log store."
        )
