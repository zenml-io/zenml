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
"""Elasticsearch log store implementation."""

import base64
import binascii
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import requests
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StrictInt,
    StrictStr,
    field_validator,
)

from zenml.exceptions import (
    LogStoreError,
    LogStoreRateLimitError,
    LogStoreUnavailableError,
)
from zenml.log_stores.elasticsearch.elasticsearch_flavor import (
    ELASTICSEARCH_MAX_PAGE_SIZE,
    EVENT_ID_FIELD,
    LOG_ID_FIELD,
    MESSAGE_FIELD,
    SEVERITY_NUMBER_FIELD,
    TIMESTAMP_FIELD,
    ElasticsearchLogStoreConfig,
)
from zenml.log_stores.elasticsearch.elasticsearch_log_exporter import (
    ElasticsearchLogExporter,
)
from zenml.log_stores.otel.otel_log_store import OtelLogStore
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

SEARCH_TIMEOUT = 30


class _ElasticsearchFilters(LogsEntriesFilter):
    """Elasticsearch filters with resolved time bounds."""

    since: datetime = Field(...)
    until: datetime = Field(...)

    model_config = ConfigDict(extra="forbid")


class _ElasticsearchCursor(BaseModel):
    """Native sort values and the parameters of the continued search."""

    version: Literal[1]
    token: Tuple[StrictInt, StrictStr]
    log_store_id: UUID
    logs_id: UUID
    filters: _ElasticsearchFilters
    direction: Literal["oldest", "newest"]
    limit: int = Field(gt=0, le=ELASTICSEARCH_MAX_PAGE_SIZE, strict=True)

    model_config = ConfigDict(extra="forbid")

    @field_validator("token")
    @classmethod
    def validate_token(cls, token: Tuple[int, str]) -> Tuple[int, str]:
        """Validate the Elasticsearch sort values.

        Args:
            token: The timestamp and unique event ID returned by Elasticsearch.

        Returns:
            The unchanged sort values.

        Raises:
            ValueError: If the event ID is empty.
        """
        if not token[1].strip():
            raise ValueError("The continuation event ID must not be empty.")
        return token

    def encode(self) -> str:
        """Encode the cursor for use in a query parameter.

        Returns:
            The URL-safe cursor.
        """
        return base64.urlsafe_b64encode(
            self.model_dump_json().encode("utf-8")
        ).decode("ascii")

    @classmethod
    def decode(cls, cursor: str) -> "_ElasticsearchCursor":
        """Decode and validate a cursor.

        Args:
            cursor: The encoded cursor.

        Returns:
            The validated continuation state.

        Raises:
            ValueError: If the cursor is malformed.
        """
        try:
            payload = base64.b64decode(
                cursor.encode("ascii"), altchars=b"-_", validate=True
            )
            return cls.model_validate_json(payload)
        except (binascii.Error, UnicodeError, ValueError) as e:
            raise ValueError("Invalid pagination cursor.") from e


