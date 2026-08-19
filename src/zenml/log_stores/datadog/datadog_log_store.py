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
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

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
from zenml.utils.time_utils import to_utc_timezone, utc_now

logger = get_logger(__name__)

SEARCH_TIMEOUT = 30

# Number of event IDs carried in a timestamp watermark cursor. Datadog
# timestamps only have millisecond resolution, so resuming a scan at a
# timestamp needs the IDs already seen at it to avoid returning them twice.
# Beyond this many events sharing a single millisecond, a live tail may repeat
# a line, which is preferable to an unbounded cursor in a URL.
BOUNDARY_ID_LIMIT = 50

# ZenML log levels paired with the Datadog statuses of that severity. Several
# spellings are listed per level because which one ends up in the index depends
# on how the log was ingested and on the customer's status remapper.
DATADOG_STATUSES_BY_LEVEL: Sequence[Tuple[int, Tuple[str, ...]]] = (
    (LoggingLevels.DEBUG.value, ("trace", "debug")),
    (LoggingLevels.INFO.value, ("info", "notice")),
    (LoggingLevels.WARNING.value, ("warn", "warning")),
    (LoggingLevels.ERROR.value, ("err", "error")),
    (
        LoggingLevels.CRITICAL.value,
        ("crit", "critical", "alert", "emerg", "emergency", "fatal"),
    ),
)

