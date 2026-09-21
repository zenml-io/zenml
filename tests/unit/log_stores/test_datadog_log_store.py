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
"""Tests for Datadog log retrieval and pagination."""

import base64
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
import requests
from pytest_mock import MockerFixture

from zenml.enums import LoggingLevels, StackComponentType
from zenml.exceptions import (
    LogStoreError,
    LogStoreRateLimitError,
    LogStoreUnavailableError,
)
from zenml.log_stores.datadog.datadog_flavor import DatadogLogStoreConfig
from zenml.log_stores.datadog.datadog_log_store import DatadogLogStore
from zenml.models import LogsEntriesFilter, LogsResponse


class StubResponse:
    """Stub Datadog search response."""

    def __init__(
        self,
        payload: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        text: str = "the-upstream-body",
        malformed: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Store the payload to return.

        Args:
            payload: The response body.
            status_code: The response status.
            text: The raw response body.
            malformed: Whether decoding the body should fail.
            headers: The response headers.
        """
        self._payload = payload
        self._malformed = malformed
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

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
    """Build a Datadog search event."""
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
    """Create a Datadog log store with test credentials."""
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
    """Capture search requests and return configured responses."""
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


def test_secret_references_authenticate_exports_and_searches(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    mocker: MockerFixture,
) -> None:
    """Test resolved secret references in both Datadog request paths."""
    values = {
        "api_key": "resolved-api-key",
        "application_key": "resolved-app-key",
    }
    client = mocker.patch("zenml.client.Client").return_value
    client.get_secret_by_name_and_private_status.return_value = (
        SimpleNamespace(values=values, secret_values=values)
    )
    store = DatadogLogStore(
        name=log_store.name,
        id=log_store.id,
        config=DatadogLogStoreConfig(
            api_key="{{datadog.api_key}}",
            application_key="{{datadog.application_key}}",
        ),
        flavor="datadog",
        type=StackComponentType.LOG_STORE,
        user=log_store.user,
        created=log_store.created,
        updated=log_store.updated,
    )
    exporter = mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.DatadogLogExporter"
    )
    post = mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.requests.post",
        return_value=StubResponse(make_payload([])),
    )

    store.get_exporter()
    store.fetch(logs_model_factory(log_store_id=store.id))

    expected_headers = {
        "dd-api-key": values["api_key"],
        "dd-application-key": values["application_key"],
    }
    assert exporter.call_args.kwargs["headers"] == expected_headers
    assert post.call_args.kwargs["headers"] == {
        **expected_headers,
        "Content-Type": "application/json",
    }
    assert all(
        call.kwargs == {"name": "datadog"}
        for call in client.get_secret_by_name_and_private_status.call_args_list
    )


def test_a_read_starts_at_the_oldest_entries_by_default(
    log_store, logs_model_factory, search
):
    """Test that reads start at the oldest end by default."""
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
    """Test chronological page order when starting from the newest end."""
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


def test_both_cursors_are_refused(log_store, logs_model_factory, search):
    """Test rejection of simultaneous before and after cursors."""
    search(make_payload([]))

    with pytest.raises(ValueError, match="only one"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id),
            before="a",
            after="b",
        )


@pytest.mark.parametrize("events", [[], None])
def test_an_empty_page_reports_no_cursor(
    log_store, logs_model_factory, search, events
):
    """Test that empty and null provider pages terminate pagination."""
    search(make_payload(events, next_cursor="a-token-past-the-end"))

    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert page.items == []
    assert page.before is None
    assert page.after is None


def test_filters_are_pushed_into_the_query(
    log_store, logs_model_factory, search
):
    """Test translation of filters into the Datadog query."""
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
    assert 'message:"say \\"hi\\""' in query
    assert (
        "status:(warn OR warning OR err OR error OR crit OR critical OR alert OR emerg OR emergency OR fatal)"
        in query
    )
    assert "debug" not in query
    assert requests_made[0]["filter"]["from"] == "2026-01-02T00:00:00+00:00"
    assert requests_made[0]["filter"]["to"] == "2026-01-03T00:00:00+00:00"


def test_status_is_mapped_to_a_log_level(
    log_store, logs_model_factory, search
):
    """Test mapping of Datadog status names to log levels."""
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
    """Test rejection of a mismatched log store ID."""
    with pytest.raises(ValueError, match="log_store_id"):
        log_store.fetch(logs_model_factory(log_store_id=uuid4()))


def test_a_rejected_search_is_an_error(log_store, logs_model_factory, search):
    """Test that rejected searches raise a log store error."""
    search(StubResponse(status_code=403))

    with pytest.raises(LogStoreError, match="403") as failure:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))

    assert "the-upstream-body" not in str(failure.value)


def test_an_unreachable_datadog_is_an_error(
    log_store, logs_model_factory, mocker
):
    """Test translation of network failures into log store errors."""
    mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.requests.post",
        side_effect=requests.ConnectionError("no route"),
    )

    with pytest.raises(
        LogStoreUnavailableError, match="Could not reach Datadog"
    ):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


@pytest.mark.parametrize(
    "start,slot", [("oldest", "after"), ("newest", "before")]
)
def test_continuations_keep_the_original_query_window(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    mocker: MockerFixture,
    start: str,
    slot: str,
) -> None:
    """Test that cursor-only requests preserve the query and time bounds."""
    now = datetime(2026, 1, 3, tzinfo=timezone.utc)
    clock = mocker.patch(
        "zenml.log_stores.datadog.datadog_log_store.utc_now",
        side_effect=[now, now + timedelta(minutes=2)],
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("1", "message 1", "2026-01-02T12:00:00Z")],
            "native/+=?",
        ),
        make_payload([]),
    )
    first = log_store.fetch(
        logs,
        start=start,
        limit=50,
        filter_=LogsEntriesFilter(
            search="message",
            level="WARNING",
            since=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
    )
    assert requests_made[0]["filter"]["to"] == now.isoformat()
    assert "until" not in first.model_dump()
    opposite_slot = "before" if slot == "after" else "after"
    assert first.model_dump()[opposite_slot] is None
    log_store.fetch(
        logs,
        **{slot: first.model_dump()[slot]},
    )
    assert requests_made[0]["filter"] == requests_made[1]["filter"]
    assert requests_made[1]["page"] == {"limit": 50, "cursor": "native/+=?"}
    assert requests_made[0]["sort"] == requests_made[1]["sort"]
    assert clock.call_count == 1


@pytest.mark.parametrize(
    "change",
    [
        "search",
        "until",
        "stream",
        "direction",
        "start",
        "limit",
    ],
)
def test_cursor_cannot_be_reused_for_a_different_query(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    change: str,
) -> None:
    """Test rejection of parameters that conflict with a cursor."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("1", "message", "2026-01-02T00:00:00Z")], "native"
        )
    )
    filters = {"until": datetime(2026, 1, 3, tzinfo=timezone.utc)}
    first = log_store.fetch(logs, filter_=LogsEntriesFilter(**filters))
    slot = "after"
    params = {}
    if change == "until":
        filters[change] = datetime(2026, 1, 2, tzinfo=timezone.utc)
    elif change == "search":
        filters[change] = "different"
    elif change == "stream":
        logs = logs_model_factory(log_store_id=log_store.id)
    elif change == "start":
        params["start"] = "newest"
    elif change == "limit":
        params["limit"] = 10
    else:
        slot = "before"
    with pytest.raises(ValueError, match="pagination cursor"):
        log_store.fetch(
            logs,
            **{slot: first.after},
            **params,
            filter_=LogsEntriesFilter(**filters),
        )
    assert len(requests_made) == 1


