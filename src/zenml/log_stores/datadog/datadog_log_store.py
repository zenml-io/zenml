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
from typing import Any, Dict, Optional, Sequence, Tuple, cast

import requests

from zenml.enums import LoggingLevels
from zenml.log_stores.datadog.datadog_flavor import (
    DATADOG_MAX_PAGE_SIZE,
    DatadogLogStoreConfig,
)
from zenml.log_stores.datadog.datadog_log_exporter import DatadogLogExporter
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsResponse,
)
from zenml.utils.time_utils import (
    iso8601_to_utc_naive,
    to_utc_timezone,
    utc_now,
)

logger = get_logger(__name__)

# Datadog status labels grouped by ZenML level. Several spellings exist
# because intake and the customer's remapper do not agree on one word.
_STATUSES_BY_LEVEL: Sequence[Tuple[int, Tuple[str, ...]]] = (
    (LoggingLevels.DEBUG.value, ("trace", "debug")),
    (LoggingLevels.INFO.value, ("info", "notice")),
    (LoggingLevels.WARNING.value, ("warn", "warning")),
    (LoggingLevels.ERROR.value, ("err", "error")),
    (
        LoggingLevels.CRITICAL.value,
        ("crit", "critical", "alert", "emerg", "emergency", "fatal"),
    ),
)
_LEVEL_BY_STATUS = {
    status: LoggingLevels(level)
    for level, group in _STATUSES_BY_LEVEL
    for status in group
}


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
        """Headers shared by the exporter and the search API.

        Returns:
            The headers.
        """
        headers: Dict[str, str] = dict(self.config.headers or {})
        headers.update(
            {
                "dd-api-key": self.config.api_key.get_secret_value(),
                "dd-application-key": (
                    self.config.application_key.get_secret_value()
                ),
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
        logs_model: "LogsResponse",
        start: Optional[str] = None,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Fetch a page of log entries from the Datadog Logs API.

        Args:
            logs_model: The logs model containing run and step metadata.
            start: Which end of the stream to start reading from. Omit it
                to read from the oldest end.
            limit: Maximum number of log entries to return.
            before: Cursor towards older entries, from a previous page.
            after: Cursor towards newer entries, from a previous page.
            filter_: Filters to apply while retrieving the entries.

        Returns:
            A page of log entries, oldest first.

        Raises:
            ValueError: If the logs model does not belong to this log store,
                or if both cursors are set.
            RuntimeError: If Datadog does not answer with a usable result.
        """
        if logs_model.log_store_id != self.id:
            raise ValueError(
                "logs_model.log_store_id does not match the id of the log "
                "store. These entries were collected by another log store, "
                "which is the one that can read them back."
            )

        if before is not None and after is not None:
            raise ValueError("Pass only one of `before` and `after`.")

        # Datadog's token only continues the scan it was issued for.
        if before is not None:
            if start == "oldest":
                raise ValueError(
                    "The datadog log store cannot honor `before` on a read "
                    "that started at the oldest end."
                )
            descending = True
        elif after is not None:
            if start == "newest":
                raise ValueError(
                    "The datadog log store cannot honor `after` on a read "
                    "that started at the newest end."
                )
            descending = False
        else:
            descending = start == "newest"

        filter_ = filter_ or LogsEntriesFilter()
        limit = min(self.resolve_limit(limit), DATADOG_MAX_PAGE_SIZE)
        since = filter_.since or to_utc_timezone(logs_model.created)
        until = filter_.until or utc_now(tz_aware=True)
        sort = "-timestamp" if descending else "timestamp"

        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        body: Dict[str, Any] = {
            "filter": {
                "query": self._build_query(logs_model, filter_),
                "from": since.isoformat(),
                "to": until.isoformat(),
            },
            "page": {"limit": limit},
            "sort": sort,
        }
        if page_cursor := before or after:
            body["page"]["cursor"] = self.decode_cursor(page_cursor)

        try:
            response = requests.post(
                f"https://api.{self.config.site}/api/v2/logs/events/search",
                headers=headers,
                json=body,
                timeout=30,
            )
        except requests.RequestException as e:
            logger.exception("Datadog log search failed")
            raise RuntimeError(
                "Could not reach Datadog to read these logs."
            ) from e

        if response.status_code != 200:
            logger.error(
                "Datadog rejected a log search with %s: %s",
                response.status_code,
                response.text[:500],
            )
            raise RuntimeError(
                f"Datadog rejected the log search with status "
                f"{response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as e:
            raise RuntimeError(
                "Datadog returned a response that could not be read as a log "
                "search result."
            ) from e

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Datadog returned a response that could not be read as a log "
                "search result."
            )

        events = payload.get("data") or []
        entries = [
            entry
            for entry in (self._parse_log_entry(event) for event in events)
            if entry is not None
        ]
        if descending:
            entries.reverse()

        # Datadog keeps issuing a token past the last page. Following it
        # would never terminate, so an empty page is the end of this scan.
        native_cursor = (
            payload.get("meta", {}).get("page", {}).get("after")
            if events
            else None
        )
        encoded = self.encode_cursor(native_cursor) if native_cursor else None

        return LogsEntriesResponse(
            items=entries,
            before=encoded if descending else None,
            after=encoded if not descending else None,
        )

    def _build_query(
        self, logs_model: "LogsResponse", filter_: LogsEntriesFilter
    ) -> str:
        """Build the Datadog search query for a log stream.

        Args:
            logs_model: The logs model containing run and step metadata.
            filter_: Filters to apply while retrieving the entries.

        Returns:
            The Datadog search query.
        """
        query = [
            f"service:{self.config.service_name}",
            f"@zenml.log.id:{logs_model.id}",
        ]

        if filter_.search:
            escaped = (
                filter_.search.replace("\\", "\\\\")
                .replace("*", "\\*")
                .replace("?", "\\?")
                .replace('"', '\\"')
            )
            query.append(f"*{escaped}*")

        if filter_.level and filter_.level.value > LoggingLevels.DEBUG.value:
            statuses = [
                status
                for level, group in _STATUSES_BY_LEVEL
                for status in group
                if level >= filter_.level.value
            ]
            query.append(f"status:({' OR '.join(statuses)})")

        return " ".join(query)

    def _parse_log_entry(self, log: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a single log entry from Datadog's API response.

        Args:
            log: The log entry from Datadog's API response.

        Returns:
            The parsed log entry.
        """
        try:
            log_fields = log.get("attributes", {})
            message = log_fields.get("message", "")
            nested_attrs = log_fields.get("attributes", {})

            if exc_info := nested_attrs.get("exception"):
                message += (
                    f"\n{exc_info.get('type')}: {exc_info.get('message')}\n"
                    f"{exc_info.get('stacktrace')}"
                )

            code_info = nested_attrs.get("code", {})
            filename = code_info.get("file", {}).get("path")
            lineno = code_info.get("line", {}).get("number")
            function_name = code_info.get("function", {}).get("name")
            logger_name = (
                nested_attrs.get("otel", {}).get("library", {}).get("name")
            )

            timestamp_raw = nested_attrs.get("timestamp")
            if timestamp_raw is None:
                timestamp_raw = log_fields.get("timestamp")

            if isinstance(timestamp_raw, (int, float)):
                timestamp = datetime.fromtimestamp(
                    float(timestamp_raw) / 1000.0,
                    tz=timezone.utc,
                )
            elif isinstance(timestamp_raw, str):
                timestamp = iso8601_to_utc_naive(timestamp_raw)
            else:
                raise ValueError(
                    "Datadog log entry is missing a valid timestamp."
                )

            status = str(log_fields.get("status", "info")).lower()
            module = None
            if function_name:
                module = function_name
            elif filename:
                module = filename.rsplit("/", 1)[-1].replace(".py", "")

            return LogEntry(
                message=message,
                level=_LEVEL_BY_STATUS.get(status, LoggingLevels.INFO),
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