DATADOG_LEVELS_BY_STATUS: Dict[str, LoggingLevels] = {
    status: LoggingLevels(level)
    for level, group in DATADOG_STATUSES_BY_LEVEL
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

    def get_exporter(self) -> DatadogLogExporter:
        """Get the Datadog log exporter.

        Returns:
            DatadogExporter with the proper configuration.
        """
        if not self._datadog_exporter:
            headers = {
                "dd-api-key": self.config.api_key.get_secret_value(),
                "dd-application-key": self.config.application_key.get_secret_value(),
            }
            if self.config.headers:
                headers.update(self.config.headers)

            self._datadog_exporter = DatadogLogExporter(
                endpoint=self.config.endpoint,
                headers=headers,
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )
        return self._datadog_exporter

    def fetch(
        self,
        logs_model: "LogsResponse",
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Fetch a page of log entries from the Datadog Logs API.

        Every call issues exactly one search request, because Datadog rate
        limits log search per organization and a browsing session that fanned
        one page out into several requests would burn that budget quickly.

        Filters are pushed down into the search query rather than applied here.
        One consequence is that `search` follows Datadog's own full-text
        matching, which is token-based, so it does not match a term in the
        middle of a word the way a substring search would.

        Args:
            logs_model: The logs model containing run and step metadata.
            limit: Maximum number of log entries to return.
            before: Cursor pointing at entries older than a previous page.
            after: Cursor pointing at entries newer than a previous page.
            filter_: Filters to apply while retrieving the entries.

        Returns:
            A page of log entries, oldest first, with cursors for the adjacent
            pages.

        Raises:
            ValueError: If the logs model does not belong to this log store.
            RuntimeError: If Datadog rejects the search request.
        """
        if logs_model.log_store_id != self.id:
            raise ValueError(
                "logs_model.log_store_id does not match the id of the log "
                "store. These entries were collected by another log store, "
                "which is the one that can read them back."
            )

        limit = min(self.resolve_limit(limit), DATADOG_MAX_PAGE_SIZE)
        filter_ = filter_ or LogsEntriesFilter()

        # Paging towards newer entries is the only case where scanning forward
        # in time is useful; a first page and a step back through history both
        # want the newest matching entries first.
        descending = after is None
        token = before or after
        cursor = self.decode_cursor(token) if token else {}

        window_start = filter_.since or to_utc_timezone(logs_model.created)
        window_end = filter_.until or utc_now(tz_aware=True)
        if watermark := cursor.get("timestamp"):
            if descending:
                window_end = self._parse_timestamp(watermark)
            else:
                window_start = self._parse_timestamp(watermark)

        body: Dict[str, Any] = {
            "filter": {
                "query": self._build_query(logs_model, filter_),
                "from": window_start.isoformat(),
                "to": window_end.isoformat(),
            },
            "page": {"limit": limit},
            "sort": "-timestamp" if descending else "timestamp",
        }
        if native_cursor := cursor.get("cursor"):
            body["page"]["cursor"] = native_cursor

        response = requests.post(
            f"https://api.{self.config.site}/api/v2/logs/events/search",
            headers={
                "DD-API-KEY": self.config.api_key.get_secret_value(),
                "DD-APPLICATION-KEY": self.config.application_key.get_secret_value(),
                "Content-Type": "application/json",
            },
            json=body,
            timeout=SEARCH_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Datadog: {response.status_code} - "
                f"{response.text[:200]}"
            )

        payload = response.json()
        seen = set(cursor.get("ids", []))
        data = payload.get("data", [])
        events = [event for event in data if event.get("id") not in seen]
        next_cursor = payload.get("meta", {}).get("page", {}).get("after")

        entries = [
            entry
            for entry in (self._parse_log_entry(event) for event in events)
            if entry is not None
        ]
        if descending:
            events.reverse()
            entries.reverse()

        # An empty page has no entry to anchor a cursor to, so paging stays
        # where it was: the caller keeps the cursor it arrived with. A first
        # page that is empty because the pipeline has not logged anything yet
        # gets a cursor at the start of the window instead, so that a tail can
        # pick the stream up as it fills.
        newer_fallback = after or (
            None
            if before
            else self.encode_cursor(timestamp=window_start.isoformat())
        )

        return LogsEntriesResponse(
            items=entries,
            before=self._get_older_cursor(
                events=events,
                native_cursor=next_cursor,
                descending=descending,
                page_full=len(data) >= limit,
            ),
            after=self._get_newer_cursor(
                events=events,
                native_cursor=next_cursor,
                descending=descending,
                fallback=newer_fallback,
            ),
        )

    def _get_older_cursor(
        self,
        events: List[Dict[str, Any]],
        native_cursor: Optional[str],
        descending: bool,
        page_full: bool,
    ) -> Optional[str]:
        """Build the cursor that continues towards older entries.

        Args:
            events: The raw events of the current page, oldest first.
            native_cursor: The Datadog continuation token for the page, if any.
            descending: Whether the page was scanned towards older entries.
            page_full: Whether Datadog filled the page it was asked for.

        Returns:
            The cursor, or None if there is nothing older to fetch.
        """
        if descending and native_cursor:
            # The scan was already going this way, so its continuation token
            # is the cheapest way to keep going.
            return self.encode_cursor(cursor=native_cursor)

        if descending and not page_full:
            # A page Datadog did not fill, with no token to continue from, is
            # the end of the stream. Reporting no cursor is only safe in this
            # order: a full page without a token has to be treated as more to
            # read, or a token withheld for any other reason would silently
            # cut a run's history short.
            return None

        return (
            self._get_watermark_cursor(events, events[0]) if events else None
        )

    def _get_newer_cursor(
        self,
        events: List[Dict[str, Any]],
        native_cursor: Optional[str],
        descending: bool,
        fallback: Optional[str],
    ) -> Optional[str]:
        """Build the cursor that continues towards newer entries.

        Unlike the cursor towards older entries, this one stays set once the
        stream has been seen at all: the log stream of a running pipeline keeps
        growing, so having caught up with it is not the same as there being
        nothing left to read.

        Args:
            events: The raw events of the current page, oldest first.
            native_cursor: The Datadog continuation token for the page, if any.
            descending: Whether the page was scanned towards older entries.
            fallback: The cursor to use when the page holds no events.

        Returns:
            The cursor, or None if the caller has no way to resume.
        """
        if not descending and native_cursor:
            return self.encode_cursor(cursor=native_cursor)

        return (
            self._get_watermark_cursor(events, events[-1])
            if events
            else fallback
        )

    def _get_watermark_cursor(
        self, events: List[Dict[str, Any]], boundary: Dict[str, Any]
    ) -> str:
        """Build a cursor that resumes a scan at the timestamp of an event.

        Args:
            events: The raw events of the current page.
            boundary: The event the next page should resume at.

        Returns:
            The cursor.
        """
        timestamp = boundary.get("attributes", {}).get("timestamp")
        return self.encode_cursor(
            timestamp=timestamp,
            ids=[
                event["id"]
                for event in events
                if event.get("attributes", {}).get("timestamp") == timestamp
                and event.get("id")
            ][:BOUNDARY_ID_LIMIT],
        )

    def _build_query(
        self, logs_model: "LogsResponse", filter_: LogsEntriesFilter
    ) -> str:
        """Build the Datadog search query for a log stream.

        Args:
            logs_model: The logs model to fetch the entries of.
            filter_: The filters to express in the query.

        Returns:
            The query.
        """
        query = [
            f"service:{self.config.service_name}",
            f"@zenml.log.id:{logs_model.id}",
        ]

        if filter_.search:
            escaped = filter_.search.replace("\\", "\\\\").replace('"', '\\"')
            query.append(f'"{escaped}"')

        if filter_.level and filter_.level.value > LoggingLevels.DEBUG.value:
            statuses = [
                status
                for level, group in DATADOG_STATUSES_BY_LEVEL
                for status in group
                if level >= filter_.level.value
            ]
            query.append(f"status:({' OR '.join(statuses)})")

        return " ".join(query)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        """Parse a Datadog timestamp.

        Args:
            value: An ISO 8601 timestamp as returned by the Datadog API.

        Returns:
            The parsed timestamp.
        """
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

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

            timestamp = self._parse_timestamp(log_fields["timestamp"])

            status = str(log_fields.get("status", "info")).lower()
            log_severity = DATADOG_LEVELS_BY_STATUS.get(
                status, LoggingLevels.INFO
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
