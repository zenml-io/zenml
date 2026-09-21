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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Grafana Loki log store implementation."""

import base64
import json
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from uuid import NAMESPACE_URL, uuid5

import requests
from pydantic import SecretStr

from zenml.exceptions import (
    LogStoreError,
    LogStoreRateLimitError,
    LogStoreUnavailableError,
)
from zenml.log_stores.loki.loki_flavor import (
    LOKI_MAX_PAGE_SIZE,
    LOKI_QUERY_RANGE_PATH,
    LokiLogStoreConfig,
)
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsResponse,
)
from zenml.utils.time_utils import from_unix_nanos, to_unix_nanos, utc_now

QUERY_TIMEOUT = 30

# Loki normalizes OTLP attribute names, including zenml.log.id.
LOKI_LOG_ID_FIELD = "zenml_log_id"


class LokiLogStore(OtelLogStore):
    """Ship logs through Loki's native OTLP endpoint and query them with LogQL."""

    _loki_exporter: Optional[OTLPLogExporter] = None

    @property
    def config(self) -> LokiLogStoreConfig:
        """Return the Loki configuration.

        Returns:
            The configuration.
        """
        return cast(LokiLogStoreConfig, self._config)

    @property
    def default_query_size(self) -> int:
        """Return the default query size.

        Returns:
            The default number of entries in one batch.
        """
        return 1000

    def get_exporter(self) -> OTLPLogExporter:
        """Get the exporter configured for Loki ingestion.

        Returns:
            The OTLP exporter.
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
        """Build headers for both ingestion and query requests.

        Returns:
            Configured headers, including authentication and tenant scope.
        """
        headers = dict(self.config.headers or {})
        if (
            self.config.username is not None
            and self.config.password is not None
        ):
            password = self.config.password
            password_value = (
                password.get_secret_value()
                if isinstance(password, SecretStr)
                else password
            )
            credentials = f"{self.config.username}:{password_value}".encode()
            token = base64.b64encode(credentials).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        elif self.config.api_key is not None:
            api_key = self.config.api_key
            token = (
                api_key.get_secret_value()
                if isinstance(api_key, SecretStr)
                else api_key
            )
            headers["Authorization"] = f"Bearer {token}"

        if self.config.tenant_id:
            headers["X-Scope-OrgID"] = self.config.tenant_id
        return headers

    def fetch(
        self,
        logs_model: LogsResponse,
        start: Optional[str] = None,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Fetch one filtered batch of log entries from Loki.

        Loki's range API has no native continuation token. Both response
        cursors are therefore absent, even when the batch reaches its limit.

        Args:
            logs_model: The log stream to read.
            start: Initial end of the stream. Defaults to `newest`.
            limit: Maximum entries to return, capped at 5000.
            before: Unsupported continuation cursor.
            after: Unsupported continuation cursor.
            filter_: Filters applied by Loki.

        Returns:
            A batch of entries in chronological order, without cursors.

        Raises:
            ValueError: If the stream belongs to another log store or the
                parameters are unsupported.
            LogStoreError: If Loki returns an invalid or failed response.
            LogStoreRateLimitError: If Loki rate limits the request.
            LogStoreUnavailableError: If Loki is unavailable.
        """  # noqa: DOC503
        if logs_model.log_store_id != self.id:
            raise ValueError(
                "logs_model.log_store_id does not match this log store."
            )
        if before is not None or after is not None:
            raise ValueError("Loki does not support continuation cursors.")
        if start not in (None, "oldest", "newest"):
            raise ValueError("`start` must be `oldest` or `newest`.")

        limit = min(self.resolve_limit(limit), LOKI_MAX_PAGE_SIZE)
        filter_ = filter_ or LogsEntriesFilter()
        start_ns = to_unix_nanos(filter_.since or logs_model.created)
        # ZenML's upper bound is inclusive; Loki's end is exclusive.
        end_ns = to_unix_nanos(filter_.until or utc_now(tz_aware=True)) + 1
        if start_ns >= end_ns:
            return LogsEntriesResponse()

        entries = self._query_range(
            query=self._build_query(logs_model, filter_),
            start_ns=start_ns,
            end_ns=end_ns,
            limit=limit,
            descending=start != "oldest",
        )
        entries.sort(key=lambda entry: (entry[0], entry[1].id))
        return LogsEntriesResponse(items=[entry for _, entry in entries])

    def _build_query(
        self, logs_model: LogsResponse, filter_: LogsEntriesFilter
    ) -> str:
        """Build a scoped LogQL query.

        Args:
            logs_model: The log stream to read.
            filter_: Filters to apply.

        Returns:
            The query with quoted label values and literal search text.
        """
        service = json.dumps(self.config.service_name, ensure_ascii=False)
        query = [
            f"{{service_name={service}}}",
            f'| {LOKI_LOG_ID_FIELD}="{logs_model.id}"',
        ]
        if filter_.search:
            query.append(
                f"|= {json.dumps(filter_.search, ensure_ascii=False)}"
            )
        if filter_.level is not None:
            threshold = self.get_severity_number_threshold(filter_.level)
            if threshold:
                # Numeric conversion failures otherwise survive label filters.
                query.append(
                    f'| severity_number >= {threshold} | __error__=""'
                )
        return " ".join(query)

    def _query_range(
        self,
        query: str,
        start_ns: int,
        end_ns: int,
        limit: int,
        descending: bool,
    ) -> List[Tuple[int, LogEntry]]:
        """Query Loki and parse all returned streams.

        Args:
            query: The LogQL query.
            start_ns: Inclusive start in Unix nanoseconds.
            end_ns: Exclusive end in Unix nanoseconds.
            limit: Maximum number of entries.
            descending: Whether to read newest entries first.

        Returns:
            Nanosecond timestamps and their parsed entries.

        Raises:
            LogStoreError: If Loki rejects the query or returns invalid data.
            LogStoreRateLimitError: If Loki rate limits the request.
            LogStoreUnavailableError: If Loki is unavailable.
        """
        client_cert: Optional[Union[str, Tuple[str, str]]] = (
            (self.config.client_certificate_file, self.config.client_key_file)
            if self.config.client_certificate_file
            and self.config.client_key_file
            else self.config.client_certificate_file
        )
        try:
            response = requests.get(
                f"{self.config.get_query_url()}{LOKI_QUERY_RANGE_PATH}",
                headers=self._get_headers(),
                params={
                    "query": query,
                    "start": str(start_ns),
                    "end": str(end_ns),
                    "limit": str(limit),
                    "direction": "backward" if descending else "forward",
                },
                timeout=QUERY_TIMEOUT,
                verify=self.config.certificate_file or True,
                cert=client_cert,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise LogStoreUnavailableError(
                "Could not reach Loki to read logs."
            ) from None

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            raise LogStoreRateLimitError(
                "Loki rate limited the log query.",
                retry_after=int(retry_after)
                if retry_after.isdecimal()
                else None,
            )
        if response.status_code == 408 or response.status_code >= 500:
            raise LogStoreUnavailableError(
                f"Loki is unavailable (HTTP {response.status_code})."
            )
        if response.status_code != 200:
            raise LogStoreError(
                f"Loki rejected the log query (HTTP {response.status_code})."
            )

        try:
            payload = response.json()
        except ValueError:
            raise LogStoreError(
                "Loki returned an invalid JSON response."
            ) from None
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise LogStoreError("Loki failed to run the log query.")
        data = payload.get("data")
        if (
            not isinstance(data, dict)
            or data.get("resultType") != "streams"
            or not isinstance(data.get("result"), list)
        ):
            raise LogStoreError("Loki returned an invalid log query result.")

        entries = []
        for stream in data["result"]:
            if (
                not isinstance(stream, dict)
                or not isinstance(stream.get("stream"), dict)
                or not isinstance(stream.get("values"), list)
            ):
                raise LogStoreError("Loki returned an invalid log stream.")
            for value in stream["values"]:
                entries.append(self._parse_entry(value, stream["stream"]))
        return entries

    def _parse_entry(
        self, value: Any, labels: Dict[str, str]
    ) -> Tuple[int, LogEntry]:
        """Parse an entry while retaining its exact timestamp for ordering.

        Args:
            value: Timestamp, message, and optional structured metadata.
            labels: Stream labels, including metadata on some Loki versions.

        Returns:
            The nanosecond timestamp and entry with a stable identifier.

        Raises:
            LogStoreError: If the entry cannot be parsed.
        """
        if (
            not isinstance(value, list)
            or len(value) not in (2, 3)
            or not isinstance(value[0], str)
            or not isinstance(value[1], str)
            or (len(value) == 3 and not isinstance(value[2], dict))
        ):
            raise LogStoreError("Loki returned an invalid log entry.")
        metadata = {**labels, **(value[2] if len(value) == 3 else {})}
        if not all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in metadata.items()
        ):
            raise LogStoreError("Loki returned invalid log metadata.")
        try:
            timestamp_ns = int(value[0])
            timestamp = from_unix_nanos(timestamp_ns)
            severity = metadata.get("severity_number")
            level = self.get_level_for_severity_number(
                int(severity) if severity else None
            )
        except (ValueError, TypeError, OverflowError):
            raise LogStoreError(
                "Loki returned an invalid log entry."
            ) from None

        # Loki has no event ID. Identical native entries share an ID, while
        # differences in stream labels, metadata, or nanoseconds remain distinct.
        identity = json.dumps(
            ["loki", timestamp_ns, value[1], metadata],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return timestamp_ns, LogEntry(
            id=uuid5(NAMESPACE_URL, identity),
            message=value[1],
            level=level,
            timestamp=timestamp,
        )

    def cleanup(self) -> None:
        """Shut down the Loki exporter."""
        if self._loki_exporter:
            self._loki_exporter.shutdown()
            self._loki_exporter = None
