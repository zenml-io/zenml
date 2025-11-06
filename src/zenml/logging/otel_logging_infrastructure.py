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
"""Shared OpenTelemetry logging infrastructure for all log stores.

Provides a unified backend using a single BatchLogRecordProcessor.
All log stores share this infrastructure, routing logs by log_id to
specific exporters.
"""

import concurrent.futures
import threading
import time
from typing import TYPE_CHECKING, Dict, Optional, Sequence

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    LogExporter,
    LogExportResult,
)

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData

from zenml.logger import get_logger

logger = get_logger(__name__)

# Global shared infrastructure (singleton per process)
_shared_logger_provider: Optional[LoggerProvider] = None
_routing_exporter: Optional["RoutingLogExporter"] = None
_infrastructure_lock = threading.Lock()


class RoutingLogExporter(LogExporter):
    """Routes logs to different exporters based on log_id.

    Processes exports in parallel using a thread pool for better performance
    when multiple log stores are active.
    """

    def __init__(self, max_concurrent_exporters: int = 10):
        """Initialize the routing exporter with thread pool.

        Args:
            max_concurrent_exporters: Maximum number of exporters to run in parallel.
        """
        self._exporters: Dict[str, LogExporter] = {}
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_exporters,
            thread_name_prefix="zenml-log-export",
        )
        self._export_count = 0
        self._slow_export_count = 0

    def register_exporter(self, log_id: str, exporter: LogExporter) -> None:
        """Register an exporter for a specific log_id.

        Args:
            log_id: Unique identifier for the log store.
            exporter: The exporter to handle logs for this log_id.
        """
        with self._lock:
            self._exporters[log_id] = exporter
            logger.debug(f"Registered exporter for log_id: {log_id}")

    def unregister_exporter(self, log_id: str) -> None:
        """Unregister an exporter for a specific log_id.

        Args:
            log_id: The log_id to unregister.
        """
        with self._lock:
            exporter = self._exporters.pop(log_id, None)
            if exporter:
                logger.debug(f"Unregistered exporter for log_id: {log_id}")

    def export(self, batch: Sequence["LogData"]) -> LogExportResult:
        """Route logs to appropriate exporters based on log_id.

        Logs are grouped by log_id from the Resource attributes, then
        exported in parallel using the thread pool.

        Args:
            batch: Sequence of LogData to export.

        Returns:
            LogExportResult indicating success or failure.
        """
        if not batch:
            return LogExportResult.SUCCESS

        self._export_count += 1
        start_time = time.time()

        # Group logs by log_id
        logs_by_id: Dict[str, list] = {}

        for log_data in batch:
            # Extract log_id from Resource attributes
            log_id = None
            if log_data.log_record.resource:
                attrs = dict(log_data.log_record.resource.attributes)
                log_id = attrs.get("zenml.log_id")

            if log_id:
                logs_by_id.setdefault(log_id, []).append(log_data)
            else:
                logger.debug("Received log without zenml.log_id")

        # Submit all exports to thread pool in parallel
        futures = []
        with self._lock:
            for log_id, logs in logs_by_id.items():
                exporter = self._exporters.get(log_id)
                if exporter:
                    # Submit to thread pool (non-blocking)
                    future = self._executor.submit(
                        self._safe_export, exporter, logs, log_id
                    )
                    futures.append(future)

        # Wait for all exports to complete
        all_success = True
        timeout = 30  # seconds total for all exports

        try:
            for future in concurrent.futures.as_completed(
                futures, timeout=timeout
            ):
                try:
                    result = future.result(timeout=1)
                    if result != LogExportResult.SUCCESS:
                        all_success = False
                except concurrent.futures.TimeoutError:
                    logger.error("Export timeout waiting for result")
                    all_success = False
                except Exception as e:
                    logger.error(f"Export failed: {e}")
                    all_success = False
        except concurrent.futures.TimeoutError:
            logger.error(f"Exports took longer than {timeout}s timeout")
            all_success = False

        # Monitor performance
        duration = time.time() - start_time
        if duration > 1.5:  # Slower than batch interval
            self._slow_export_count += 1
            if self._slow_export_count % 10 == 0:
                logger.warning(
                    f"Slow exports detected: {duration:.2f}s "
                    f"(total slow: {self._slow_export_count}/{self._export_count})"
                )

        return (
            LogExportResult.SUCCESS if all_success else LogExportResult.FAILURE
        )

    def _safe_export(
        self, exporter: LogExporter, logs: Sequence["LogData"], log_id: str
    ) -> LogExportResult:
        """Safely export logs with error handling.

        Args:
            exporter: The exporter to use.
            logs: Logs to export.
            log_id: ID for logging purposes.

        Returns:
            Export result.
        """
        try:
            return exporter.export(logs)
        except Exception as e:
            logger.error(f"Export failed for log_id {log_id}: {e}")
            return LogExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the routing exporter and thread pool."""
        logger.debug("Shutting down routing exporter thread pool")
        try:
            self._executor.shutdown(wait=True, timeout=30)
        except Exception as e:
            logger.warning(f"Error shutting down thread pool: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered logs.

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful.
        """
        # Flush all registered exporters in parallel
        futures = []
        with self._lock:
            for exporter in self._exporters.values():
                future = self._executor.submit(
                    self._safe_flush, exporter, timeout_millis
                )
                futures.append(future)

        # Wait for all flushes
        all_success = True
        timeout_sec = timeout_millis / 1000.0
        try:
            for future in concurrent.futures.as_completed(
                futures, timeout=timeout_sec
            ):
                try:
                    if not future.result(timeout=1):
                        all_success = False
                except Exception as e:
                    logger.warning(f"Force flush failed: {e}")
                    all_success = False
        except concurrent.futures.TimeoutError:
            logger.warning("Force flush timeout")
            all_success = False

        return all_success

    def _safe_flush(self, exporter: LogExporter, timeout_millis: int) -> bool:
        """Safely flush an exporter with error handling.

        Args:
            exporter: The exporter to flush.
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful.
        """
        try:
            return exporter.force_flush(timeout_millis)
        except Exception as e:
            logger.warning(f"Flush failed: {e}")
            return False