@pytest.mark.parametrize("cursor", ["", "@@@", "bmF0aXZl"])
def test_bad_cursor_never_reaches_datadog(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    cursor: str,
) -> None:
    """Test that invalid cursors never reach Datadog."""
    requests_made = search()
    with pytest.raises(ValueError, match="Invalid pagination cursor"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id),
            after=cursor,
            filter_=LogsEntriesFilter(
                until=datetime(2026, 1, 3, tzinfo=timezone.utc)
            ),
        )
    assert not requests_made


def test_identical_explicit_parameters_are_accepted(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test matching continuation filters with equivalent timezones."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("1", "message", "2026-01-02T00:00:00Z")], "native"
        ),
        make_payload([]),
    )
    filters = LogsEntriesFilter(
        search="message",
        level="WARNING",
        since=datetime(2026, 1, 2, tzinfo=timezone.utc),
        until=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )
    first = log_store.fetch(logs, start="oldest", limit=50, filter_=filters)
    log_store.fetch(
        logs,
        after=first.after,
        start="oldest",
        limit=50,
        filter_=LogsEntriesFilter(
            search="message",
            level="warn",
            since=datetime(2026, 1, 2, 1, tzinfo=timezone(timedelta(hours=1))),
            until=filters.until,
        ),
    )
    assert requests_made[0]["filter"] == requests_made[1]["filter"]


