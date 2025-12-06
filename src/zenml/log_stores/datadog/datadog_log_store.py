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

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import requests

from zenml.enums import LoggingLevels
from zenml.log_stores.base_log_store import MAX_ENTRIES_PER_REQUEST
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
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
            OTLPLogExporter configured with API key and site.
        """
        if not self._otlp_exporter:
            self._otlp_exporter = OTLPLogExporter(
                endpoint=f"https://otlp.{self.config.site}/v1/logs",
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
        specified pipeline run and step. It automatically paginates through
        results to fetch up to the requested limit.

        Args:
            logs_model: The logs model containing run and step metadata.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries from Datadog.
        """
        query_parts = [
            f"service:{self.config.service_name}",
            f"@zenml.log_model.id:{logs_model.id}",
        ]

        query = " ".join(query_parts)

        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )
        headers = {
            "DD-API-KEY": self.config.api_key.get_secret_value(),
            "DD-APPLICATION-KEY": self.config.application_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        log_entries: List[LogEntry] = []
        cursor: Optional[str] = None
        remaining = limit

        try:
            while remaining > 0:
                # Datadog API limit is 1000 per request
                page_limit = min(remaining, 1000)

                body: Dict[str, Any] = {
                    "filter": {
                        "query": query,
                        "from": (
                            start_time.isoformat()
                            if start_time
                            else logs_model.created.isoformat()
                        ),
                        "to": (
                            end_time.isoformat()
                            if end_time
                            else datetime.now().astimezone().isoformat()
                        ),
                    },
                    "page": {
                        "limit": page_limit,
                    },
                    "sort": "@otel.timestamp",
                }

                if cursor:
                    body["page"]["cursor"] = cursor

                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=body,
                    timeout=30,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch logs from Datadog: "
                        f"{response.status_code} - {response.text[:200]}"
                    )
                    break

                data = response.json()
                logs = data.get("data", [])

                if not logs:
                    break

                for log in logs:
                    entry = self._parse_log_entry(log)
                    if entry:
                        log_entries.append(entry)

                remaining -= len(logs)

                # Get cursor for next page
                cursor = data.get("meta", {}).get("page", {}).get("after")
                if not cursor:
                    break

            logger.debug(f"Fetched {len(log_entries)} logs from Datadog")
            return log_entries

        except Exception as e:
            logger.exception(f"Error fetching logs from Datadog: {e}")
            return log_entries  # Return what we have so far

    def _parse_log_entry(self, log: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a single log entry from Datadog's API response.

        Args:
            log: The log data from Datadog's API.

        Returns:
            A LogEntry object, or None if parsing fails.
        """
        try:
            log_fields = log.get("attributes", {})
            message = log_fields.get("message", "")
            nested_attrs = log_fields.get("attributes", {})

            if exc_info := nested_attrs.get("exception"):
                exc_message = exc_info.get("message")
                exc_type = exc_info.get("type")
                exc_stacktrace = exc_info.get("stacktrace")
                message += f"\n{exc_type}: {exc_message}\n{exc_stacktrace}"

            code_info = nested_attrs.get("code", {})
            filename = code_info.get("file", {}).get("path")
            lineno = code_info.get("line", {}).get("number")
            function_name = code_info.get("function", {}).get("name")

            otel_info = nested_attrs.get("otel", {})
            logger_name = otel_info.get("library", {}).get("name")

            timestamp_ns_str = otel_info.get("timestamp")
            if timestamp_ns_str:
                timestamp_ns = int(timestamp_ns_str)
                timestamp = datetime.fromtimestamp(
                    timestamp_ns / 1e9, tz=timezone.utc
                )
            else:
                timestamp = datetime.fromisoformat(
                    log_fields["timestamp"].replace("Z", "+00:00")
                )

            severity = log_fields.get("status", "info").upper()
            log_severity = (
                LoggingLevels[severity]
                if severity in LoggingLevels.__members__
                else LoggingLevels.INFO
            )

            module = None
            if function_name:
                module = function_name
            elif filename:
                module = filename.rsplit("/", 1)[-1].replace(".py", "")

            return LogEntry(
                message=message,
                level=log_severity,
                timestamp=timestamp,
                name=logger_name,
                filename=filename,
                lineno=lineno,
                module=module,
            )
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None

    def cleanup(self) -> None:
        """Cleanup the Datadog log store.

        This method is called when the log store is no longer needed.
        """
        if self._otlp_exporter:
            self._otlp_exporter.shutdown()
            self._otlp_exporter = None
