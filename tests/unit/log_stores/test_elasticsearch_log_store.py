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
"""Tests for paging through the Elasticsearch search API."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from zenml.enums import LoggingLevels, StackComponentType
from zenml.log_stores.elasticsearch.elasticsearch_flavor import (
    ElasticsearchLogStoreConfig,
)
from zenml.log_stores.elasticsearch.elasticsearch_log_store import (
    ElasticsearchLogStore,
)
from zenml.models import LogsEntriesFilter
from zenml.utils.time_utils import to_unix_nanos

SECOND = 1_000_000_000

NOON = to_unix_nanos(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))


def at(second: int) -> int:
    """Nanosecond timestamp of a given second after noon."""
    return NOON + second * SECOND


class StubResponse:
    """A canned Elasticsearch search response."""

    def __init__(
        self, payload: Dict[str, Any], status_code: int = 200
    ) -> None:
        """Store the payload to return.

        Args:
            payload: The response body.
            status_code: The response status.
        """
        self._payload = payload
        self.status_code = status_code
        self.text = "error"

    def json(self) -> Dict[str, Any]:
        """Return the response body.

        Returns:
            The response body.
        """
        return self._payload


def make_hit(
    timestamp_ns: int,
    message: str,
    severity_number: Optional[int] = None,
    sequence_number: int = 0,
) -> Dict[str, Any]:
    """Build a search hit, with the sort values the cursors are built from."""
    return {
        "_source": {
            "timestamp_nanos": timestamp_ns,
            "sequence_number": sequence_number,
            "message": message,
            "severity_number": severity_number,
        },
        "sort": [timestamp_ns, sequence_number],
    }


def make_payload(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a search response body."""
    return {"hits": {"hits": hits}}


