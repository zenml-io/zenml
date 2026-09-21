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
"""Tests for Elasticsearch log queries and native pagination."""

import base64
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
import requests

from zenml.enums import LoggingLevels, StackComponentType
from zenml.exceptions import (
    LogStoreError,
    LogStoreRateLimitError,
    LogStoreUnavailableError,
)
from zenml.log_stores.elasticsearch.elasticsearch_flavor import (
    ElasticsearchLogStoreConfig,
)
from zenml.log_stores.elasticsearch.elasticsearch_log_store import (
    ElasticsearchLogStore,
)
from zenml.models import LogsEntriesFilter
from zenml.utils.time_utils import to_unix_nanos

NOON = to_unix_nanos(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))
SEARCH_POST = (
    "zenml.log_stores.elasticsearch.elasticsearch_log_store.requests.post"
)


def make_hit(
    number: int,
    severity_number: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a search hit with a stable ID and provider sort values."""
    event_id = str(UUID(int=number))
    return {
        "_id": event_id,
        "_index": "zenml-logs",
        "_source": {
            "timestamp_nanos": NOON,
            "event_id": event_id,
            "message": f"message {number}",
            "severity_number": severity_number,
        },
        "sort": [NOON, event_id],
    }


def make_response(
    entries: List[Dict[str, Any]], status: int = 200, **metadata: Any
) -> requests.Response:
    """Build a JSON search response."""
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(
        {
            "timed_out": False,
            "_shards": {"failed": 0},
            "hits": {"hits": entries},
            **metadata,
        }
    ).encode()
    return response


@pytest.fixture
def log_store() -> ElasticsearchLogStore:
    """An Elasticsearch log store with unused credentials."""
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


def test_default_newest_read_uses_native_cursor_and_frozen_window(
    log_store, logs_model_factory, mocker
):
    """A cursor alone retains the query and advances over timestamp ties."""
    post = mocker.patch(
        SEARCH_POST,
        side_effect=[
            make_response([make_hit(3), make_hit(2)]),
            make_response([make_hit(1)]),
            make_response([]),
        ],
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    first = log_store.fetch(logs)
    second = log_store.fetch(logs, before=first.before)
    terminal = log_store.fetch(logs, before=second.before)

    first_query, second_query, _ = [
        call.kwargs["json"] for call in post.call_args_list
    ]
    assert first_query["sort"] == [
        {"timestamp_nanos": "desc"},
        {"event_id.keyword": "desc"},
    ]
    assert first_query["size"] == 1000
    assert "search_after" not in first_query
    assert second_query == {
        **first_query,
        "search_after": make_hit(2)["sort"],
    }
    assert first_query["query"]["bool"]["filter"][0] == {
        "term": {"zenml.log.id.keyword": str(logs.id)}
    }
    window = first_query["query"]["bool"]["filter"][1]["range"][
        "timestamp_nanos"
    ]
    assert window["gte"] == to_unix_nanos(logs.created)
    assert window["lte"] > window["gte"]
    assert [entry.message for entry in first.items] == [
        "message 2",
        "message 3",
    ]
    assert [entry.message for entry in second.items] == ["message 1"]
    assert first.before and first.after is None
    assert terminal.items == []
    assert terminal.before is terminal.after is None
    assert "until" not in first.model_dump()


def test_oldest_traversal_and_repeated_reads_keep_event_ids(
    log_store, logs_model_factory, mocker
):
    """Native IDs remain stable in either traversal direction."""
    hits = [make_hit(1), make_hit(2, 17), make_hit(3, 21)]
    post = mocker.patch(
        SEARCH_POST,
        side_effect=[
            make_response(hits),
            make_response([]),
            make_response(hits[::-1]),
        ],
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    oldest = log_store.fetch(logs, start="oldest", limit=3)
    log_store.fetch(logs, after=oldest.after)
    newest = log_store.fetch(logs, limit=3)

    assert oldest.before is None and oldest.after
    assert (
        post.call_args_list[1].kwargs["json"]["search_after"]
        == hits[-1]["sort"]
    )
    assert post.call_args_list[0].kwargs["json"]["sort"] == [
        {"timestamp_nanos": "asc"},
        {"event_id.keyword": "asc"},
    ]
    assert oldest.items == newest.items
    assert len({entry.id for entry in oldest.items}) == 3
    assert [entry.level for entry in oldest.items] == [
        LoggingLevels.INFO,
        LoggingLevels.ERROR,
        LoggingLevels.CRITICAL,
    ]


def test_filters_are_restored_from_cursor(
    log_store, logs_model_factory, mocker
):
    """The provider applies phrase, level and time filters on every page."""
    post = mocker.patch(
        SEARCH_POST,
        side_effect=[make_response([make_hit(1)]), make_response([])],
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    filters = LogsEntriesFilter(
        search='failed to connect "host"',
        level=LoggingLevels.WARNING,
        since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        until=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    first = log_store.fetch(logs, start="oldest", limit=20000, filter_=filters)
    log_store.fetch(logs, after=first.after)

    initial, continued = [call.kwargs["json"] for call in post.call_args_list]
    assert initial["query"] == continued["query"]
    assert initial["size"] == continued["size"] == 10000
    assert initial["query"]["bool"]["filter"] == [
        {"term": {"zenml.log.id.keyword": str(logs.id)}},
        {
            "range": {
                "timestamp_nanos": {
                    "gte": to_unix_nanos(filters.since),
                    "lte": to_unix_nanos(filters.until),
                }
            }
        },
        {"range": {"severity_number": {"gte": 13}}},
        {"match_phrase": {"message": filters.search}},
    ]


@pytest.mark.parametrize(
    "conflict",
    [
        {"start": "oldest"},
        {"limit": 2},
        {"filter_": LogsEntriesFilter(search="other")},
        {
            "filter_": LogsEntriesFilter(
                since=datetime(2026, 1, 2, tzinfo=timezone.utc)
            )
        },
    ],
)
def test_continuation_rejects_conflicting_parameters(
    log_store, logs_model_factory, mocker, conflict
):
    """An existing cursor cannot silently start a different query."""
    post = mocker.patch(SEARCH_POST, return_value=make_response([make_hit(1)]))
    logs = logs_model_factory(log_store_id=log_store.id)
    page = log_store.fetch(logs, limit=1)

    with pytest.raises(ValueError, match="conflicts"):
        log_store.fetch(logs, before=page.before, **conflict)
    assert post.call_count == 1


def test_cursor_is_scoped_to_store_stream_and_direction(
    log_store, logs_model_factory, mocker
):
    """Unsigned cursors cannot bypass the trusted stream query."""
    post = mocker.patch(SEARCH_POST, return_value=make_response([make_hit(1)]))
    logs = logs_model_factory(log_store_id=log_store.id)
    page = log_store.fetch(logs)
    other_logs = logs_model_factory(log_store_id=log_store.id)
    with pytest.raises(ValueError, match="stream"):
        log_store.fetch(other_logs, before=page.before)
    with pytest.raises(ValueError, match="direction"):
        log_store.fetch(logs, after=page.before)

    payload = json.loads(base64.urlsafe_b64decode(page.before))
    payload["log_store_id"] = str(uuid4())
    changed = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    with pytest.raises(ValueError, match="log store"):
        log_store.fetch(logs, before=changed)
    with pytest.raises(ValueError, match="log_store_id"):
        log_store.fetch(logs_model_factory(log_store_id=uuid4()))
    assert post.call_count == 1


@pytest.mark.parametrize("cursor", ["", "not-base64!", "WzEsIDJd"])
def test_malformed_cursor_is_rejected_before_search(
    log_store, logs_model_factory, mocker, cursor
):
    """Invalid cursor envelopes are input errors, not provider requests."""
    post = mocker.patch(SEARCH_POST)
    with pytest.raises(ValueError, match="cursor"):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id), before=cursor
        )
    post.assert_not_called()


@pytest.mark.parametrize(
    "status,error",
    [
        (401, LogStoreError),
        (429, LogStoreRateLimitError),
        (503, LogStoreUnavailableError),
    ],
)
def test_provider_http_errors(
    log_store, logs_model_factory, mocker, status, error
):
    """Provider failures preserve their retry category without exposing bodies."""
    response = make_response([], status=status)
    response.headers["Retry-After"] = "12"
    mocker.patch(SEARCH_POST, return_value=response)
    with pytest.raises(error) as exc:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    if status == 429:
        assert exc.value.retry_after == 12


@pytest.mark.parametrize(
    "response,error",
    [
        (make_response([], timed_out=True), LogStoreUnavailableError),
        (make_response([], _shards={"failed": 1}), LogStoreError),
        (make_response([], hits={"hits": None}), LogStoreError),
        (
            make_response([{**make_hit(1), "sort": [NOON, None]}]),
            LogStoreError,
        ),
        (make_response([{**make_hit(1), "_id": ""}]), LogStoreError),
    ],
)
def test_incomplete_or_invalid_results_are_not_empty_pages(
    log_store, logs_model_factory, mocker, response, error
):
    """A failed search must not be mistaken for the end of a stream."""
    mocker.patch(SEARCH_POST, return_value=response)
    with pytest.raises(error):
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))


def test_search_connection_failure(log_store, logs_model_factory, mocker):
    """Connection errors become retryable domain errors."""
    mocker.patch(
        SEARCH_POST, side_effect=requests.ConnectionError("private details")
    )
    with pytest.raises(
        LogStoreUnavailableError, match="Could not reach"
    ) as exc:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    assert "private details" not in str(exc.value)


@pytest.mark.parametrize(
    "authentication,authorization",
    [
        ({"api_key": "{{elasticsearch.api_key}}"}, "ApiKey resolved-key"),
        (
            {"username": "elastic", "password": "{{elasticsearch.password}}"},
            "Basic ZWxhc3RpYzpyZXNvbHZlZC1wYXNzd29yZA==",
        ),
    ],
)
def test_secret_credentials_and_tls_apply_to_searches_and_exports(
    log_store, logs_model_factory, mocker, authentication, authorization
):
    """Resolved secrets and TLS configuration reach both request paths."""
    values = {"api_key": "resolved-key", "password": "resolved-password"}
    client = mocker.patch("zenml.client.Client").return_value
    client.get_secret_by_name_and_private_status.return_value = (
        SimpleNamespace(values=values, secret_values=values)
    )
    store = ElasticsearchLogStore(
        name=log_store.name,
        id=log_store.id,
        config=ElasticsearchLogStoreConfig(
            url="https://elasticsearch:9200",
            certificate_file="ca.pem",
            client_certificate_file="client.pem",
            client_key_file="client.key",
            **authentication,
        ),
        flavor="elasticsearch",
        type=StackComponentType.LOG_STORE,
        user=log_store.user,
        created=log_store.created,
        updated=log_store.updated,
    )
    exporter = mocker.patch(
        "zenml.log_stores.elasticsearch.elasticsearch_log_store.ElasticsearchLogExporter"
    )
    post = mocker.patch(SEARCH_POST, return_value=make_response([]))
    store.get_exporter()
    store.fetch(logs_model_factory(log_store_id=store.id))

    assert (
        exporter.call_args.kwargs["headers"]["Authorization"] == authorization
    )
    assert exporter.call_args.kwargs["certificate_file"] == "ca.pem"
    assert exporter.call_args.kwargs["client_certificate_file"] == "client.pem"
    assert exporter.call_args.kwargs["client_key_file"] == "client.key"
    assert (
        exporter.call_args.kwargs["endpoint"]
        == "https://elasticsearch:9200/zenml-logs/_bulk"
    )
    assert post.call_args.kwargs["headers"]["Authorization"] == authorization
    assert post.call_args.kwargs["verify"] == "ca.pem"
    assert post.call_args.kwargs["cert"] == ("client.pem", "client.key")
    assert post.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "authentication",
    [
        {"username": "elastic"},
        {"password": "password"},
        {"api_key": "key", "username": "elastic", "password": "password"},
    ],
)
def test_authentication_modes_are_validated(authentication):
    """An incomplete or ambiguous authentication configuration is rejected."""
    with pytest.raises(ValueError):
        ElasticsearchLogStoreConfig(
            url="http://elasticsearch:9200", **authentication
        )


def test_updated_configuration_keeps_export_and_search_destinations_aligned(
    log_store, logs_model_factory, mocker
):
    """Persisted defaults follow URL/index updates; explicit overrides survive."""
    config = log_store.config.model_dump(exclude_unset=True)
    config.update(url="https://new-cluster:9200", index="new-logs")
    updated = ElasticsearchLogStoreConfig.model_validate(config)
    store = ElasticsearchLogStore(
        name=log_store.name,
        id=log_store.id,
        config=updated,
        flavor="elasticsearch",
        type=StackComponentType.LOG_STORE,
        user=log_store.user,
        created=log_store.created,
        updated=log_store.updated,
    )
    exporter = mocker.patch(
        "zenml.log_stores.elasticsearch.elasticsearch_log_store.ElasticsearchLogExporter"
    )
    post = mocker.patch(SEARCH_POST, return_value=make_response([]))
    store.get_exporter()
    store.fetch(logs_model_factory(log_store_id=store.id))

    assert (
        exporter.call_args.kwargs["endpoint"]
        == "https://new-cluster:9200/new-logs/_bulk"
    )
    assert (
        post.call_args.args[0] == "https://new-cluster:9200/new-logs/_search"
    )
    config["endpoint"] = "https://ingestion:9200/custom/_bulk"
    assert (
        ElasticsearchLogStoreConfig.model_validate(config).endpoint
        == config["endpoint"]
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("_source", None),
        ("timestamp_nanos", "private provider details"),
        ("severity_number", "private provider details"),
    ],
)
def test_malformed_hit_fails_the_page_instead_of_advancing_past_it(
    log_store, logs_model_factory, mocker, field, value
):
    """A mixed page must not silently skip a record while returning its cursor."""
    malformed = make_hit(1)
    if field == "_source":
        malformed[field] = value
    else:
        malformed["_source"][field] = value
    post = mocker.patch(
        SEARCH_POST, return_value=make_response([make_hit(2), malformed])
    )
    with pytest.raises(LogStoreError, match="invalid log entry") as exc:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    assert "private provider details" not in str(exc.value)
    post.assert_called_once()
