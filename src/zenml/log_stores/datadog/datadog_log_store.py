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

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import requests

from zenml.enums import LoggingLevels
from zenml.exceptions import (
    LogStoreError,
    LogStoreRateLimitError,
    LogStoreUnavailableError,
)
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
                Continue with the same filters and the previous page's `until`.

        Returns:
            A page of log entries, oldest first.

        Raises:
            ValueError: If the logs model does not belong to this log store,
                or the pagination parameters are invalid.
            LogStoreError: If Datadog does not answer with a usable result.
        """  # noqa: DOC503
        if logs_model.log_store_id != self.id:
            raise ValueError(
                "logs_model.log_store_id does not match the id of the log "
                "store. These entries were collected by another log store, "
                "which is the one that can read them back."
            )

        if before is not None and after is not None:
            raise ValueError("Pass only one of `before` and `after`.")
        if start not in (None, "oldest", "newest"):
            raise ValueError("`start` must be `oldest` or `newest`.")

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
        page_cursor = before if before is not None else after
        if page_cursor is not None and filter_.until is None:
            raise ValueError(
                "Pass the previous page's `until` with a continuation cursor."
            )
        limit = min(self.resolve_limit(limit), DATADOG_MAX_PAGE_SIZE)
        since = filter_.since or to_utc_timezone(logs_model.created)
        until = filter_.until or utc_now(tz_aware=True)
        if since > until:
            raise ValueError("`since` must be earlier than `until`.")
        sort = "-timestamp" if descending else "timestamp"

        body: Dict[str, Any] = {
            "filter": {
                "query": self._build_query(logs_model, filter_),
                "from": since.isoformat(),
                "to": until.isoformat(),
            },
            "page": {"limit": limit},
            "sort": sort,
        }
        context = json.dumps(
            [str(self.id), str(logs_model.id), body["filter"], sort],
            sort_keys=True,
        )
        signing_key = self.config.application_key.get_secret_value()
        if page_cursor is not None:
            body["page"]["cursor"] = self.decode_cursor(
                page_cursor, signing_key=signing_key, context=context
            )

        events, native_cursor = self._search(body)
        entries = [
            entry
            for entry in (self._parse_log_entry(event) for event in events)
            if entry is not None
        ]
        if descending:
            entries.reverse()

        encoded = (
            self.encode_cursor(
                native_cursor, signing_key=signing_key, context=context
            )
            if native_cursor
            else None
        )
        return LogsEntriesResponse(
            items=entries,
            until=until,
            before=encoded if descending else None,
            after=encoded if not descending else None,
        )

    def _search(
        self, body: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Execute one Datadog search and read its native continuation token.

        Args:
            body: The Datadog search request.

        Returns:
            The events and the native token, if another request is possible.

        Raises:
            LogStoreUnavailableError: If Datadog cannot be reached or fails.
            LogStoreRateLimitError: If Datadog rate limits the search.
            LogStoreError: If Datadog rejects the search or returns invalid data.
        """
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        try:
            response = requests.post(
                f"https://api.{self.config.site}/api/v2/logs/events/search",
                headers=headers,
                json=body,
                timeout=30,
            )
        except requests.RequestException as e:
            logger.exception("Datadog log search failed")
            raise LogStoreUnavailableError(
                "Could not reach Datadog to read these logs."
            ) from e

        if response.status_code != 200:
            logger.error(
                "Datadog rejected a log search with %s: %s",
                response.status_code,
                response.text[:500],
            )
            if response.status_code == 429:
                retry_after = response.headers.get(
                    "Retry-After",
                    response.headers.get("X-RateLimit-Reset", ""),
                )
                raise LogStoreRateLimitError(
                    "Datadog rate limited the log search. Try again later.",
                    retry_after=int(retry_after)
                    if retry_after.isdecimal()
                    else None,
                )
            if response.status_code >= 500:
                raise LogStoreUnavailableError(
                    "Datadog is temporarily unavailable. Try again later."
                )
            raise LogStoreError(
                f"Datadog rejected the log search with status "
                f"{response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as e:
            raise LogStoreError(
                "Datadog returned a response that could not be read as a log "
                "search result."
            ) from e

        if not isinstance(payload, dict) or "data" not in payload:
            raise LogStoreError(
                "Datadog returned an invalid log search result."
            )
        events = payload["data"]
        # Datadog may issue a token even on the empty terminal page.
        if events is None or events == []:
            return [], None
        if not isinstance(events, list) or not all(
            isinstance(event, dict) for event in events
        ):
            raise LogStoreError(
                "Datadog returned an invalid log search result."
            )
        meta = payload.get("meta", {})
        if not isinstance(meta, dict) or not isinstance(
            meta.get("page", {}), dict
        ):
            raise LogStoreError(
                "Datadog returned invalid log pagination metadata."
            )
        native_cursor = meta.get("page", {}).get("after")
        if native_cursor is not None and (
            not isinstance(native_cursor, str) or not native_cursor.strip()
        ):
            raise LogStoreError(
                "Datadog returned an invalid continuation token."
            )
        return events, native_cursor

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
        service = self.config.service_name.replace("\\", "\\\\").replace(
            '"', '\\"'
        )
        query = [
            f'service:"{service}"',
            f"@zenml.log.id:{logs_model.id}",
        ]

        if filter_.search:
            # Quoting keeps multiword searches together. Wildcards only work
            # outside quotes, and Datadog's index controls punctuation matching.
            if any(character.isspace() for character in filter_.search):
                escaped = filter_.search.replace("\\", "\\\\").replace(
                    '"', '\\"'
                )
                query.append(f'message:"{escaped}"')
            else:
                escaped = re.sub(
                    r'([+\-=!&|><(){}\[\]^"~*?:\\/#@])',
                    r"\\\1",
                    filter_.search,
                )
                query.append(f"message:*{escaped}*")

        if filter_.level and filter_.level.value > LoggingLevels.DEBUG.value:
            statuses = [
                status
                for level, group in _STATUSES_BY_LEVEL
                for status in group
                if level >= filter_.level.value
            ]
            query.append(f"status:({' OR '.join(statuses)})")

        return " AND ".join(query)

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
                timestamp = to_utc_timezone(
                    iso8601_to_utc_naive(timestamp_raw)
                )
            else:
                logger.warning(
                    "Datadog log entry is missing a valid timestamp."
                )
                return None

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
