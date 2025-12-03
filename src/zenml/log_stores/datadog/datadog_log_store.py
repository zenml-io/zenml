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
from typing import Any, Dict, List, Optional, cast

import requests
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)

from zenml.enums import LoggingLevels
from zenml.log_stores.base_log_store import MAX_ENTRIES_PER_REQUEST
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.utils.logging_utils import LogEntry

logger = get_logger(__name__)


class DatadogLogStore(OtelLogStore):
    """Log store that exports logs to Datadog.

    This implementation extends OtelLogStore and configures it to send logs
    to Datadog's HTTP intake API.
    """

    _otlp_exporter: Optional[OTLPLogExporter] = None

    @property
    def config(self) -> DatadogLogStoreConfig:
        """Returns the configuration of the Datadog log store.

        Returns:
            The configuration.
        """
        return cast(DatadogLogStoreConfig, self._config)

    def get_exporter(self) -> OTLPLogExporter:
        """Get the Datadog log exporter.

        Returns:
            DatadogLogExporter configured with API key and site.
        """
        if not self._otlp_exporter:
            self._otlp_exporter = OTLPLogExporter(
                endpoint=f"https://http-intake.logs.{self.config.site}/v1/logs",
                headers={"dd-api-key": self.config.api_key.get_secret_value()},
            )
        return self._otlp_exporter

    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = MAX_ENTRIES_PER_REQUEST,
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

    def cleanup(self) -> None:
        """Cleanup the Datadog log store.

        This method is called when the log store is no longer needed.
        """
        if self._otlp_exporter:
            self._otlp_exporter.shutdown()  # type: ignore[no-untyped-call]
            self._otlp_exporter = None