@pytest.fixture
def log_store() -> ElasticsearchLogStore:
    """An Elasticsearch log store with credentials that are never used."""
    return ElasticsearchLogStore(
        name="elasticsearch",
        id=uuid4(),
        config=ElasticsearchLogStoreConfig(
            url="http://elasticsearch:9200",
            api_key="api-key",
        ),
        flavor="elasticsearch",
        type=StackComponentType.LOG_STORE,
        user=uuid4(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )


@pytest.fixture
def search(mocker):
    """Capture search requests and answer them with canned payloads."""
    requests: List[Dict[str, Any]] = []

    def _install(*payloads: Dict[str, Any]) -> List[Dict[str, Any]]:
        responses = [StubResponse(payload) for payload in payloads]

        def _post(url, headers, json, timeout):
            requests.append({"url": url, "headers": headers, **json})
            return responses[len(requests) - 1]

        mocker.patch(
            "zenml.log_stores.elasticsearch.elasticsearch_log_store.requests.post",
            side_effect=_post,
        )
        return requests

    return _install


def test_first_page_reads_the_oldest_entries(
    log_store, logs_model_factory, search
):
    """When start is omitted, Elasticsearch reads from the oldest end."""
    requests = search(
        make_payload(
            [
                make_hit(at(1), "first"),
                make_hit(at(2), "second"),
                make_hit(at(3), "third"),
            ]
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests[0]["sort"] == [
        {"timestamp_nanos": "asc"},
        {"sequence_number": "asc"},
    ]
    assert requests[0]["size"] == log_store.default_query_size
    assert "search_after" not in requests[0]
    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_a_read_from_the_newest_end_returns_its_page_chronologically(
    log_store, logs_model_factory, search
):
    """The starting end picks where a read begins, not how a page is ordered."""
    requests = search(
        make_payload(
            [
                make_hit(at(3), "third"),
                make_hit(at(2), "second"),
                make_hit(at(1), "first"),
            ]
        )
    )

    page = log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        start="newest",
    )

    assert requests[0]["sort"] == [
        {"timestamp_nanos": "desc"},
        {"sequence_number": "desc"},
    ]
    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_older_page_searches_after_the_oldest_entry_seen(
    log_store, logs_model_factory, search
):
    """A step back through history continues from the edge of the last page."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(
        make_payload([make_hit(at(2), "second")]),
        make_payload([make_hit(at(1), "first")]),
    )

    first = log_store.fetch(logs, start="newest")
    second = log_store.fetch(logs, start="newest", before=first.before)

    assert requests[1]["search_after"] == [at(2), 0]
    assert requests[1]["sort"][0] == {"timestamp_nanos": "desc"}
    assert [entry.message for entry in second.items] == ["first"]


def test_newer_page_searches_after_the_newest_entry_seen(
    log_store, logs_model_factory, search
):
    """Tailing continues forward from the newest entry already seen."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(
        make_payload([make_hit(at(2), "second")]),
        make_payload([make_hit(at(3), "third")]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert requests[1]["search_after"] == [at(2), 0]
    assert requests[1]["sort"][0] == {"timestamp_nanos": "asc"}
    assert [entry.message for entry in second.items] == ["third"]


def test_entries_of_one_nanosecond_are_ordered_by_their_sequence(
    log_store, logs_model_factory, search
):
    """The sequence number is what makes a cursor exact within a nanosecond."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(
        make_payload(
            [
                make_hit(at(2), "first", sequence_number=0),
                make_hit(at(2), "second", sequence_number=1),
            ]
        ),
        make_payload([]),
    )

    first = log_store.fetch(logs)
    log_store.fetch(logs, after=first.after)

    assert [entry.message for entry in first.items] == ["first", "second"]
    assert requests[1]["search_after"] == [at(2), 1]


def test_an_empty_page_reports_no_cursor(
    log_store, logs_model_factory, search
):
    """No hits means there is no sort value to continue from."""
    logs = logs_model_factory(log_store_id=log_store.id)
    search(
        make_payload([make_hit(at(2), "second")]),
        make_payload([]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert second.items == []
    assert second.after is None
    assert second.before is None


def test_an_empty_first_page_reports_no_cursor(
    log_store, logs_model_factory, search
):
    """A stream with nothing in it has no page to continue from."""
    search(make_payload([]))

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert page.items == []
    assert page.after is None
    assert page.before is None


def test_filters_are_pushed_into_the_query(
    log_store, logs_model_factory, search
):
    """Elasticsearch does the filtering, so the query has to express it."""
    requests = search(make_payload([]))

    log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        filter_=LogsEntriesFilter(
            search="failed to connect",
            level=LoggingLevels.WARNING,
            since=datetime(2026, 1, 2, tzinfo=timezone.utc),
            until=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
    )

    clauses = requests[0]["query"]["bool"]["filter"]
    assert {
        "wildcard": {
            "message": {
                "value": "*failed to connect*",
                "case_insensitive": True,
            }
        }
    } in clauses
    assert {"range": {"severity_number": {"gte": 13}}} in clauses
    assert {
        "range": {
            "timestamp_nanos": {
                "gte": to_unix_nanos(
                    datetime(2026, 1, 2, tzinfo=timezone.utc)
                ),
                "lte": to_unix_nanos(
                    datetime(2026, 1, 3, tzinfo=timezone.utc)
                ),
            }
        }
    } in clauses


def test_query_is_scoped_to_the_log_stream(
    log_store, logs_model_factory, search
):
    """Entries of other runs must never leak into a log stream."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(make_payload([]))

    log_store.fetch(logs)

    clauses = requests[0]["query"]["bool"]["filter"]
    assert {"match_phrase": {"zenml.log.id": str(logs.id)}} in clauses


def test_severity_number_is_mapped_to_a_log_level(
    log_store, logs_model_factory, search
):
    """OTEL numbers a severity, Python names it."""
    search(
        make_payload(
            [
                make_hit(at(1), "a"),
                make_hit(at(2), "b", severity_number=17),
                make_hit(at(3), "c", severity_number=21),
            ]
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert [entry.level for entry in page.items] == [
        LoggingLevels.INFO,
        LoggingLevels.ERROR,
        LoggingLevels.CRITICAL,
    ]


def test_credentials_authenticate_the_search(
    log_store, logs_model_factory, search
):
    """One configuration has to authenticate reads as well as writes."""
    requests = search(make_payload([]))

    log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests[0]["headers"]["Authorization"] == "ApiKey api-key"
    assert requests[0]["url"] == (
        "http://elasticsearch:9200/zenml-logs/_search"
    )


def test_logs_of_another_log_store_are_rejected(log_store, logs_model_factory):
    """Searching the wrong cluster would look like an empty run."""
    with pytest.raises(ValueError, match="log_store_id"):
        log_store.fetch(logs_model_factory(log_store_id=uuid4()))


def test_a_rejected_search_is_an_error(log_store, logs_model_factory, mocker):
    """A failed search must not look like a log stream with no entries."""
    mocker.patch(
        "zenml.log_stores.elasticsearch.elasticsearch_log_store.requests.post",
        return_value=StubResponse({}, status_code=401),
    )

    with pytest.raises(RuntimeError, match="401"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
