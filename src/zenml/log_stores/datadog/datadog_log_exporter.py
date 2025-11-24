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
"""OpenTelemetry exporter that sends logs to Datadog."""

from typing import Any, List

import requests
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

from zenml.logger import get_logger

logger = get_logger(__name__)


class DatadogLogExporter(LogExporter):
    """Custom log exporter that sends logs to Datadog's HTTP intake API.

    This exporter transforms OpenTelemetry log records into Datadog's format
    and sends them via HTTP POST without requiring the Datadog SDK.
    """

    def __init__(
        self,
        api_key: str,
        site: str = "datadoghq.com",
    ):
        """Initialize the Datadog log exporter.

        Args:
            api_key: Datadog API key.
            site: Datadog site domain.
        """
        self.endpoint = f"https://http-intake.logs.{site}/v1/input"
        self.headers = {
            "DD-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    def export(self, batch: List[LogData]) -> Any:
        """Export a batch of log records to Datadog.

        Args:
            batch: List of LogData objects from OpenTelemetry.

        Returns:
            LogExportResult indicating success or failure.
        """
        logs = []
        for log_data in batch:
            log_record = log_data.log_record

            resource_attrs = {}
            if log_record.resource:
                resource_attrs = dict(log_record.resource.attributes)

            log_attrs = {}
            if log_record.attributes:
                log_attrs = dict(log_record.attributes)

            all_attrs = {**resource_attrs, **log_attrs}

            log_entry = {
                "message": str(log_record.body),
            }

            if log_record.severity_text:
                log_entry["status"] = log_record.severity_text.lower()

            if log_record.timestamp:
                log_entry["timestamp"] = int(log_record.timestamp / 1_000_000)

            if all_attrs:
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
        except Exception:
            logger.exception("Failed to export logs to Datadog")
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
