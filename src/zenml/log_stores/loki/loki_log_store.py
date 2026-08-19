#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Grafana Loki log store implementation."""

import base64
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict, List, Optional, Tuple, cast

import requests

from zenml.log_stores.loki.loki_flavor import (
    LOKI_MAX_PAGE_SIZE,
    LOKI_QUERY_RANGE_PATH,
    LokiLogStoreConfig,
)
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsResponse,
)
from zenml.utils.time_utils import (
    from_unix_nanos,
    to_unix_nanos,
    to_utc_timezone,
    utc_now,
)

logger = get_logger(__name__)

QUERY_TIMEOUT = 30

# Number of entry keys carried in a watermark cursor. Loki timestamps have
# nanosecond resolution, so entries hardly ever share one and this list stays
# tiny in practice. It is capped so that a pathological stream cannot grow the
# cursor without bound.
BOUNDARY_KEY_LIMIT = 50

# Loki normalizes attribute names by replacing dots with underscores, so the
# `zenml.log.id` attribute the exporter attaches is queried under this name.
LOKI_LOG_ID_FIELD = "zenml_log_id"


class LokiLogStore(OtelLogStore):
    """Log store that ships logs to Loki over OTLP and reads them with LogQL.

    Loki has ingested OTLP natively since 3.0, so the write path is the
    inherited one; only the query side is specific to Loki.
    """

    _loki_exporter: Optional[OTLPLogExporter] = None

    @property
    def config(self) -> LokiLogStoreConfig:
        """Returns the configuration of the Loki log store.

        Returns:
            The configuration.
        """
        return cast(LokiLogStoreConfig, self._config)

    def get_exporter(self) -> OTLPLogExporter:
        """Get the log exporter that pushes to Loki's OTLP endpoint.

        Returns:
            An OTLP exporter carrying the Loki credentials.
        """
        if not self._loki_exporter:
            self._loki_exporter = OTLPLogExporter(
                endpoint=self.config.endpoint,
                headers=self._get_headers(),
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )
        return self._loki_exporter

    def _get_headers(self) -> Dict[str, str]:
        """Build the headers that authenticate a request to Loki.

        Credentials are resolved here rather than folded into the configured
        headers, so that they stay in the config fields ZenML knows to treat as
        secrets.

        Returns:
            The headers for both ingestion and query requests.
        """
        headers: Dict[str, str] = dict(self.config.headers or {})

        if (
            self.config.username is not None
            and self.config.password is not None
        ):
            credentials = (
                f"{self.config.username}:"
                f"{self.config.password.get_secret_value()}"
            ).encode("utf-8")
            token = base64.b64encode(credentials).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        elif self.config.api_key is not None:
            headers["Authorization"] = (
                f"Bearer {self.config.api_key.get_secret_value()}"
            )

        if self.config.tenant_id:
            headers["X-Scope-OrgID"] = self.config.tenant_id

        return headers

    def fetch(
        self,
        logs_model: "LogsResponse",
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Fetch a page of log entries from Loki.

        Every call issues exactly one range query. Loki has no continuation
        token, so a page is bounded by a timestamp taken from the entry at the
        edge of the previous page. That boundary is inclusive on the side the
        scan resumes from, so the entries sharing it come back a second time and
        are dropped by their keys, which the cursor carries.

        Filters are pushed down into LogQL. `search` therefore follows Loki's
        line filter, which matches a substring anywhere in the message.

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
        """
        if logs_model.log_store_id != self.id:
            raise ValueError(
                "logs_model.log_store_id does not match the id of the log "
                "store. These entries were collected by another log store, "
                "which is the one that can read them back."
            )

        limit = min(self.resolve_limit(limit), LOKI_MAX_PAGE_SIZE)
        filter_ = filter_ or LogsEntriesFilter()

        # Scanning forward in time is only useful when paging towards newer
        # entries; a first page and a step back through history both want the
        # newest matching entries first.
        descending = after is None
        token = before or after
        cursor = self.decode_cursor(token) if token else {}

        start_ns = to_unix_nanos(
            filter_.since or to_utc_timezone(logs_model.created)
        )
        end_ns = to_unix_nanos(filter_.until or utc_now(tz_aware=True))
        if watermark := cursor.get("timestamp"):
            # `start` is inclusive and `end` is exclusive, so resuming at a
            # watermark means nudging the exclusive side past it to keep the
            # boundary entries in range for deduplication.
            if descending:
                end_ns = min(end_ns, int(watermark) + 1)
            else:
                start_ns = max(start_ns, int(watermark))

        seen = set(cursor.get("keys", []))
        entries: List[Tuple[int, str, LogEntry]] = []
        if start_ns < end_ns:
            entries = [
                entry
                for entry in self._query_range(
                    query=self._build_query(logs_model, filter_),
                    start_ns=start_ns,
                    end_ns=end_ns,
                    limit=limit,
                    descending=descending,
                )
                if entry[1] not in seen
            ]
            entries.sort(key=lambda entry: entry[0])

        # An empty page has no entry to anchor a cursor to, so paging stays
        # where it was: the caller keeps the cursor it arrived with. A first
        # page that is empty because the pipeline has not logged anything yet
        # gets a cursor at the start of the window instead, so that a tail can
        # pick the stream up as it fills.
        newer_fallback = after or (
            None if before else self.encode_cursor(timestamp=start_ns)
        )

        return LogsEntriesResponse(
            items=[entry[2] for entry in entries],
            before=self._get_boundary_cursor(entries, oldest=True)
            if entries
            else None,
            after=self._get_boundary_cursor(entries, oldest=False)
            if entries
            else newer_fallback,
        )

    def _get_boundary_cursor(
        self, entries: List[Tuple[int, str, LogEntry]], oldest: bool
    ) -> str:
        """Build a cursor that resumes a scan at one edge of a page.

        Args:
            entries: The entries of the current page, oldest first.
            oldest: Whether to anchor on the oldest rather than the newest
                entry.

        Returns:
            The cursor.
        """
        timestamp = entries[0][0] if oldest else entries[-1][0]
        return self.encode_cursor(
            timestamp=timestamp,
            keys=[
                key
                for entry_timestamp, key, _ in entries
                if entry_timestamp == timestamp
            ][:BOUNDARY_KEY_LIMIT],
        )

    def _build_query(
        self, logs_model: "LogsResponse", filter_: LogsEntriesFilter
    ) -> str:
        """Build the LogQL query for a log stream.

        Args:
            logs_model: The logs model to fetch the entries of.
            filter_: The filters to express in the query.

        Returns:
            The query.
        """
        # Only resource attributes become index labels, so the stream is
        # selected by service name and narrowed to one log stream by a
        # structured metadata filter.
        query = [
            f'{{service_name="{self.config.service_name}"}}',
            f'| {LOKI_LOG_ID_FIELD}="{logs_model.id}"',
        ]

        if filter_.search:
            escaped = filter_.search.replace("\\", "\\\\").replace('"', '\\"')
            query.append(f'|= "{escaped}"')

        if filter_.level and (
            threshold := self.get_severity_number_threshold(filter_.level)
        ):
            query.append(f"| severity_number >= {threshold}")

        return " ".join(query)

    def _query_range(
        self,
        query: str,
        start_ns: int,
        end_ns: int,
        limit: int,
        descending: bool,
    ) -> List[Tuple[int, str, LogEntry]]:
        """Run a range query and parse every entry of every stream it returns.

        Args:
            query: The LogQL query to run.
            start_ns: Start of the time window, in nanoseconds, inclusive.
            end_ns: End of the time window, in nanoseconds, exclusive.
            limit: Maximum number of entries Loki may return.
            descending: Whether to scan towards older entries.

        Returns:
            Tuples of nanosecond timestamp, deduplication key and entry, in the
            order Loki returned them.

        Raises:
            RuntimeError: If Loki rejects or fails the query.
        """
        response = requests.get(
            f"{self.config.query_url}{LOKI_QUERY_RANGE_PATH}",
            headers=self._get_headers(),
            params={
                "query": query,
                "start": str(start_ns),
                "end": str(end_ns),
                "limit": str(limit),
                "direction": "backward" if descending else "forward",
            },
            timeout=QUERY_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Loki: {response.status_code} - "
                f"{response.text[:200]}"
            )

        payload = response.json()
        # Loki reports a failed query in the body of an otherwise fine
        # response, so the status code alone does not prove there are entries.
        if payload.get("status") != "success":
            raise RuntimeError(f"Loki failed to run the query: {payload}")

        # A response stream is one combination of labels and structured
        # metadata, not one log stream, and OTLP ingestion puts enough per-entry
        # metadata in there to give nearly every entry a stream of its own. A
        # page is therefore spread over many of them.
        entries = []
        for stream in payload.get("data", {}).get("result", []):
            labels = stream.get("stream", {})
            for value in stream.get("values", []):
                if entry := self._parse_entry(value, labels):
                    entries.append(entry)

        return entries

    def _parse_entry(
        self, value: List[Any], labels: Dict[str, str]
    ) -> Optional[Tuple[int, str, LogEntry]]:
        """Parse one entry of a Loki stream.

        Args:
            value: A stream value of a timestamp, a log line and, on the
                versions that report it there, a flat mapping of the entry's
                structured metadata.
            labels: The labels of the response stream, which is where Loki
                reports structured metadata alongside the index labels.

        Returns:
            The nanosecond timestamp, the deduplication key and the entry, or
            None if the entry could not be parsed.
        """
        try:
            timestamp_ns = int(value[0])
            message = str(value[1])
            metadata = value[2] if len(value) > 2 else {}

            # Severity is per-entry structured metadata under OTLP ingestion,
            # which reaches a query either merged into the labels of a response
            # stream or attached to the entry, depending on the version.
            severity_number = metadata.get("severity_number") or labels.get(
                "severity_number"
            )

            return (
                timestamp_ns,
                _get_entry_key(timestamp_ns, message),
                LogEntry(
                    message=message,
                    level=self.get_level_for_severity_number(
                        int(severity_number) if severity_number else None
                    ),
                    timestamp=from_unix_nanos(timestamp_ns),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None

    def cleanup(self) -> None:
        """Cleanup the Loki log store."""
        if self._loki_exporter:
            self._loki_exporter.shutdown()
            self._loki_exporter = None


def _get_entry_key(timestamp_ns: int, message: str) -> str:
    """Build a key that identifies an entry at a given timestamp.

    Loki has no entry IDs, so resuming a scan at a timestamp needs another way
    to recognize the entries already returned at it. Hashing the line keeps the
    key short enough to carry several of them in a cursor.

    Args:
        timestamp_ns: The nanosecond timestamp of the entry.
        message: The log line of the entry.

    Returns:
        The key.
    """
    digest = blake2b(
        f"{timestamp_ns}:{message}".encode("utf-8"), digest_size=8
    )
    return digest.hexdigest()
