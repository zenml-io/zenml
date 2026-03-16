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
from zenml.exceptions import IllegalOperationError
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

logger = get_logger(__name__)


def _to_unix_ns(dt: datetime) -> int:
    """Convert a datetime to a Unix timestamp in nanoseconds.

    Args:
        dt: The datetime.

    Returns:
        The Unix timestamp in nanoseconds.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp() * 1_000_000_000)


def _from_unix_ns(ns: int) -> datetime:
    """Convert a Unix timestamp in nanoseconds to a datetime.

    Args:
        ns: The Unix timestamp in nanoseconds.

    Returns:
        The datetime.
    """
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)


def _allowed_datadog_statuses(level: LoggingLevels) -> List[str]:
    """Map a minimum ZenML log level to Datadog status values.

    Datadog stores this integration's log level as `status` text instead of
    a numeric OTEL severity field, so level-based filtering needs to query the
    corresponding status labels.

    Args:
        level: The minimum ZenML log level.

    Returns:
        Allowed Datadog status values that satisfy the threshold.
    """
    if level in (LoggingLevels.NOTSET, LoggingLevels.DEBUG):
        return ["debug", "info", "warn", "warning", "error", "critical"]
    if level == LoggingLevels.INFO:
        return ["info", "warn", "warning", "error", "critical"]
    if level in (LoggingLevels.WARN, LoggingLevels.WARNING):
        return ["warn", "warning", "error", "critical"]
    if level == LoggingLevels.ERROR:
        return ["error", "critical"]
    if level == LoggingLevels.CRITICAL:
        return ["critical"]

    return ["info", "warn", "warning", "error", "critical"]


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
        limit: Optional[int] = None,
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

        Raises:
            ValueError: If `limit` is not positive or if both `before` and
                `after` are set.
            IllegalOperationError: If the log store ID does not match the logs model.
            Exception: If the request to Datadog's API fails.
        """
        if self.id != logs_model.log_store_id:
            raise IllegalOperationError(
                f"The log store that you are trying to use {self.name} "
                "does not match the log store ID in the logs model. Please "
                "make sure to use the correct log store."
            )

        if limit is None:
            limit = self.config.default_query_size
        else:
            if limit <= 0:
                raise ValueError("`limit` must be positive.")

        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        query = self.build_query(logs_model=logs_model, filter_=filter_)

        since = logs_model.created
        until = datetime.now(timezone.utc)

        if filter_ and filter_.since:
            since = filter_.since
        if filter_ and filter_.until:
            until = filter_.until

        since_ns = _to_unix_ns(since)
        until_ns = _to_unix_ns(until)

        if after is not None:
            after_cursor = self.decode_cursor(after)
            since_ns = max(since_ns, after_cursor + 1)
        elif before is not None:
            before_cursor = self.decode_cursor(before)
            until_ns = min(until_ns, before_cursor - 1)

        api_endpoint = (
            f"https://api.{self.config.site}/api/v2/logs/events/search"
        )

        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        body: Dict[str, Any] = {
            "filter": {
                "query": query,
                "from": _from_unix_ns(since_ns).isoformat(),
                "to": _from_unix_ns(until_ns).isoformat(),
            },
            "page": {
                "limit": limit,
            },
            "sort": "timestamp" if after else "-timestamp",
        }

        response = requests.post(
            api_endpoint,
            headers=headers,
            json=body,
            timeout=30,
        )

        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch logs from Datadog: {response.status_code} - "
                f"{response.text[:200]}"
            )

        data = response.json()
        logs = data.get("data", [])

        log_entries: List[LogEntry] = []

        for log in logs:
            entry = self._parse_log_entry(log)
            if entry:
                log_entries.append(entry)

        if after is None:
            log_entries.reverse()

        before_token: Optional[str] = None
        after_token: Optional[str] = None

        if log_entries:
            if log_entries[0].timestamp is not None:
                oldest_timestamp = _to_unix_ns(log_entries[0].timestamp)
                after_token = self.encode_cursor(oldest_timestamp)

            if log_entries[-1].timestamp is not None:
                newest_timestamp = _to_unix_ns(log_entries[-1].timestamp)
                before_token = self.encode_cursor(newest_timestamp)

        return LogsEntriesResponse(
            items=log_entries,
            before=before_token,
            after=after_token,
        )

    @classmethod
    def encode_cursor(cls, ts_ns: int) -> str:
        """Encode a cursor timestamp into a base64 URL-safe string.

        Args:
            ts_ns: The timestamp in nanoseconds.

        Returns:
            The encoded cursor.
        """
        payload = {"ts_ns": int(ts_ns)}
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(data).decode("ascii")

    @classmethod
    def decode_cursor(cls, token: str) -> int:
        """Decode a base64 URL-safe string into a cursor timestamp.

        Args:
            token: The base64 URL-safe string.

        Returns:
            The decoded cursor.
        """
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
        return int(decoded.get("ts_ns"))

    def build_query(
        self,
        logs_model: LogsResponse,
        filter_: Optional[LogsEntriesFilter] = None,
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
            statuses = _allowed_datadog_statuses(filter_.level)
            query_parts.append(
                "("
                + " OR ".join(f"status:{status}" for status in statuses)
                + ")"
            )

        if filter_ and filter_.search:
            query_parts.append(f"*{filter_.search}*")

        return " ".join(query_parts)

    @staticmethod
    def _parse_log_entry(log: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a single log entry from Datadog's API response.

        Args:
            log: The log data from Datadog's API.

        Returns:
            A LogEntry object, or None if parsing fails.

        Raises:
            ValueError: If the log entry is missing a valid timestamp.
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
