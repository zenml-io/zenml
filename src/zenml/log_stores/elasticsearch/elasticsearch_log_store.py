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
import json
from typing import Any, Dict, List, Optional, cast

import requests

from zenml.log_stores.elasticsearch.elasticsearch_flavor import (
    ELASTICSEARCH_MAX_PAGE_SIZE,
    LOG_ID_FIELD,
    MESSAGE_FIELD,
    SEQUENCE_FIELD,
    SEVERITY_NUMBER_FIELD,
    TIMESTAMP_FIELD,
    ElasticsearchLogStoreConfig,
)
from zenml.log_stores.elasticsearch.elasticsearch_log_exporter import (
    ElasticsearchLogExporter,
)
from zenml.log_stores.otel.otel_log_store import OtelLogStore
from zenml.logger import get_logger
from zenml.models import (
    LogEntry,
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsResponse,
)
from zenml.utils.time_utils import from_unix_nanos, to_unix_nanos

logger = get_logger(__name__)

SEARCH_TIMEOUT = 30


class ElasticsearchLogStore(OtelLogStore):
    """Log store that writes logs to Elasticsearch and queries them back.

    Works against OpenSearch too, whose bulk and search APIs agree with the
    Elasticsearch ones on everything this log store uses.
    """

    _elasticsearch_exporter: Optional[ElasticsearchLogExporter] = None

    @property
    def config(self) -> ElasticsearchLogStoreConfig:
        """Returns the configuration of the Elasticsearch log store.

        Returns:
            The configuration.
        """
        return cast(ElasticsearchLogStoreConfig, self._config)

    def get_exporter(self) -> ElasticsearchLogExporter:
        """Get the log exporter that writes to the bulk API.

        Returns:
            An Elasticsearch exporter carrying the cluster credentials.
        """
        if not self._elasticsearch_exporter:
            self._elasticsearch_exporter = ElasticsearchLogExporter(
                endpoint=self.config.endpoint,
                headers=self._get_headers(),
                certificate_file=self.config.certificate_file,
                client_key_file=self.config.client_key_file,
                client_certificate_file=self.config.client_certificate_file,
                compression=self.config.compression,
            )
        return self._elasticsearch_exporter

    def _get_headers(self) -> Dict[str, str]:
        """Build the headers that authenticate a request to the cluster.

        Credentials are resolved here rather than folded into the configured
        headers, so that they stay in the config fields ZenML knows to treat as
        secrets.

        Returns:
            The headers for both ingestion and search requests.
        """
        headers: Dict[str, str] = dict(self.config.headers or {})

        if self.config.api_key is not None:
            headers["Authorization"] = (
                f"ApiKey {self.config.api_key.get_secret_value()}"
            )
        elif (
            self.config.username is not None
            and self.config.password is not None
        ):
            credentials = (
                f"{self.config.username}:"
                f"{self.config.password.get_secret_value()}"
            ).encode("utf-8")
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

        Documents are written with a nanosecond timestamp and a sequence
        number, which together are a total order, so `search_after` on those
        sort values is the cluster's own continuation.

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
            RuntimeError: If the cluster does not answer with a usable result.
        """
        if logs_model.log_store_id != self.id:
            raise ValueError(
                "logs_model.log_store_id does not match the id of the log "
                "store. These entries were collected by another log store, "
                "which is the one that can read them back."
            )

        if before is not None and after is not None:
            raise ValueError("Pass only one of `before` and `after`.")

        if after is not None:
            descending = False
        elif before is not None:
            descending = True
        else:
            descending = start == "newest"

        limit = min(self.resolve_limit(limit), ELASTICSEARCH_MAX_PAGE_SIZE)
        filter_ = filter_ or LogsEntriesFilter()
        token = before or after
        sort_values = json.loads(self.decode_cursor(token)) if token else None

        order = "desc" if descending else "asc"
        body: Dict[str, Any] = {
            "size": limit,
            "sort": [
                {TIMESTAMP_FIELD: order},
                {SEQUENCE_FIELD: order},
            ],
            "query": self._build_query(logs_model, filter_),
            "track_total_hits": False,
        }
        if sort_values is not None:
            body["search_after"] = sort_values

        try:
            response = requests.post(
                f"{self.config.url.rstrip('/')}/{self.config.index}/_search",
                headers=self._get_headers(),
                json=body,
                timeout=SEARCH_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.exception("Elasticsearch log search failed")
            raise RuntimeError(
                "Could not reach Elasticsearch to read these logs."
            ) from e

        if response.status_code != 200:
            logger.error(
                "Elasticsearch rejected a log search with %s: %s",
                response.status_code,
                response.text[:500],
            )
            raise RuntimeError(
                f"Elasticsearch rejected the log search with status "
                f"{response.status_code}."
            )

        try:
            hits = response.json().get("hits", {}).get("hits", [])
        except ValueError as e:
            raise RuntimeError(
                "Elasticsearch returned a response that could not be read "
                "as a log search result."
            ) from e

        if descending:
            hits.reverse()

        entries = [
            entry
            for entry in (self._parse_hit(hit) for hit in hits)
            if entry is not None
        ]

        return LogsEntriesResponse(
            items=entries,
            before=self._get_cursor(hits, oldest=True) if hits else None,
            after=self._get_cursor(hits, oldest=False) if hits else None,
        )

    def _get_cursor(self, hits: List[Dict[str, Any]], oldest: bool) -> str:
        """Build a cursor that resumes a search at one edge of a page.

        Args:
            hits: The hits of the current page, oldest first.
            oldest: Whether to anchor on the oldest rather than the newest hit.

        Returns:
            The cursor.
        """
        hit = hits[0] if oldest else hits[-1]

        return self.encode_cursor(json.dumps(hit["sort"]))

    def _build_query(
        self, logs_model: "LogsResponse", filter_: LogsEntriesFilter
    ) -> Dict[str, Any]:
        """Build the search query for a log stream.

        Args:
            logs_model: The logs model to fetch the entries of.
            filter_: The filters to express in the query.

        Returns:
            The query.
        """
        # Every clause is a filter rather than a `must`, because relevance
        # scoring has no meaning for a log stream that is ordered by time.
        #
        # The log ID is matched as a phrase rather than as a term because a
        # dynamically mapped string is analyzed, and a term query would then
        # never match a UUID that the analyzer split on its hyphens. A phrase
        # matches under both that mapping and an explicit keyword one.
        clauses: List[Dict[str, Any]] = [
            {"match_phrase": {LOG_ID_FIELD: str(logs_model.id)}}
        ]

        window: Dict[str, Any] = {}
        if filter_.since:
            window["gte"] = to_unix_nanos(filter_.since)
        if filter_.until:
            window["lte"] = to_unix_nanos(filter_.until)
        if window:
            clauses.append({"range": {TIMESTAMP_FIELD: window}})

        if filter_.level and (
            threshold := self.get_severity_number_threshold(filter_.level)
        ):
            clauses.append(
                {"range": {SEVERITY_NUMBER_FIELD: {"gte": threshold}}}
            )

        if filter_.search:
            escaped = (
                filter_.search.replace("\\", "\\\\")
                .replace("*", "\\*")
                .replace("?", "\\?")
            )
            clauses.append(
                {
                    "wildcard": {
                        MESSAGE_FIELD: {
                            "value": f"*{escaped}*",
                            "case_insensitive": True,
                        }
                    }
                }
            )

        return {"bool": {"filter": clauses}}

    def _parse_hit(self, hit: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a single hit of an Elasticsearch search response.

        Args:
            hit: The hit to parse.

        Returns:
            A log entry, or None if the hit could not be parsed.
        """
        try:
            document = hit["_source"]

            return LogEntry(
                message=str(document.get(MESSAGE_FIELD, "")),
                level=self.get_level_for_severity_number(
                    document.get(SEVERITY_NUMBER_FIELD)
                ),
                timestamp=from_unix_nanos(int(document[TIMESTAMP_FIELD])),
            )
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None

    def cleanup(self) -> None:
        """Cleanup the Elasticsearch log store."""
        if self._elasticsearch_exporter:
            self._elasticsearch_exporter.shutdown()
            self._elasticsearch_exporter = None
