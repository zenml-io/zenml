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
"""Tests for paging through the Loki query API."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from zenml.enums import LoggingLevels, StackComponentType
from zenml.log_stores.loki.loki_flavor import LokiLogStoreConfig
from zenml.log_stores.loki.loki_log_store import LokiLogStore
from zenml.models import LogsEntriesFilter
from zenml.utils.time_utils import to_unix_nanos

SECOND = 1_000_000_000

# Entries have to sit inside the window a fetch reads, which starts when the
# log stream was created.
NOON = to_unix_nanos(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))


def at(second: int) -> int:
    """Nanosecond timestamp of a given second after noon."""
    return NOON + second * SECOND


class StubResponse:
    """A canned Loki query response."""

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


def make_entry(
    timestamp_ns: int, message: str, severity_number: Optional[int] = None
) -> List[Any]:
    """Build a Loki stream value, with severity as structured metadata."""
    metadata = (
        {"severity_number": str(severity_number)} if severity_number else {}
    )
    return [str(timestamp_ns), message, metadata]


def make_payload(
    *streams: List[List[Any]], labels: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Build a Loki query response body, one stream per argument."""
    return {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"service_name": "zenml", **(labels or {})},
                    "values": values,
                }
                for values in streams
            ],
        },
    }


@pytest.fixture
def log_store() -> LokiLogStore:
    """A Loki log store with credentials that are never used."""
    return LokiLogStore(
        name="loki",
        id=uuid4(),
        config=LokiLogStoreConfig(
            endpoint="http://loki:3100/otlp/v1/logs",
            username="123456",
            password="token",
            tenant_id="zenml",
        ),
        flavor="loki",
        type=StackComponentType.LOG_STORE,
        user=uuid4(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )


@pytest.fixture
def query(mocker):
    """Capture range queries and answer them with canned payloads."""
    requests: List[Dict[str, Any]] = []

    def _install(*payloads: Dict[str, Any]) -> List[Dict[str, Any]]:
        responses = [StubResponse(payload) for payload in payloads]

        def _get(url, headers, params, timeout):
            requests.append({"url": url, "headers": headers, **params})
            return responses[len(requests) - 1]

        mocker.patch(
            "zenml.log_stores.loki.loki_log_store.requests.get",
            side_effect=_get,
        )
        return requests

    return _install


def test_first_page_reads_the_newest_entries(
    log_store, logs_model_factory, query
):
    """Without a cursor, the newest entries are returned oldest first."""
    requests = query(
        make_payload(
            [
                make_entry(at(3), "third"),
                make_entry(at(2), "second"),
                make_entry(at(1), "first"),
            ]
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests[0]["direction"] == "backward"
    assert requests[0]["limit"] == str(log_store.default_query_size)
    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_a_page_spans_every_stream_it_is_spread_over(
    log_store, logs_model_factory, query
):
    """A page is spread over as many response streams as there are label sets."""
    query(
        make_payload(
            [make_entry(at(3), "third"), make_entry(at(1), "first")],
            [make_entry(at(2), "second")],
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_older_page_ends_at_the_oldest_entry_seen(
    log_store, logs_model_factory, query
):
    """A step back through history resumes at the edge of the last page."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = query(
        make_payload([make_entry(at(2), "second")]),
        make_payload([make_entry(at(1), "first")]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, before=first.before)

    assert requests[1]["direction"] == "backward"
    # `end` is exclusive, so it sits one nanosecond past the boundary entry to
    # keep it in range for deduplication.
    assert requests[1]["end"] == str(at(2) + 1)
    assert [entry.message for entry in second.items] == ["first"]


def test_older_page_drops_entries_already_seen(
    log_store, logs_model_factory, query
):
    """The overlapping boundary entry must not be returned twice."""
    logs = logs_model_factory(log_store_id=log_store.id)
    seen = make_entry(at(2), "second")
    query(
        make_payload([seen]),
        make_payload([seen, make_entry(at(2), "also second")]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, before=first.before)

    assert [entry.message for entry in second.items] == ["also second"]


def test_newer_page_resumes_at_the_newest_entry(
    log_store, logs_model_factory, query
):
    """Tailing scans forward from the newest entry already seen."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = query(
        make_payload([make_entry(at(2), "second")]),
        make_payload([make_entry(at(3), "third")]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert requests[1]["direction"] == "forward"
    # `start` is inclusive, so the boundary entry comes back and is dropped.
    assert requests[1]["start"] == str(at(2))
    assert [entry.message for entry in second.items] == ["third"]


def test_empty_tail_keeps_its_cursor(log_store, logs_model_factory, query):
    """A tail that finds nothing new can still be resumed later."""
    logs = logs_model_factory(log_store_id=log_store.id)
    query(
        make_payload([make_entry(at(2), "second")]),
        make_payload([]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert second.items == []
    assert second.after == first.after


def test_empty_first_page_can_be_tailed_from_the_start(
    log_store, logs_model_factory, query
):
    """A pipeline that has not logged yet still gets a usable tail cursor."""
    logs = logs_model_factory(
        log_store_id=log_store.id,
        created=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
    )
    requests = query(make_payload(), make_payload())

    page = log_store.fetch(logs)
    log_store.fetch(logs, after=page.after)

    assert page.after is not None
    assert requests[1]["start"] == requests[0]["start"]


def test_filters_are_pushed_into_the_query(
    log_store, logs_model_factory, query
):
    """Loki does the filtering, so LogQL has to express it."""
    requests = query(make_payload())

    log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        filter_=LogsEntriesFilter(
            search='say "hi"',
            level=LoggingLevels.WARNING,
            since=datetime(2026, 1, 2, tzinfo=timezone.utc),
            until=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
    )

    assert '|= "say \\"hi\\""' in requests[0]["query"]
    assert "| severity_number >= 13" in requests[0]["query"]
    assert requests[0]["start"] == str(
        int(datetime(2026, 1, 2, tzinfo=timezone.utc).timestamp()) * SECOND
    )
    assert requests[0]["end"] == str(
        int(datetime(2026, 1, 3, tzinfo=timezone.utc).timestamp()) * SECOND
    )


def test_query_is_scoped_to_the_log_stream(
    log_store, logs_model_factory, query
):
    """Entries of other runs must never leak into a log stream."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = query(make_payload())

    log_store.fetch(logs)

    assert '{service_name="zenml"}' in requests[0]["query"]
    assert f'| zenml_log_id="{logs.id}"' in requests[0]["query"]


def test_severity_is_read_from_the_labels_of_a_response_stream(
    log_store, logs_model_factory, query
):
    """Loki reports structured metadata as labels of the stream it returns."""
    query(
        make_payload(
            [make_entry(at(1), "a")], labels={"severity_number": "17"}
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert [entry.level for entry in page.items] == [LoggingLevels.ERROR]


def test_severity_is_read_per_entry_when_attached_to_one(
    log_store, logs_model_factory, query
):
    """Some versions attach structured metadata to the entry instead."""
    query(
        make_payload(
            [
                make_entry(at(3), "c", severity_number=21),
                make_entry(at(2), "b", severity_number=17),
                make_entry(at(1), "a"),
            ]
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert [entry.level for entry in page.items] == [
        LoggingLevels.INFO,
        LoggingLevels.ERROR,
        LoggingLevels.CRITICAL,
    ]


def test_credentials_authenticate_the_query(
    log_store, logs_model_factory, query
):
    """One configuration has to authenticate reads as well as writes."""
    requests = query(make_payload())

    log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests[0]["headers"]["Authorization"].startswith("Basic ")
    assert requests[0]["headers"]["X-Scope-OrgID"] == "zenml"
    assert requests[0]["url"].startswith("http://loki:3100/loki/api/v1/")


def test_configured_headers_are_left_alone():
    """Building request headers must not write back into the configuration."""
    log_store = LokiLogStore(
        name="loki",
        id=uuid4(),
        config=LokiLogStoreConfig(
            endpoint="http://loki:3100/otlp/v1/logs",
            api_key="token",
            headers={"X-Custom": "value"},
        ),
        flavor="loki",
        type=StackComponentType.LOG_STORE,
        user=uuid4(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )

    headers = log_store._get_headers()

    assert headers["Authorization"] == "Bearer token"
    assert headers["X-Custom"] == "value"
    assert log_store.config.headers == {"X-Custom": "value"}


def test_logs_of_another_log_store_are_rejected(log_store, logs_model_factory):
    """Querying the wrong Loki would look like an empty run."""
    with pytest.raises(ValueError, match="log_store_id"):
        log_store.fetch(logs_model_factory(log_store_id=uuid4()))


def test_a_rejected_query_is_an_error(log_store, logs_model_factory, mocker):
    """A failed query must not look like a log stream with no entries."""
    mocker.patch(
        "zenml.log_stores.loki.loki_log_store.requests.get",
        return_value=StubResponse({}, status_code=403),
    )

    with pytest.raises(RuntimeError, match="403"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


def test_a_failed_query_with_a_fine_status_is_an_error(
    log_store, logs_model_factory, mocker
):
    """Loki reports a failed query in the body of a 200 response."""
    mocker.patch(
        "zenml.log_stores.loki.loki_log_store.requests.get",
        return_value=StubResponse({"status": "error", "error": "parse error"}),
    )

    with pytest.raises(RuntimeError, match="parse error"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
