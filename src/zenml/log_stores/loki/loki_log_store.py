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
from typing import Any, Dict, List, Optional, Tuple, cast

import requests

from zenml.enums import LoggingLevels
from zenml.log_stores.loki.loki_flavor import LokiLogStoreConfig
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


class LokiLogStore(OtelLogStore):
    """Log store that exports logs via OTLP and fetches from Loki."""

    @property
    def config(self) -> LokiLogStoreConfig:
        """Return the Loki log store configuration.

        Returns:
            The Loki log store configuration.
        """
        return cast(LokiLogStoreConfig, self._config)

    def _get_headers(self) -> Dict[str, str]:
        """Construct request headers for Loki ingest and query requests.

        Returns:
            The request headers.
        """
        headers: Dict[str, str] = self.config.headers or {}

        if (
            self.config.username is not None
            and self.config.password is not None
        ):
            credentials = (
                f"{self.config.username.get_secret_value()}:"
                f"{self.config.password.get_secret_value()}"
            ).encode("utf-8")
            token = base64.b64encode(credentials).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        elif self.config.api_key is not None:
            headers["Authorization"] = (
                f"Bearer {self.config.api_key.get_secret_value()}"
            )

        return headers

    def fetch(
        self,
        logs_model: LogsResponse,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
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
        if limit is None:
            limit = self.config.default_query_size
        else:
            if limit <= 0:
                raise ValueError("`limit` must be positive.")

        if before is not None and after is not None:
            raise ValueError("Only one of `before` or `after` can be set.")

        if self.config.query_range_url is None:
            raise ValueError(
                "The query_range_url is not set in the configuration. "
                "Fetching is impossible."
            )

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

        if since_ns > until_ns:
            return LogsEntriesResponse(items=[], before=None, after=after)

        raw_lines = self.query_range(
            query=query,
            start_ns=since_ns,
            end_ns=until_ns,
            limit=limit,
            direction="forward" if after else "backward",
        )
        if not raw_lines:
            return LogsEntriesResponse(
                items=[],
                before=None,
                after=after if after is not None else None,
            )
        entries = self.translate(raw_lines)

        before_token = self.encode_cursor(entries[0][0])
        after_token = self.encode_cursor(entries[-1][0])

        entries.sort(key=lambda x: x[0])

        return LogsEntriesResponse(
            items=[e[1] for e in entries],
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

    @staticmethod
    def translate(
        raw_lines: List[Dict[str, Any]],
    ) -> List[Tuple[int, LogEntry]]:
        """Translate raw loki data to ZenML entries.

        Each entry in the raw loki data has the following format:
            "stream" -> dict that contains metadata about the stream
            "values" -> list of lists of strings, first one is the timestamp,
                second one is the message.

        Args:
            raw_lines: The raw loki data.

        Returns:
            The translated ZenML entry.
        """
        entries = []
        for line in raw_lines:
            values = line["values"][0]
            stream = line["stream"]

            message = str(values[1])

            ts_ns = int(line.get("ts_ns", values[0]))
            timestamp = _from_unix_ns(ts_ns)

            severity_raw = stream.get("severity_text", "info").upper()
            severity = str(severity_raw or "info").upper()
            log_severity = (
                LoggingLevels[severity]
                if severity in LoggingLevels.__members__
                else LoggingLevels.INFO
            )
            entries.append(
                (
                    ts_ns,
                    LogEntry(
                        message=message,
                        level=log_severity,
                        timestamp=timestamp,
                    ),
                )
            )

        return entries

    def build_query(
        self, *, logs_model: LogsResponse, filter_: Optional[LogsEntriesFilter]
    ) -> str:
        """Build a LogQL query to fetch log entries from Loki.

        Important: Loki normalization replaces '.' with '_' for
        label/field names (e.g., 'zenml.log.id' becomes 'zenml_log_id').

        Args:
            logs_model: The logs model containing metadata about the logs.
            filter_: Filters that must be applied during retrieval.

        Returns:
            A LogQL query string.
        """
        selector = f'{{service_name="{self.config.service_name}"}}'

        params: List[str] = [f'| zenml_log_id="{logs_model.id}"']

        if filter_ and filter_.search:
            search = filter_.search.replace('"', '\\"')
            params.append(f'|= "{search}"')

        if filter_ and filter_.level is not None:
            threshold = severity_number_threshold(filter_.level)
            params.append(f"| severity_number >= {threshold}")

        return f"{selector} " + " ".join(params)

    def query_range(
        self,
        query: str,
        start_ns: int,
        end_ns: int,
        limit: int,
        direction: str,
    ) -> List[Dict[str, Any]]:
        """Query the Loki API to fetch log entries in a range of timestamps.

        Args:
            query: The LogQL query to execute.
            start_ns: The start timestamp in nanoseconds.
            end_ns: The end timestamp in nanoseconds.
            limit: The maximum number of log entries to return.
            direction: The direction of the query.

        Returns:
            The log entries.

        Raises:
            RuntimeError: If the request fails.
            ValueError: The configuration does not include a query range URL.
        """
        if self.config.query_range_url is None:
            raise ValueError(
                "The configuration does not include a query range url."
            )

        headers = self._get_headers()

        params = {
            "query": query,
            "start": str(int(start_ns)),
            "end": str(int(end_ns)),
            "limit": str(int(limit)),
            "direction": direction,
        }
        resp = requests.get(
            url=self.config.query_range_url,
            headers=headers,
            params=params,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch logs from Loki: {resp.status_code} - {resp.text[:200]}"
            )

        payload = resp.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Failed to fetch logs from Loki: {payload!r}")

        data = payload.get("data") or {}
        results = data.get("result") or []
        return results
