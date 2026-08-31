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
import requests

from zenml.enums import LoggingLevels, StackComponentType
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.datadog.datadog_log_store import DatadogLogStore
from zenml.models import LogsEntriesFilter


class StubResponse:
    """A canned Datadog search response."""

    def __init__(
        self,
        payload: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        text: str = "the-upstream-body",
        malformed: bool = False,
    ) -> None:
        """Store the payload to return.

        Args:
            payload: The response body.
            status_code: The response status.
            text: The raw response body.
            malformed: Whether decoding the body should fail.
        """
        self._payload = payload
        self._malformed = malformed
        self.status_code = status_code
        self.text = text

    def json(self) -> Any:
        """Return the response body.

        Returns:
            The response body.

        Raises:
            ValueError: If the response was set up as malformed.
        """
        if self._malformed:
            raise ValueError("not json")
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
    events: Optional[List[Dict[str, Any]]], next_cursor: Optional[str] = None
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
    requests_made: List[Dict[str, Any]] = []

    def _install(*payloads: Dict[str, Any]) -> List[Dict[str, Any]]:
        responses = [
            payload
            if isinstance(payload, StubResponse)
            else StubResponse(payload)
            for payload in payloads
        ]

        def _post(url, headers, json, timeout):
            requests_made.append(json)
            return responses[len(requests_made) - 1]

        mocker.patch(
            "zenml.log_stores.datadog.datadog_log_store.requests.post",
            side_effect=_post,
        )
        return requests_made

    return _install


def test_a_read_starts_at_the_oldest_entries_by_default(
    log_store, logs_model_factory, search
):
    """When start is omitted, Datadog reads from the oldest end."""
    requests_made = search(
        make_payload(
            [
                make_event("1", "first", "2026-01-01T12:00:01.000Z"),
                make_event("2", "second", "2026-01-01T12:00:02.000Z"),
            ]
        )
    )

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert requests_made[0]["sort"] == "timestamp"
    assert [entry.message for entry in page.items] == ["first", "second"]
    assert page.before is None
    assert page.after is None


def test_a_read_from_the_newest_end_returns_its_page_chronologically(
    log_store, logs_model_factory, search
):
    """The starting end picks where a read begins, not how a page is ordered."""
    requests_made = search(
        make_payload(
            [
                make_event("3", "third", "2026-01-01T12:00:03.000Z"),
                make_event("2", "second", "2026-01-01T12:00:02.000Z"),
                make_event("1", "first", "2026-01-01T12:00:01.000Z"),
            ]
        )
    )

    page = log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        start="newest",
    )

    assert requests_made[0]["sort"] == "-timestamp"
    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]


def test_after_continues_on_datadog_s_cursor(
    log_store, logs_model_factory, search
):
    """An oldest-end read pages with Datadog's own continuation token."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("1", "first", "2026-01-01T12:00:01.000Z")],
            next_cursor="next-page",
        ),
        make_payload([make_event("2", "second", "2026-01-01T12:00:02.000Z")]),
    )

    first = log_store.fetch(logs)
    log_store.fetch(logs, after=first.after)

    assert first.before is None
    assert first.after is not None
    assert requests_made[1]["page"]["cursor"] == "next-page"
    assert requests_made[1]["sort"] == "timestamp"


def test_before_continues_on_datadog_s_cursor(
    log_store, logs_model_factory, search
):
    """A newest-end read pages with the same token, in the other slot."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("2", "second", "2026-01-01T12:00:02.000Z")],
            next_cursor="older-page",
        ),
        make_payload([make_event("1", "first", "2026-01-01T12:00:01.000Z")]),
    )

    first = log_store.fetch(logs, start="newest")
    log_store.fetch(logs, start="newest", before=first.before)

    assert first.after is None
    assert first.before is not None
    assert requests_made[1]["page"]["cursor"] == "older-page"
    assert requests_made[1]["sort"] == "-timestamp"