@pytest.mark.parametrize(
    "term,clause",
    [
        ("message", "message:*message*"),
        ("message 1", 'message:"message 1"'),
        ('x" OR *:*', 'message:"x\\" OR *:*"'),
        ("a:b*?", r"message:*a\:b\*\?*"),
    ],
)
def test_search_text_cannot_change_stream_scope(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    term: str,
    clause: str,
) -> None:
    """Test phrase quoting and escaping of search syntax."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(make_payload([]))
    log_store.fetch(logs, filter_=LogsEntriesFilter(search=term))
    assert requests_made[0]["filter"]["query"] == (
        f'service:"zenml" AND @zenml.log.id:{logs.id} AND {clause}'
    )


@pytest.mark.parametrize(
    "timestamp", ["2026-01-01T13:00:00+01:00", 1767268800000]
)
def test_timestamps_remain_aware_utc(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    timestamp: Any,
) -> None:
    """Numeric and ISO timestamps serialize consistently with UTC offsets."""
    search(make_payload([make_event("1", "message", timestamp)]))
    entry = log_store.fetch(
        logs_model_factory(log_store_id=log_store.id)
    ).items[0]
    assert entry.timestamp == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    assert entry.timestamp.utcoffset() == timedelta(0)
    assert entry.model_dump(mode="json")["timestamp"].endswith("Z")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": ["invalid"]},
        {"data": [{}], "meta": {"page": {"after": 1}}},
    ],
)
def test_invalid_provider_responses_raise_shared_error(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    payload: Any,
) -> None:
    """Test that malformed responses raise a log store error."""
    search(StubResponse(payload=payload))
    with pytest.raises(LogStoreError):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


@pytest.mark.parametrize(
    "status,error",
    [
        (429, LogStoreRateLimitError),
        (503, LogStoreUnavailableError),
    ],
)
def test_provider_failures_have_distinct_errors(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    status: int,
    error: type[Exception],
) -> None:
    """Test distinct errors for rate limits and backend unavailability."""
    search(
        StubResponse(status_code=status, headers={"X-RateLimit-Reset": "17"})
    )
    with pytest.raises(error) as failure:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    if status == 429:
        assert failure.value.retry_after == 17


def test_malformed_json_is_a_log_store_error(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test rejection of invalid JSON in successful HTTP responses."""
    search(StubResponse(malformed=True))
    with pytest.raises(LogStoreError):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


def test_unparsable_events_do_not_lose_the_native_cursor(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test continuation when all entries on a page fail to parse."""
    search(make_payload([make_event("1", "message", "invalid")], "next"))
    page = log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    assert page.items == []
    assert page.after is not None


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", 2),
        ("token", " \t"),
        ("log_store_id", str(uuid4())),
        ("limit", 1001),
        ("filters", {"since": None, "until": None}),
    ],
)
def test_invalid_cursor_state_is_rejected_before_search(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    field: str,
    value: Any,
) -> None:
    """Test rejection of invalid cursor state."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("1", "message", "2026-01-02T00:00:00Z")], "native"
        ),
    )
    first = log_store.fetch(logs)
    payload = json.loads(base64.urlsafe_b64decode(first.after))
    payload[field] = value
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    with pytest.raises(ValueError, match="Invalid pagination cursor"):
        log_store.fetch(logs, after=cursor)
    assert len(requests_made) == 1


