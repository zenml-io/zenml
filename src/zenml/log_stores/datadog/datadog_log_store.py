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
"""Datadog log store implementation."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger

if TYPE_CHECKING:
    from opentelemetry.sdk._logs.export import LogExporter

    from zenml.logging.step_logging import LogEntry
    from zenml.models import LogsResponse

logger = get_logger(__name__)


class DatadogLogExporter:
    """Custom log exporter that sends logs to Datadog's HTTP intake API.

    This exporter transforms OpenTelemetry log records into Datadog's format
    and sends them via HTTP POST without requiring the Datadog SDK.
    """

    def __init__(
        self,
        api_key: str,
        site: str = "datadoghq.com",
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        """Initialize the Datadog log exporter.

        Args:
            api_key: Datadog API key.
            site: Datadog site domain.
            additional_tags: Additional tags to add to all logs.
        """

        self.headers = {
            "DD-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        self.additional_tags = additional_tags or {}

    def export(self, batch: List[Any]) -> Any:
        """Export a batch of log records to Datadog.

        Args:
            batch: List of LogData objects from OpenTelemetry.

        Returns:
            LogExportResult indicating success or failure.
        """
        try:
            import requests
            from opentelemetry.sdk._logs.export import LogExportResult
        except ImportError:
            logger.error(
                "Required packages not installed. Install with: "
                "pip install requests opentelemetry-sdk"
            )
            from opentelemetry.sdk._logs.export import LogExportResult

            return LogExportResult.FAILURE

        if not batch:
            return LogExportResult.SUCCESS

        logs = []
        for log_data in batch:
            log_record = log_data.log_record

            # Extract resource attributes
            resource_attrs = {}
            if log_record.resource:
                resource_attrs = dict(log_record.resource.attributes)

            # Extract log attributes
            log_attrs = {}
            if log_record.attributes:
                log_attrs = dict(log_record.attributes)

            # Combine attributes with additional tags
            all_attrs = {**resource_attrs, **log_attrs, **self.additional_tags}

            # Build Datadog log entry
            log_entry = {
                "message": str(log_record.body),
                "ddsource": "zenml",
                "service": resource_attrs.get("service.name", "zenml"),
                "hostname": resource_attrs.get(
                    "service.instance.id", "unknown"
                ),
            }

            # Add severity if available
            if log_record.severity_text:
                log_entry["status"] = log_record.severity_text.lower()

            # Add timestamp if available (convert from nanoseconds to milliseconds)
            if log_record.timestamp:
                log_entry["timestamp"] = int(log_record.timestamp / 1_000_000)

            # Add all attributes as tags
            if all_attrs:
                # Convert dict to Datadog tags format: key:value
                tags = [f"{k}:{v}" for k, v in all_attrs.items()]
                log_entry["ddtags"] = ",".join(tags)

            logs.append(log_entry)

        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=logs,
                timeout=10,
            )

            if response.status_code in [200, 202]:
                logger.debug(f"Successfully sent {len(logs)} logs to Datadog")
                return LogExportResult.SUCCESS
            else:
                logger.warning(
                    f"Datadog rejected logs: {response.status_code} - {response.text[:200]}"
                )
                return LogExportResult.FAILURE
        except Exception as e:
            logger.error(f"Failed to export logs to Datadog: {e}")
            return LogExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered logs.

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if successful.
        """
        return True


class DatadogLogStore(OtelLogStore):
    """Log store that exports logs to Datadog.

    This implementation extends OtelLogStore and configures it to send logs
    to Datadog's HTTP intake API. Logs are sent with appropriate tags including
    pipeline_run_id, step_id, and source for easy filtering on Datadog.
    """

    @property
    def config(self) -> DatadogLogStoreConfig:
        """Returns the configuration of the Datadog log store.

        Returns:
            The configuration.
        """
        return cast(DatadogLogStoreConfig, self._config)

    def get_exporter(self) -> "LogExporter":
        """Get the Datadog log exporter.

        Returns:
            DatadogLogExporter configured with API key and site.
        """
        return DatadogLogExporter(
            api_key=self.config.api_key.get_secret_value(),
            site=self.config.site,
            additional_tags=self.config.additional_tags,
        )

    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List["LogEntry"]:
        """Fetch logs from Datadog's API.

        This method queries Datadog's Logs API to retrieve logs for the
        specified pipeline run and step. It uses the HTTP API without
        requiring the Datadog SDK.

        Args:
            logs_model: The logs model containing run and step metadata.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries from Datadog.
        """
        try:
            import requests
        except ImportError:
            logger.error(
                "requests package not installed. Install with: pip install requests"
            )
            return []

        from zenml.logging.step_logging import LogEntry

        # Build query
        query_parts = [
            f"service:{self.config.service_name}",
            f"zenml.pipeline_run_id:{logs_model.pipeline_run_id}",
        ]

        if logs_model.step_run_id:
            query_parts.append(f"zenml.step_id:{logs_model.step_run_id}")

        if logs_model.source:
            query_parts.append(f"zenml.source:{logs_model.source}")

        query = " ".join(query_parts)

        # Build API request
        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )
        headers = {
            "DD-API-KEY": self.config.api_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        body: Dict[str, Any] = {
            "filter": {
                "query": query,
            },
            "page": {
                "limit": min(limit, 1000),  # Datadog API limit
            },
            "sort": "timestamp",
        }

        # Add time filters if provided
        if start_time:
            body["filter"]["from"] = start_time.isoformat()
        if end_time:
            body["filter"]["to"] = end_time.isoformat()

        try:
            response = requests.post(
                api_endpoint,
                headers=headers,
                json=body,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch logs from Datadog: {response.status_code} - {response.text[:200]}"
                )
                return []

            data = response.json()
            log_entries = []

            for log in data.get("data", []):
                attributes = log.get("attributes", {})

                # Parse log entry
                entry = LogEntry(
                    message=attributes.get("message", ""),
                    level=self._parse_log_level(attributes.get("status")),
                    timestamp=datetime.fromisoformat(
                        attributes["timestamp"].replace("Z", "+00:00")
                    )
                    if "timestamp" in attributes
                    else None,
                )

                log_entries.append(entry)

            logger.debug(f"Fetched {len(log_entries)} logs from Datadog")
            return log_entries

        except Exception as e:
            logger.error(f"Error fetching logs from Datadog: {e}")
            return []

    def _parse_log_level(
        self, status: Optional[str]
    ) -> Optional["LoggingLevels"]:
        """Parse Datadog log status to ZenML log level.

        Args:
            status: Datadog log status string.

        Returns:
            ZenML LoggingLevels enum value.
        """
        from zenml.enums import LoggingLevels

        if not status:
            return None

        status_upper = status.upper()
        if status_upper in ["DEBUG", "TRACE"]:
            return LoggingLevels.DEBUG
        elif status_upper in ["INFO", "INFORMATION"]:
            return LoggingLevels.INFO
        elif status_upper in ["WARN", "WARNING"]:
            return LoggingLevels.WARN
        elif status_upper == "ERROR":
            return LoggingLevels.ERROR
        elif status_upper in ["CRITICAL", "FATAL", "EMERGENCY"]:
            return LoggingLevels.CRITICAL
        else:
            return LoggingLevels.INFO
