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

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk.resources import Resource

from zenml.log_stores.base_log_store import BaseLogStore
from zenml.log_stores.otel.otel_flavor import OtelLogStoreConfig
from zenml.logger import get_logger, get_storage_log_level, logging_handlers
from zenml.models import LogsRequest

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import LogExporter

    from zenml.logging.step_logging import LogEntry
    from zenml.models import LogsResponse

logger = get_logger(__name__)


class OtelLogStore(BaseLogStore):
    """Log store that exports logs using OpenTelemetry.

    This implementation uses the OpenTelemetry SDK to collect and export logs
    to various backends. It uses a BatchLogRecordProcessor for efficient
    background processing.

    Subclasses should implement `get_exporter()` to provide the specific
    log exporter for their backend (e.g., console, OTLP, Datadog).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the OpenTelemetry log store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._logger_provider_with_resource: Optional["LoggerProvider"] = None
        self._handler: Optional[logging.Handler] = None
        self._exporter: Optional["LogExporter"] = None
        self._log_id: Optional[str] = None

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
        exporter for their backend (e.g., ConsoleLogExporter, OTLPLogExporter).

        Returns:
            The log exporter instance.
        """

    def activate(self, log_request: "LogsRequest") -> None:
        """Activate log collection with OpenTelemetry.

        Args:
            log_request: The log request model.
        """
        from zenml.logging.otel_logging_infrastructure import (
            get_shared_otel_infrastructure,
        )
        from zenml.logging.routing_handler import set_active_log_store

        # Get shared OTel infrastructure
        logger_provider, routing_exporter = get_shared_otel_infrastructure()

        # Get exporter for this log store
        self._exporter = self.get_exporter()

        # Register exporter with routing exporter
        self._log_id = str(log_request.id)
        routing_exporter.register_exporter(self._log_id, self._exporter)

        # Create resource with log_id and service info
        otel_resource = Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": "0.91.0",  # TODO: Fetch this
                "zenml.log_id": self._log_id,
            }
        )

        # Create logger provider with this resource
        self._logger_provider_with_resource = LoggerProvider(
            resource=otel_resource
        )

        # Share the same processor (routing exporter) from the global provider
        for processor in (
            logger_provider._multi_log_record_processor._log_record_processors
        ):
            self._logger_provider_with_resource.add_log_record_processor(
                processor
            )

        # Create handler
        self._handler = LoggingHandler(
            level=get_storage_log_level().value,
            logger_provider=self._logger_provider_with_resource,
        )

        # Register this log store for routing
        set_active_log_store(self)

        # Add to context variables for print capture
        logging_handlers.add(self._handler)

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record by sending to OpenTelemetry.

        Args:
            record: The log record to process.
        """
        if self._handler:
            try:
                self._handler.emit(record)
            except Exception:
                # Don't let logging errors break execution
                pass

    def deactivate(self) -> None:
        """Deactivate log collection and flush remaining logs."""
        if not self._handler:
            return

        # Unregister from the current thread's context
        from zenml.logging.otel_logging_infrastructure import (
            get_shared_otel_infrastructure,
        )
        from zenml.logging.routing_handler import set_active_log_store

        set_active_log_store(None)

        # Remove from context variables
        logging_handlers.remove(self._handler)

        # Unregister exporter from routing
        if self._log_id and self._exporter:
            _, routing_exporter = get_shared_otel_infrastructure()
            routing_exporter.unregister_exporter(self._log_id)

            # Flush exporter
            try:
                self._exporter.force_flush()
            except Exception as e:
                logger.warning(f"Error flushing exporter: {e}")

        logger.debug("OtelLogStore deactivated")

    @abstractmethod
    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
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