def test_unsigned_cursor_filters_cannot_replace_trusted_scope(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test that cursor filters cannot override the authorized stream scope."""
    logs = logs_model_factory(log_store_id=log_store.id)
    requests_made = search(
        make_payload(
            [make_event("1", "message", "2026-01-02T00:00:00Z")], "native/+?="
        ),
        make_payload([]),
    )
    first = log_store.fetch(logs)
    assert "/" not in first.after and "+" not in first.after
    payload = json.loads(base64.urlsafe_b64decode(first.after))
    payload["filters"]["search"] = 'x" OR service:other'
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    log_store.fetch(logs, after=cursor)
    assert requests_made[1]["filter"]["query"] == (
        f'service:"zenml" AND @zenml.log.id:{logs.id} '
        'AND message:"x\\" OR service:other"'
    )
    assert requests_made[1]["page"]["cursor"] == "native/+?="


def test_default_page_size_matches_datadog_limit(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test the default and maximum Datadog page size."""
    requests_made = search(make_payload([]), make_payload([]))
    logs = logs_model_factory(log_store_id=log_store.id)
    log_store.fetch(logs)
    log_store.fetch(logs, limit=2000)
    assert log_store.default_query_size == 1000
    assert [request["page"]["limit"] for request in requests_made] == [
        1000,
        1000,
    ]


def test_http_success_with_timeout_is_not_a_complete_page(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test timeout metadata in successful HTTP responses."""
    search(
        {
            "data": [],
            "meta": {"status": "timeout", "page": {"after": "native"}},
        }
    )
    with pytest.raises(LogStoreUnavailableError, match="timed out"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


def test_partial_result_warnings_are_reported(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test rejection of partial results with provider warnings."""
    search(
        {
            "data": [make_event("1", "partial", "2026-01-01T12:00:00Z")],
            "meta": {
                "status": "done",
                "warnings": [{"code": "unknown_index"}],
            },
        }
    )
    with pytest.raises(LogStoreError, match="incomplete"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


def test_canonical_timestamps_preserve_provider_order_and_filter_range(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test precedence of provider timestamps over custom attributes."""
    first = make_event("1", "first", "2026-01-01T12:00:00Z")
    first["attributes"]["attributes"]["timestamp"] = 1767276000000
    second = make_event("2", "second", "2026-01-01T12:01:00Z")
    second["attributes"]["attributes"]["timestamp"] = "Jan 01 12:01:00"
    search(make_payload([first, second]))
    page = log_store.fetch(
        logs_model_factory(log_store_id=log_store.id),
        filter_=LogsEntriesFilter(
            since=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            until=datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
        ),
    )
    assert [entry.timestamp for entry in page.items] == [
        datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
    ]


def test_datadog_event_ids_are_preserved_across_reads(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Test stable event IDs across reads and log store instances."""
    event_id = "AwAAAZ-native/+=.event"
    payload = make_payload(
        [
            make_event(event_id, "message", "2026-01-01T12:00:00Z"),
            make_event(event_id + "other", "message", "2026-01-01T12:00:00Z"),
        ]
    )
    search(payload, payload, payload)
    logs = logs_model_factory(log_store_id=log_store.id)
    first = log_store.fetch(logs)
    second = log_store.fetch(logs)
    another_store = DatadogLogStore(
        name="another-datadog",
        id=uuid4(),
        config=log_store.config,
        flavor="datadog",
        type=StackComponentType.LOG_STORE,
        user=log_store.user,
        created=log_store.created,
        updated=log_store.updated,
    )
    third = another_store.fetch(
        logs_model_factory(log_store_id=another_store.id)
    )

    ids = [entry.id for entry in first.items]
    assert all(
        isinstance(entry_id, UUID) and entry_id.version == 5
        for entry_id in ids
    )
    assert len(set(ids)) == 2
    assert [entry.id for entry in second.items] == ids
    assert [entry.id for entry in third.items] == ids


@pytest.mark.parametrize("event_id", [None, " \t"])
def test_invalid_native_event_ids_are_reported(
    log_store: DatadogLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    search: Callable[..., List[Dict[str, Any]]],
    event_id: Any,
) -> None:
    """Test rejection of events without valid IDs."""
    search(
        make_payload([make_event(event_id, "message", "2026-01-01T12:00:00Z")])
    )
    with pytest.raises(LogStoreError, match="valid ID"):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
