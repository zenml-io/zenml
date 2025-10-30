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
from uuid import UUID

from zenml.log_stores.base_log_store import BaseLogStore
from zenml.logger import get_logger, get_storage_log_level, logging_handlers
from zenml.utils.string_utils import random_str

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
        self.logger_provider: Optional["LoggerProvider"] = None
        self.handler: Optional[logging.Handler] = None
        self._original_root_level: Optional[int] = None
        self._pipeline_run_id: Optional[UUID] = None
        self._step_id: Optional[UUID] = None
        self._source: Optional[str] = None

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

    def activate(
        self,
        pipeline_run_id: UUID,
        step_id: Optional[UUID] = None,
        source: str = "step",
    ) -> None:
        """Activate log collection with OpenTelemetry.

        Args:
            pipeline_run_id: The ID of the pipeline run.
            step_id: The ID of the step (if collecting step logs).
            source: The source of the logs (e.g., "step", "orchestrator").
        """
        try:
            from opentelemetry.sdk._logs import LoggerProvider
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
            from opentelemetry.sdk.resources import Resource
        except ImportError:
            logger.error(
                "OpenTelemetry SDK not installed. Install with: "
                "pip install opentelemetry-sdk opentelemetry-exporter-otlp"
            )
            return

        # Store metadata
        self._pipeline_run_id = pipeline_run_id
        self._step_id = step_id
        self._source = source

        # Create resource with service information and ZenML metadata
        resource_attributes = {
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "service.instance.id": random_str(8),
            "deployment.environment": self.config.deployment_environment,
            "zenml.pipeline_run_id": str(pipeline_run_id),
            "zenml.source": source,
        }
        if step_id:
            resource_attributes["zenml.step_id"] = str(step_id)

        otel_resource = Resource.create(resource_attributes)

        # Create logger provider
        self.logger_provider = LoggerProvider(resource=otel_resource)

        # Get exporter from subclass
        exporter = self.get_exporter()

        # Create batch processor for efficient background processing
        processor = BatchLogRecordProcessor(
            exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=self.config.schedule_delay_millis,
            max_export_batch_size=self.config.max_export_batch_size,
        )
        self.logger_provider.add_log_record_processor(processor)

        # Create handler for Python logging integration
        try:
            from opentelemetry.sdk._logs import LoggingHandler

            self.handler = LoggingHandler(
                level=get_storage_log_level().value,
                logger_provider=self.logger_provider,
            )
        except ImportError:
            logger.error(
                "Failed to import LoggingHandler from OpenTelemetry SDK"
            )
            return

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.handler)

        # Set root logger level to minimum of all handlers
        self._original_root_level = root_logger.level
        handler_levels = [handler.level for handler in root_logger.handlers]
        min_level = min(handler_levels)
        if min_level < root_logger.level:
            root_logger.setLevel(min_level)

        # Add to context variables for print capture
        logging_handlers.add(self.handler)

        logger.debug(
            f"OtelLogStore activated for {source} "
            f"(pipeline_run={pipeline_run_id}, step={step_id})"
        )

    def deactivate(self) -> None:
        """Deactivate log collection and flush remaining logs."""
        if not self.handler:
            return

        # Remove handler from root logger
        root_logger = logging.getLogger()
        if self.handler in root_logger.handlers:
            root_logger.removeHandler(self.handler)

        # Restore original root logger level
        if self._original_root_level is not None:
            root_logger.setLevel(self._original_root_level)

        # Remove from context variables
        logging_handlers.remove(self.handler)

        # Flush and shutdown logger provider
        if self.logger_provider:
            try:
                self.logger_provider.force_flush()
                self.logger_provider.shutdown()
            except Exception as e:
                logger.warning(
                    f"Error shutting down OTel logger provider: {e}"
                )

        logger.debug("OtelLogStore deactivated")

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
        logger.warning(
            "OtelLogStore.fetch() not implemented. "
            "Subclasses should override this method to query their backend."
        )
        return []
