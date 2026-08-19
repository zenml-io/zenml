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
"""Tests for paging through the Datadog Logs API."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from zenml.enums import LoggingLevels, StackComponentType
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.datadog.datadog_log_store import DatadogLogStore
from zenml.models import LogsEntriesFilter


class StubResponse:
    """A canned Datadog search response."""

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


def make_event(
    event_id: str, message: str, timestamp: str, status: str = "info"
) -> Dict[str, Any]:
    """Build a Datadog log event as the search API returns it."""
    return {
        "id": event_id,
        "attributes": {
            "message": message,
            "timestamp": timestamp,
            "status": status,
            "attributes": {},
        },
    }


def make_payload(
    events: List[Dict[str, Any]], next_cursor: Optional[str] = None
) -> Dict[str, Any]:
    """Build a Datadog search response body."""
    payload: Dict[str, Any] = {"data": events}
    if next_cursor:
        payload["meta"] = {"page": {"after": next_cursor}}
    return payload


@pytest.fixture
def log_store() -> DatadogLogStore:
    """A Datadog log store with credentials that are never used."""
    return DatadogLogStore(
        name="datadog",
        id=uuid4(),
        config=DatadogLogStoreConfig(
            api_key="api-key",
            application_key="application-key",
        ),
        flavor="datadog",
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
            requests.append(json)
            return responses[len(requests) - 1]

        mocker.patch(
            "zenml.log_stores.datadog.datadog_log_store.requests.post",
            side_effect=_post,
        )
        return requests

    return _install


def test_first_page_reads_the_newest_entries(
    log_store, logs_model_factory, search
):
    """Without a cursor, the newest entries are returned oldest first."""
    requests = search(
        make_payload(
            [
                make_event("3", "third", "2026-01-01T12:00:03.000Z"),
                make_event("2", "second", "2026-01-01T12:00:02.000Z"),
                make_event("1", "first", "2026-01-01T12:00:01.000Z"),
            ],
            next_cursor="older-page",
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests[0]["sort"] == "-timestamp"
    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_first_page_asks_for_the_configured_page_size(
    log_store, logs_model_factory, search
):
    """One fetch is one Datadog request of at most one page."""
    requests = search(make_payload([]))

    log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests[0]["page"]["limit"] == log_store.default_query_size
    assert len(requests) == 1


def test_older_page_uses_the_native_cursor(
    log_store, logs_model_factory, search
):
    """Datadog's own continuation token is what walks back through history."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(
        make_payload(
            [make_event("2", "second", "2026-01-01T12:00:02.000Z")],
            next_cursor="older-page",
        ),
        make_payload([make_event("1", "first", "2026-01-01T12:00:01.000Z")]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, before=first.before)

    assert requests[1]["page"]["cursor"] == "older-page"
    assert requests[1]["sort"] == "-timestamp"
    assert [entry.message for entry in second.items] == ["first"]


