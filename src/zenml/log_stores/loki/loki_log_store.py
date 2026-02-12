# Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Loki log store implementation."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Dict, List, NamedTuple, Optional, Tuple, cast

import requests

from zenml.log_stores.artifact.artifact_log_store import parse_log_entry
from zenml.log_stores.loki.loki_flavor import LokiLogStoreConfig
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import LogsResponse
from zenml.models.v2.misc.log_models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
)

logger = get_logger(__name__)


class CursorToken(NamedTuple):
    """Cursor token payload for Loki pagination."""

    ts_ns: int


def _encode_cursor(*, pos: CursorToken) -> str:
    """Encode a cursor token into a base64 URL-safe string.

    Args:
        pos: The cursor token.

    Returns:
        The base64 URL-safe string.
    """
    payload = {"ts_ns": int(pos.ts_ns)}
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("ascii")


def _decode_cursor(*, token: str) -> CursorToken:
    """Decode a base64 URL-safe string into a cursor token.

    Args:
        token: The base64 URL-safe string.

    Returns:
        The cursor token.
    """
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    decoded = json.loads(raw.decode("utf-8"))

    ts_ns = int(decoded["ts_ns"])
    if ts_ns < 0:
        raise ValueError("Invalid cursor position.")

    return CursorToken(ts_ns=ts_ns)


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