def get_shared_otel_infrastructure() -> tuple[
    LoggerProvider, RoutingLogExporter
]:
    """Get or create shared OpenTelemetry logging infrastructure.

    Creates a single LoggerProvider with BatchLogRecordProcessor and
    RoutingLogExporter that all log stores share.

    Returns:
        Tuple of (LoggerProvider, RoutingLogExporter).
    """
    global _shared_logger_provider, _routing_exporter

    if _shared_logger_provider is None:
        with _infrastructure_lock:
            if _shared_logger_provider is None:
                logger.info(
                    "Initializing shared OTel logging infrastructure "
                    "with 1 background thread"
                )

                # Create routing exporter
                _routing_exporter = RoutingLogExporter()

                # Create shared logger provider
                _shared_logger_provider = LoggerProvider()

                # One background thread for all log stores
                processor = BatchLogRecordProcessor(
                    _routing_exporter,
                    max_queue_size=4096,  # Larger for shared use
                    schedule_delay_millis=1000,  # Batch every 1 second
                    max_export_batch_size=512,  # Export in batches of 512
                )
                _shared_logger_provider.add_log_record_processor(processor)

    return _shared_logger_provider, _routing_exporter


def shutdown_shared_infrastructure() -> None:
    """Shutdown the shared OpenTelemetry infrastructure.

    This should be called on process shutdown to cleanly close all resources.
    """
    global _shared_logger_provider, _routing_exporter

    if _shared_logger_provider:
        logger.info("Shutting down shared OTel logging infrastructure")
        try:
            _shared_logger_provider.force_flush()
            _shared_logger_provider.shutdown()
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")

    if _routing_exporter:
        try:
            _routing_exporter.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down routing exporter: {e}")

    _shared_logger_provider = None
    _routing_exporter = None