def test_no_older_page_reports_no_cursor(
    log_store, logs_model_factory, search
):
    """Running out of continuation tokens means the stream starts here."""
    search(
        make_payload([make_event("1", "first", "2026-01-01T12:00:01.000Z")])
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert page.before is None


def test_a_full_page_without_a_cursor_can_still_be_continued(
    log_store, logs_model_factory, search
):
    """Only an unfilled page proves that a run's history has been read out."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(
        make_payload(
            [
                make_event("2", "second", "2026-01-01T12:00:02.000Z"),
                make_event("1", "first", "2026-01-01T12:00:01.000Z"),
            ]
        ),
        make_payload([make_event("0", "zeroth", "2026-01-01T12:00:00.000Z")]),
    )

    first = log_store.fetch(logs, limit=2)
    second = log_store.fetch(logs, limit=2, before=first.before)

    assert requests[1]["sort"] == "-timestamp"
    assert requests[1]["filter"]["to"] == "2026-01-01T12:00:01+00:00"
    assert [entry.message for entry in second.items] == ["zeroth"]


def test_newer_page_resumes_at_the_newest_entry(
    log_store, logs_model_factory, search
):
    """Tailing scans forward from the newest entry already seen."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(
        make_payload([make_event("2", "second", "2026-01-01T12:00:02.000Z")]),
        make_payload([make_event("3", "third", "2026-01-01T12:00:03.000Z")]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert requests[1]["sort"] == "timestamp"
    assert requests[1]["filter"]["from"] == "2026-01-01T12:00:02+00:00"
    assert [entry.message for entry in second.items] == ["third"]


def test_newer_page_drops_entries_already_seen(
    log_store, logs_model_factory, search
):
    """A timestamp boundary is inclusive, so its entries must be deduplicated."""
    logs = logs_model_factory(log_store_id=log_store.id)
    seen = make_event("2", "second", "2026-01-01T12:00:02.000Z")
    search(
        make_payload([seen]),
        make_payload(
            [seen, make_event("3", "third", "2026-01-01T12:00:02.000Z")]
        ),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert [entry.message for entry in second.items] == ["third"]


def test_empty_tail_keeps_its_cursor(log_store, logs_model_factory, search):
    """A tail that finds nothing new can still be resumed later."""
    logs = logs_model_factory(log_store_id=log_store.id)
    search(
        make_payload([make_event("2", "second", "2026-01-01T12:00:02.000Z")]),
        make_payload([]),
    )

    first = log_store.fetch(logs)
    second = log_store.fetch(logs, after=first.after)

    assert second.items == []
    assert second.after == first.after


def test_empty_first_page_can_be_tailed_from_the_start(
    log_store, logs_model_factory, search
):
    """A pipeline that has not logged yet still gets a usable tail cursor."""
    logs = logs_model_factory(
        log_store_id=log_store.id,
        created=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
    )
    requests = search(make_payload([]), make_payload([]))

    page = log_store.fetch(logs)
    log_store.fetch(logs, after=page.after)

    assert page.after is not None
    assert requests[1]["filter"]["from"] == "2026-01-01T12:00:00+00:00"


def test_filters_are_pushed_into_the_query(
    log_store, logs_model_factory, search
):
    """Datadog does the filtering, so the query has to express it."""
    requests = search(make_payload([]))

    log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        filter_=LogsEntriesFilter(
            search='say "hi"',
            level=LoggingLevels.WARNING,
            since=datetime(2026, 1, 2, tzinfo=timezone.utc),
            until=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
    )

    query = requests[0]["filter"]["query"]
    assert 'say \\"hi\\"' in query
    assert "status:(warn OR warning OR err OR error" in query
    assert "debug" not in query
    assert requests[0]["filter"]["from"] == "2026-01-02T00:00:00+00:00"
    assert requests[0]["filter"]["to"] == "2026-01-03T00:00:00+00:00"


def test_query_is_scoped_to_the_log_stream(
    log_store, logs_model_factory, search
):
    """Entries of other runs must never leak into a log stream."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests = search(make_payload([]))

    log_store.fetch(logs)

    assert f"@zenml.log.id:{logs.id}" in requests[0]["filter"]["query"]
    assert "service:zenml" in requests[0]["filter"]["query"]


def test_status_is_mapped_to_a_log_level(
    log_store, logs_model_factory, search
):
    """Datadog spells its severities differently to Python."""
    search(
        make_payload(
            [
                make_event(
                    "3", "c", "2026-01-01T12:00:03.000Z", status="unknown"
                ),
                make_event(
                    "2", "b", "2026-01-01T12:00:02.000Z", status="emergency"
                ),
                make_event(
                    "1", "a", "2026-01-01T12:00:01.000Z", status="warn"
                ),
            ]
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert [entry.level for entry in page.items] == [
        LoggingLevels.WARNING,
        LoggingLevels.CRITICAL,
        LoggingLevels.INFO,
    ]


def test_logs_of_another_log_store_are_rejected(log_store, logs_model_factory):
    """Searching the wrong Datadog account would look like an empty run."""
    with pytest.raises(ValueError, match="log_store_id"):
        log_store.fetch(logs_model_factory(log_store_id=uuid4()))


def test_a_rejected_search_is_an_error(log_store, logs_model_factory, mocker):
    """A failed search must not look like a log stream with no entries."""
    mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.requests.post",
        return_value=StubResponse({}, status_code=403),
    )

    with pytest.raises(RuntimeError, match="403"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
