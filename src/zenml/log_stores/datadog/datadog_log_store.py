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

import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import requests

from zenml.enums import LoggingLevels
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.datadog.datadog_log_exporter import DatadogLogExporter
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.models.v2.misc.log_models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
)
from zenml.utils.logging_utils import severity_number_threshold

logger = get_logger(__name__)


class DatadogLogStore(OtelLogStore):
    """Log store that exports logs to Datadog.

    This implementation extends OtelLogStore and configures it to send logs
    to Datadog's HTTP intake API.
    """

    _datadog_exporter: Optional[DatadogLogExporter] = None

    @property
    def config(self) -> DatadogLogStoreConfig:
        """Returns the configuration of the Datadog log store.

        Returns:
            The configuration.
        """
        return cast(DatadogLogStoreConfig, self._config)

    def _get_headers(self) -> Dict[str, str]:
        """Get the headers for the Datadog log store.

        Returns:
            The headers.
        """
        headers: Dict[str, str] = self.config.headers or {}

        headers.update(
            {
                "dd-api-key": self.config.api_key.get_secret_value(),
                "dd-application-key": self.config.application_key.get_secret_value(),
            }
        )
        return headers

    def get_exporter(self) -> DatadogLogExporter:
        """Get the Datadog log exporter.

        Returns:
            DatadogExporter with the proper configuration.
        """
        if not self._datadog_exporter:
            self._datadog_exporter = DatadogLogExporter(
                endpoint=self.config.endpoint,
                headers=self._get_headers(),
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )
        return self._datadog_exporter

    def fetch(
        self,
        logs_model: LogsResponse,
        limit: int,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Fetch logs from Datadog's API.

        This method queries Datadog's Logs API to retrieve logs for the
        specified pipeline run and step. It automatically paginates through
        results to fetch up to the requested limit.

        Args:
            logs_model: The logs model containing run and step metadata.
            limit: Maximum number of log entries to return.
            before: Cursor token pointing to older entries.
            after: Cursor token pointing to newer entries.
            filter_: Filters that must be applied during retrieval.

        Returns:
            List of log entries from Datadog.
        """
        if limit <= 0:
            raise ValueError("`limit` must be positive.")

        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        query = self.build_query(logs_model=logs_model, filter_=filter_)

        cursor: Optional[str] = None

        since_ns = logs_model.created
        until_ns = datetime.now(timezone.utc)

        if filter_ and filter_.since:
            since_ns = filter_.since
        if filter_ and filter_.until:
            until_ns = filter_.until

        if after is not None:
            since_ns = datetime.strptime(self._decode_cursor(after))
        elif before is not None:
            until_ns = datetime.strptime(self._decode_cursor(before))

        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )

        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        body: Dict[str, Any] = {
            "filter": {
                "query": query,
                "from": since_ns.isoformat(),
                "to": until_ns.isoformat(),
            },
            "page": {
                "limit": limit,
            },
            "sort": "timestamp" if after else "-timestamp",
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
            raise Exception("")

        data = response.json()
        logs = data.get("data", [])

        log_entries: List[LogEntry] = []

        for log in logs:
            entry = self._parse_log_entry(log)
            if entry:
                log_entries.append(entry)

        before_token = self._encode_cursor(log_entries[0].timestamp)
        after_token = self._encode_cursor(log_entries[-1].timestamp)

        return LogsEntriesResponse(
            items=log_entries,
            before=before_token,
            after=after_token,
        )

    @classmethod
    def _encode_cursor(cls, pos: datetime) -> str:
        """Encode a cursor token into a base64 URL-safe string.

        Args:
            pos: The cursor position.

        Returns:
            The encoded cursor.
        """
        if pos.tzinfo is None:
            pos = pos.replace(tzinfo=timezone.utc)
        else:
            pos = pos.astimezone(timezone.utc)

        payload = {"ts": pos.isoformat()}
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(data).decode("ascii")

    @classmethod
    def _decode_cursor(cls, token: str) -> datetime:
        """Decode a cursor token into a dictionary.

        Args:
            token: The cursor token.

        Returns:
            The decoded cursor.
        """
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
        timestamp = decoded["ts"]
        if isinstance(timestamp, str):
            timestamp = timestamp.replace("Z", "+00:00")
        return datetime.fromisoformat(timestamp)

    def build_query(
        self, logs_model: LogsResponse, filter_: LogsEntriesFilter
    ) -> str:
        """Build a query to fetch log entries from Datadog.

        Args:
            logs_model: The logs model containing metadata about the logs.
            filter_: Filters that must be applied during retrieval.

        Returns:
            The query.
        """
        query_parts = [
            f"service:{self.config.service_name}",
            f"@zenml.log.id:{logs_model.id}",
        ]

        if filter_ and filter_.level:
            threshold = severity_number_threshold(filter_.level)
            query_parts.append(f"@severity_number:>={threshold}")

        if filter_ and filter_.search:
            # Best-effort translation; we still post-filter to match
            # substring semantics.
            query_parts.append(filter_.search)

        return " ".join(query_parts)

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

            # Prefer nested Datadog attributes timestamp (epoch ms), and
            # fall back to outer attributes timestamp (ISO string).
            timestamp_raw = nested_attrs.get("timestamp")
            if timestamp_raw is None:
                timestamp_raw = log_fields.get("timestamp")

            if isinstance(timestamp_raw, (int, float)):
                timestamp = datetime.fromtimestamp(
                    float(timestamp_raw) / 1000.0,
                    tz=timezone.utc,
                )
            elif isinstance(timestamp_raw, str):
                timestamp = datetime.fromisoformat(
                    timestamp_raw.replace("Z", "+00:00")
                )
            else:
                raise ValueError(
                    "Datadog log entry is missing a valid timestamp."
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
        if self._datadog_exporter:
            self._datadog_exporter.shutdown()
            self._datadog_exporter = None