class ElasticsearchLogStore(OtelLogStore):
    """Log store that writes logs to Elasticsearch and queries them back."""

    _elasticsearch_exporter: Optional[ElasticsearchLogExporter] = None

    @property
    def config(self) -> ElasticsearchLogStoreConfig:
        """Returns the configuration of the Elasticsearch log store.

        Returns:
            The configuration.
        """
        return cast(ElasticsearchLogStoreConfig, self._config)

    @property
    def default_query_size(self) -> int:
        """The default page size for Elasticsearch searches.

        Returns:
            The default number of entries per page.
        """
        return 1000

    def get_exporter(self) -> ElasticsearchLogExporter:
        """Get the log exporter that writes to the bulk API.

        Returns:
            An Elasticsearch exporter carrying the cluster credentials.
        """
        if not self._elasticsearch_exporter:
            self._elasticsearch_exporter = ElasticsearchLogExporter(
                endpoint=self.config.endpoint
                or f"{self.config.url.rstrip('/')}/{self.config.index}/_bulk",
                headers=self._get_headers(),
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )
        return self._elasticsearch_exporter

    def _get_headers(self) -> Dict[str, str]:
        """Build authentication headers for exports and searches.

        Returns:
            The request headers.
        """
        headers: Dict[str, str] = dict(self.config.headers or {})
        api_key: SecretStr | str | None = self.config.api_key
        password: SecretStr | str | None = self.config.password
        if isinstance(api_key, SecretStr):
            api_key = api_key.get_secret_value()
        if isinstance(password, SecretStr):
            password = password.get_secret_value()

        if api_key is not None:
            headers["Authorization"] = f"ApiKey {api_key}"
        elif self.config.username is not None and password is not None:
            credentials = f"{self.config.username}:{password}".encode("utf-8")
            token = base64.b64encode(credentials).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        return headers

    def fetch(
        self,
        logs_model: "LogsResponse",
        start: Optional[str] = None,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Fetch a page of log entries from Elasticsearch.

        Cursors retain the filters, time bounds, direction, and page size.
        Pagination uses the native timestamp and event ID sort values.

        Args:
            logs_model: The logs model containing run and step metadata.
            start: Initial end of the stream. Defaults to `newest`.
            limit: Maximum number of log entries to return.
            before: Cursor towards older entries, from a previous page.
            after: Cursor towards newer entries, from a previous page.
            filter_: Filters for a new read. Explicit continuation filters
                must match the cursor.

        Returns:
            A page of log entries, oldest first.

        Raises:
            ValueError: If the logs model does not belong to this log store,
                or the pagination parameters are invalid.
            LogStoreError: If Elasticsearch returns an error or unusable data.
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

        filter_ = filter_ or LogsEntriesFilter()
        page_cursor = before if before is not None else after
        cursor = None
        direction: Literal["oldest", "newest"]
        if page_cursor is not None:
            cursor = _ElasticsearchCursor.decode(page_cursor)
            direction = "newest" if before is not None else "oldest"
            if (
                cursor.log_store_id != self.id
                or cursor.logs_id != logs_model.id
                or cursor.direction != direction
            ):
                raise ValueError(
                    "Invalid pagination cursor for this log store, stream, "
                    "or direction."
                )
            if start is not None and start != cursor.direction:
                raise ValueError(
                    "`start` conflicts with the pagination cursor."
                )
            if (
                limit is not None
                and min(self.resolve_limit(limit), ELASTICSEARCH_MAX_PAGE_SIZE)
                != cursor.limit
            ):
                raise ValueError(
                    "`limit` conflicts with the pagination cursor."
                )
            saved_filters = cursor.filters.model_dump()
            for name, value in filter_.model_dump(exclude_none=True).items():
                if value != saved_filters[name]:
                    raise ValueError(
                        f"`{name}` conflicts with the pagination cursor."
                    )
            filters = cursor.filters
            limit = self.resolve_limit(cursor.limit)
        else:
            direction = "oldest" if start == "oldest" else "newest"
            limit = min(self.resolve_limit(limit), ELASTICSEARCH_MAX_PAGE_SIZE)
            filters = _ElasticsearchFilters(
                search=filter_.search,
                level=filter_.level,
                since=filter_.since or to_utc_timezone(logs_model.created),
                until=filter_.until or utc_now(tz_aware=True),
            )

        descending = direction == "newest"
        order = "desc" if descending else "asc"
        body: Dict[str, Any] = {
            "size": limit,
            "sort": [
                {TIMESTAMP_FIELD: order},
                {f"{EVENT_ID_FIELD}.keyword": order},
            ],
            "query": self._build_query(logs_model, filters),
            "track_total_hits": False,
        }
        if cursor is not None:
            body["search_after"] = list(cursor.token)

        hits = self._search(body)
        encoded = None
        if hits:
            try:
                encoded = _ElasticsearchCursor(
                    version=1,
                    token=hits[-1]["sort"],
                    log_store_id=self.id,
                    logs_id=logs_model.id,
                    filters=filters,
                    direction=direction,
                    limit=limit,
                ).encode()
            except (KeyError, ValueError) as e:
                raise LogStoreError(
                    "Elasticsearch returned invalid continuation sort values."
                ) from e
        entries = [self._parse_hit(hit) for hit in hits]
        if descending:
            entries.reverse()
        return LogsEntriesResponse(
            items=entries,
            before=encoded if descending else None,
            after=encoded if not descending else None,
        )

    def _search(self, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute one Elasticsearch search.

        Args:
            body: The search request.

        Returns:
            The search hits in provider order.

        Raises:
            LogStoreUnavailableError: If Elasticsearch cannot complete the search.
            LogStoreRateLimitError: If Elasticsearch rate limits the search.
            LogStoreError: If the search fails or returns invalid or partial data.
        """
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        client_cert = self.config.client_certificate_file
        client_key = self.config.client_key_file
        try:
            response = requests.post(
                f"{self.config.url.rstrip('/')}/{self.config.index}/_search",
                headers=headers,
                json=body,
                timeout=SEARCH_TIMEOUT,
                verify=self.config.certificate_file or True,
                cert=(client_cert, client_key)
                if client_cert and client_key
                else client_cert,
                allow_redirects=False,
            )
        except requests.RequestException as e:
            raise LogStoreUnavailableError(
                "Could not reach Elasticsearch to read these logs."
            ) from e

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            raise LogStoreRateLimitError(
                "Elasticsearch rate limited the log search. Try again later.",
                retry_after=int(retry_after)
                if retry_after.isdecimal()
                else None,
            )
        if response.status_code >= 500:
            raise LogStoreUnavailableError(
                "Elasticsearch is temporarily unavailable. Try again later."
            )
        if response.status_code != 200:
            raise LogStoreError(
                f"Elasticsearch rejected the log search with status "
                f"{response.status_code}."
            )
        try:
            payload = response.json()
        except ValueError as e:
            raise LogStoreError(
                "Elasticsearch returned an invalid log search result."
            ) from e

        if not isinstance(payload, dict):
            raise LogStoreError(
                "Elasticsearch returned an invalid log search result."
            )
        if payload.get("timed_out") is True:
            raise LogStoreUnavailableError(
                "Elasticsearch timed out while searching these logs. Try again later."
            )
        shards = payload.get("_shards")
        if (
            payload.get("timed_out") is not False
            or not isinstance(shards, dict)
            or type(shards.get("failed")) is not int
        ):
            raise LogStoreError(
                "Elasticsearch returned invalid search metadata."
            )
        if shards["failed"] != 0 or payload.get("terminated_early"):
            raise LogStoreError(
                "Elasticsearch returned an incomplete log search result."
            )
        hits = payload.get("hits")
        if (
            not isinstance(hits, dict)
            or not isinstance(hits.get("hits"), list)
            or not all(isinstance(hit, dict) for hit in hits["hits"])
        ):
            raise LogStoreError(
                "Elasticsearch returned invalid log search hits."
            )
        return cast(List[Dict[str, Any]], hits["hits"])

    def _build_query(
        self, logs_model: "LogsResponse", filter_: _ElasticsearchFilters
    ) -> Dict[str, Any]:
        """Build the search query for a log stream.

        Args:
            logs_model: The logs model to fetch the entries of.
            filter_: The filters to express in the query.

        Returns:
            The query.
        """
        clauses: List[Dict[str, Any]] = [
            {"term": {f"{LOG_ID_FIELD}.keyword": str(logs_model.id)}},
            {
                "range": {
                    TIMESTAMP_FIELD: {
                        "gte": to_unix_nanos(filter_.since),
                        "lte": to_unix_nanos(filter_.until),
                    }
                }
            },
        ]
        if filter_.level and (
            threshold := self.get_severity_number_threshold(filter_.level)
        ):
            clauses.append(
                {"range": {SEVERITY_NUMBER_FIELD: {"gte": threshold}}}
            )
        if filter_.search:
            clauses.append({"match_phrase": {MESSAGE_FIELD: filter_.search}})
        return {"bool": {"filter": clauses}}

    def _parse_hit(self, hit: Dict[str, Any]) -> LogEntry:
        """Parse a single search hit.

        Args:
            hit: The hit to parse.

        Returns:
            The parsed log entry.

        Raises:
            LogStoreError: If the hit has invalid identifiers or log fields.
        """
        event_id = hit.get("_id")
        index = hit.get("_index")
        if (
            not isinstance(event_id, str)
            or not event_id.strip()
            or not isinstance(index, str)
            or not index.strip()
        ):
            raise LogStoreError(
                "Elasticsearch returned a log without a valid ID."
            )
        document = hit.get("_source")
        if not isinstance(document, dict):
            raise LogStoreError("Elasticsearch returned an invalid log entry.")
        timestamp_ns = document.get(TIMESTAMP_FIELD)
        message = document.get(MESSAGE_FIELD)
        severity = document.get(SEVERITY_NUMBER_FIELD)
        if (
            type(timestamp_ns) is not int
            or not isinstance(message, str)
            or (
                severity is not None
                and (type(severity) is not int or not 0 <= severity <= 24)
            )
        ):
            raise LogStoreError("Elasticsearch returned an invalid log entry.")
        try:
            return LogEntry(
                id=uuid5(
                    NAMESPACE_URL,
                    f"https://www.elastic.co/logs/{index}/{event_id}",
                ),
                message=message,
                level=self.get_level_for_severity_number(severity),
                timestamp=from_unix_nanos(timestamp_ns),
            )
        except (TypeError, ValueError, OverflowError):
            raise LogStoreError(
                "Elasticsearch returned an invalid log entry."
            ) from None

    def cleanup(self) -> None:
        """Clean up the Elasticsearch log store."""
        if self._elasticsearch_exporter:
            self._elasticsearch_exporter.shutdown()
            self._elasticsearch_exporter = None