class LokiLogStore(OtelLogStore):
    """Log store that exports logs via OTLP and fetches from Loki."""

    @property
    def config(self) -> LokiLogStoreConfig:
        """Return the Loki log store configuration.

        Returns:
            The Loki log store configuration.
        """
        return cast(LokiLogStoreConfig, self._config)

    def _query_range(
        self,
        *,
        query: str,
        start_ns: int,
        end_ns: int,
        limit: int,
        direction: str,
    ) -> List[Tuple[int, str]]:
        """Query the Loki API to fetch log entries in a range of timestamps.

        Args:
            query: The LogQL query to execute.
            start_ns: The start timestamp in nanoseconds.
            end_ns: The end timestamp in nanoseconds.
            limit: The maximum number of log entries to return.
            direction: The direction of the query.
        """
        url = (
            self.config.query_base_url.rstrip("/") + "/loki/api/v1/query_range"
        )
        headers: Dict[str, str] = {}
        if self.config.headers:
            headers.update(self.config.headers)

        params = {
            "query": query,
            "start": str(int(start_ns)),
            "end": str(int(end_ns)),
            "limit": str(int(limit)),
            "direction": direction,
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Loki: {resp.status_code} - {resp.text[:200]}"
            )
        payload = resp.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Failed to fetch logs from Loki: {payload!r}")

        data = payload.get("data") or {}
        results = data.get("result") or []

        lines: List[Tuple[int, str]] = []
        for result in results:
            values = cast(List[List[str]], result.get("values") or [])
            for ts_raw, line in values:
                ts_ns = int(ts_raw)
                lines.append((ts_ns, line))
        return lines

    def _build_logql_query(
        self, *, logs_model: LogsResponse, filter_: Optional[LogsEntriesFilter]
    ) -> str:
        """Build a LogQL query to fetch log entries from Loki.

        Args:
            logs_model: The logs model containing metadata about the logs.
            filter_: Filters that must be applied during retrieval.

        Returns:
            A LogQL query string.
        """
        # OTLP -> Loki label key normalization replaces '.' with '_' for label names
        # (e.g., 'zenml.log.id' becomes 'zenml_log_id').
        #
        # `zenml_log_id` might be stored as structured metadata instead of an index
        # label depending on Loki OTLP mapping. Filtering it in the pipeline works
        # for both setups while still using a selective stream selector.
        selector = '{service_name="zenml"}'
        log_id = str(logs_model.id).replace('"', '\\"')
        pipeline_parts: List[str] = [f'| zenml_log_id="{log_id}"']

        if not filter_:
            return f"{selector} " + " ".join(pipeline_parts)

        if filter_.search:
            needle = filter_.search.replace('"', '\\"')
            pipeline_parts.append(f'|= "{needle}"')

        if filter_.level is not None:
            # Filter at query-time based on JSON payloads. This is intentionally
            # strict: if a line isn't JSON (or doesn't contain "level"), Loki will
            # drop it when the level filter is used.
            pipeline_parts.append("| json")
            pipeline_parts.append(f'| level="{filter_.level.name}"')

        return f"{selector} " + " ".join(pipeline_parts)

    def fetch(
        self,
        logs_model: LogsResponse,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[LogEntry]:
        """Fetch log entries from Loki (non-paginated helper)."""
        if limit <= 0:
            return []

        start = _to_unix_ns(start_time or logs_model.created)
        end = _to_unix_ns(end_time or datetime.now(timezone.utc))
        query = self._build_logql_query(logs_model=logs_model, filter_=None)

        raw_lines = self._query_range(
            query=query,
            start_ns=start,
            end_ns=end,
            limit=min(limit, 5000),
            direction="forward",
        )

        items: List[LogEntry] = []
        raw_lines.sort(key=lambda x: x[0])
        for ts_ns, line in raw_lines:
            entry = parse_log_entry(line)
            if entry is None:
                continue
            entry.timestamp = datetime.fromtimestamp(
                ts_ns / 1_000_000_000, tz=timezone.utc
            )
            items.append(entry)
            if len(items) >= limit:
                break
        return items

    def fetch_entries(
        self,
        logs_model: LogsResponse,
        limit: int,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: LogsEntriesFilter = None,
    ) -> LogsEntriesResponse:
        """Fetch log entries from Loki with cursor-based pagination.

        Args:
            logs_model: The logs model containing metadata about the logs.
            limit: Maximum number of log entries to return.
            before: Cursor token pointing to older entries.
            after: Cursor token pointing to newer entries.
            filter_: Filters that must be applied during retrieval.

        Returns:
            A response containing log entries and pagination tokens.

        Raises:
            ValueError: If `limit` is not positive or if both `before`
                and `after` are set.
        """
        if limit <= 0:
            raise ValueError("`limit` must be positive.")

        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        query = self._build_logql_query(logs_model=logs_model, filter_=filter_)

        since_ns = logs_model.created
        until_ns = datetime.now(timezone.utc)

        if filter_:
            if filter_.since:
                since_ns = filter_.since
            if filter_.until:
                until_ns = filter_.until

        since_ns = _to_unix_ns(since_ns)
        until_ns = _to_unix_ns(until_ns)

        if after is not None:
            watermark = _decode_cursor(token=after)
            start_ns = max(since_ns, watermark.ts_ns + 1)

            if start_ns > until_ns:
                return LogsEntriesResponse(items=[], before=None, after=after)

            raw_lines = self._query_range(
                query=query,
                start_ns=start_ns,
                end_ns=until_ns,
                limit=min(limit, 5000),
                direction="forward",
            )
            raw_lines.sort(key=lambda x: x[0], reverse=True)

            items: List[LogEntry] = []
            newest_ts: Optional[int] = None
            oldest_ts: Optional[int] = None
            for ts_ns, line in raw_lines:
                entry = parse_log_entry(line)
                if entry is None:
                    continue
                entry.timestamp = datetime.fromtimestamp(
                    ts_ns / 1_000_000_000, tz=timezone.utc
                )
                items.append(entry)
                if newest_ts is None:
                    newest_ts = ts_ns
                oldest_ts = ts_ns
                if len(items) >= limit:
                    break

            if not items or newest_ts is None or oldest_ts is None:
                return LogsEntriesResponse(items=[], before=None, after=after)

            before_token = (
                _encode_cursor(pos=CursorToken(ts_ns=oldest_ts))
                if oldest_ts > since_ns
                else None
            )
            return LogsEntriesResponse(
                items=items,
                before=before_token,
                after=_encode_cursor(pos=CursorToken(ts_ns=newest_ts)),
            )

        cursor_pos = (
            _decode_cursor(token=before) if before is not None else None
        )

        end_ns = (
            min(until_ns, cursor_pos.ts_ns - 1)
            if cursor_pos is not None
            else until_ns
        )
        if end_ns < since_ns:
            return LogsEntriesResponse(items=[], before=None, after=None)

        raw_lines = self._query_range(
            query=query,
            start_ns=since_ns,
            end_ns=end_ns,
            limit=min(limit, 5000),
            direction="backward",
        )
        raw_lines.sort(key=lambda x: x[0], reverse=True)

        page_items: List[LogEntry] = []
        newest_ts: Optional[int] = None
        oldest_ts: Optional[int] = None
        for ts_ns, line in raw_lines:
            entry = parse_log_entry(line)
            if entry is None:
                continue
            entry.timestamp = datetime.fromtimestamp(
                ts_ns / 1_000_000_000, tz=timezone.utc
            )
            page_items.append(entry)
            if newest_ts is None:
                newest_ts = ts_ns
            oldest_ts = ts_ns
            if len(page_items) >= limit:
                break

        if not page_items or newest_ts is None or oldest_ts is None:
            return LogsEntriesResponse(items=[], before=None, after=None)

        before_token = (
            _encode_cursor(pos=CursorToken(ts_ns=oldest_ts))
            if oldest_ts > since_ns
            else None
        )
        after_token = _encode_cursor(pos=CursorToken(ts_ns=newest_ts))
        return LogsEntriesResponse(
            items=page_items, before=before_token, after=after_token
        )