def test_an_oldest_read_refuses_before(
    log_store, logs_model_factory, search
):
    """Datadog cannot walk backwards from a read that started at the oldest end."""
    search(make_payload([]))

    with pytest.raises(ValueError, match="before"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id),
            start="oldest",
            before="anything",
        )


def test_a_newest_read_refuses_after(
    log_store, logs_model_factory, search
):
    """Datadog cannot walk forwards from a read that started at the newest end."""
    search(make_payload([]))

    with pytest.raises(ValueError, match="after"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id),
            start="newest",
            after="anything",
        )


def test_both_cursors_are_refused(log_store, logs_model_factory, search):
    """A page continues in one direction at a time."""
    search(make_payload([]))

    with pytest.raises(ValueError, match="only one"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id),
            before="a",
            after="b",
        )


def test_an_empty_page_reports_no_cursor(
    log_store, logs_model_factory, search
):
    """No events means this scan is over, even if Datadog still sent a token."""
    search(make_payload([], next_cursor="a-token-past-the-end"))

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert page.items == []
    assert page.before is None
    assert page.after is None


def test_a_null_data_field_is_the_end_of_the_results(
    log_store, logs_model_factory, search
):
    """Datadog documents `data: null` for a read that ran out of results."""
    search(make_payload(None))

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert page.items == []
    assert page.before is None
    assert page.after is None


def test_a_made_up_cursor_is_refused(log_store, logs_model_factory):
    """A cursor that cannot be decoded is not sent to Datadog."""
    with pytest.raises(ValueError, match="not one this server issued"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id),
            after="not-base64",
        )


def test_filters_are_pushed_into_the_query(
    log_store, logs_model_factory, search
):
    """Datadog does the filtering, so the query has to express it."""
    requests_made = search(make_payload([]))

    log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        filter_=LogsEntriesFilter(
            search='say "hi"',
            level=LoggingLevels.WARNING,
            since=datetime(2026, 1, 2, tzinfo=timezone.utc),
            until=datetime(2026, 1, 3, tzinfo=timezone.utc),
        ),
    )

    query = requests_made[0]["filter"]["query"]
    assert '*say \\"hi\\"*' in query
    assert "status:warn" in query
    assert "status:debug" not in query
    assert requests_made[0]["filter"]["from"] == "2026-01-02T00:00:00+00:00"
    assert requests_made[0]["filter"]["to"] == "2026-01-03T00:00:00+00:00"


def test_query_is_scoped_to_the_log_stream(
    log_store, logs_model_factory, search
):
    """Entries of other runs must never leak into a log stream."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(make_payload([]))

    log_store.fetch(logs)

    assert f"@zenml.log.id:{logs.id}" in requests_made[0]["filter"]["query"]
    assert "service:zenml" in requests_made[0]["filter"]["query"]


def test_status_is_mapped_to_a_log_level(
    log_store, logs_model_factory, search
):
    """Datadog spells its severities differently to Python."""
    search(
        make_payload(
            [
                make_event(
                    "1", "a", "2026-01-01T12:00:01.000Z", status="warn"
                ),
                make_event(
                    "2", "b", "2026-01-01T12:00:02.000Z", status="emergency"
                ),
                make_event(
                    "3", "c", "2026-01-01T12:00:03.000Z", status="unknown"
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


def test_a_rejected_search_is_an_error(log_store, logs_model_factory, search):
    """A failed search must not look like a log stream with no entries."""
    search(StubResponse(status_code=403))

    with pytest.raises(RuntimeError, match="403") as failure:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert "the-upstream-body" not in str(failure.value)


def test_an_unreachable_datadog_is_an_error(
    log_store, logs_model_factory, mocker
):
    """A network failure has to arrive as a log store failure."""
    mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.requests.post",
        side_effect=requests.ConnectionError("no route"),
    )

    with pytest.raises(RuntimeError, match="Could not reach Datadog"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
