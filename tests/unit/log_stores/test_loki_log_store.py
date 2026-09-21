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
"""Tests for bounded Loki log retrieval."""

import base64
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Type
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
from zenml.log_stores.loki.loki_flavor import LokiLogStoreConfig
from zenml.log_stores.loki.loki_log_store import LokiLogStore
from zenml.models import LogsEntriesFilter, LogsResponse
from zenml.utils.time_utils import to_unix_nanos

NOON = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
NOON_NS = 1767268800000000000


class StubResponse:
    """A canned Loki response."""

    def __init__(
        self,
        payload: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        malformed: bool = False,
    ) -> None:
        """Configure a response.

        Args:
            payload: Parsed response body.
            status_code: HTTP status.
            headers: Response headers.
            malformed: Whether JSON decoding fails.
        """
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.malformed = malformed
        self.text = "private provider diagnostic"

    def json(self) -> Any:
        """Return the configured payload.

        Returns:
            The response body.

        Raises:
            ValueError: If JSON decoding was configured to fail.
        """
        if self.malformed:
            raise ValueError(self.text)
        return self.payload


def make_entry(
    timestamp_ns: int, message: str, severity: Optional[int] = None
) -> List[Any]:
    """Build a timestamp, message, and metadata tuple for Loki.

    Args:
        timestamp_ns: Unix timestamp in nanoseconds.
        message: Log message.
        severity: Optional OpenTelemetry severity number.

    Returns:
        A Loki entry represented as a JSON array.
    """
    metadata = (
        {"severity_number": str(severity)} if severity is not None else {}
    )
    return [str(timestamp_ns), message, metadata]


def make_payload(
    *streams: List[List[Any]], labels: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Build a Loki response from streams of entries.

    Args:
        *streams: Lists of entries.
        labels: Additional stream labels.

    Returns:
        A successful query response.
    """
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
    """Create a Loki log store without network access."""
    return LokiLogStore(
        name="loki",
        id=uuid4(),
        config=LokiLogStoreConfig(endpoint="http://loki:3100/otlp/v1/logs"),
        flavor="loki",
        type=StackComponentType.LOG_STORE,
        user=uuid4(),
        created=NOON,
        updated=NOON,
    )


@pytest.fixture
def query(mocker: MockerFixture) -> Callable[..., List[Dict[str, Any]]]:
    """Capture query requests and return configured responses."""

    def install(*payloads: Any) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        responses = [
            payload
            if isinstance(payload, StubResponse)
            else StubResponse(payload)
            for payload in payloads
        ]

        def get(url: str, **kwargs: Any) -> StubResponse:
            calls.append({"url": url, **kwargs})
            return responses[len(calls) - 1]

        mocker.patch(
            "zenml.log_stores.loki.loki_log_store.requests.get",
            side_effect=get,
        )
        return calls

    return install


@pytest.mark.parametrize(
    "start,direction",
    [(None, "backward"), ("newest", "backward"), ("oldest", "forward")],
)
def test_batch_is_chronological_across_streams_without_cursors(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    start: Optional[str],
    direction: str,
) -> None:
    """Test ordering and absent cursors for all supported starting points."""
    calls = query(
        make_payload(
            [
                make_entry(NOON_NS + 3, "third"),
                make_entry(NOON_NS + 1, "first"),
            ],
            [make_entry(NOON_NS + 2, "second")],
        )
    )
    page = log_store.fetch(
        logs_model_factory(log_store_id=log_store.id), start=start, limit=3
    )
    assert [entry.message for entry in page.items] == [
        "first",
        "second",
        "third",
    ]
    assert page.before is None and page.after is None
    assert calls[0]["params"]["direction"] == direction
    assert calls[0]["params"]["limit"] == "3"


@pytest.mark.parametrize("limit,expected", [(None, 1000), (100000, 5000)])
def test_query_limit_is_bounded(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    limit: Optional[int],
    expected: int,
) -> None:
    """Test the default batch size and maximum query limit."""
    calls = query(make_payload())
    page = log_store.fetch(
        logs_model_factory(log_store_id=log_store.id), limit=limit
    )
    assert calls[0]["params"]["limit"] == str(expected)
    assert page.items == [] and page.before is None and page.after is None


@pytest.mark.parametrize(
    "params",
    [
        {"before": ""},
        {"after": ""},
        {"before": "cursor"},
        {"after": "cursor"},
        {"before": "a", "after": "b"},
        {"start": "middle"},
        {"limit": 0},
    ],
)
def test_unsupported_parameters_fail_before_query(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    mocker: MockerFixture,
    params: Dict[str, Any],
) -> None:
    """Reject unsupported cursors and invalid input before contacting Loki."""
    get = mocker.patch("zenml.log_stores.loki.loki_log_store.requests.get")
    with pytest.raises(ValueError):
        log_store.fetch(
            logs_model_factory(log_store_id=log_store.id), **params
        )
    get.assert_not_called()


def test_filters_are_escaped_scoped_and_use_inclusive_bounds(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    mocker: MockerFixture,
) -> None:
    """Test literal query values, severity filtering, and exact bounds."""
    service = 'service"} |= "escape\n\\'
    search = 'say "hi"\n\\ ❄'
    mocker.patch.object(
        LokiLogStore,
        "config",
        new_callable=mocker.PropertyMock,
        return_value=log_store.config.model_copy(
            update={"service_name": service}
        ),
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    calls = query(make_payload())
    bound = NOON.replace(microsecond=123456)
    log_store.fetch(
        logs,
        filter_=LogsEntriesFilter(
            search=search, level="WARNING", since=bound, until=bound
        ),
    )
    params = calls[0]["params"]
    assert params["query"] == (
        f"{{service_name={json.dumps(service, ensure_ascii=False)}}} "
        f'| zenml_log_id="{logs.id}" '
        f"|= {json.dumps(search, ensure_ascii=False)} "
        '| severity_number >= 13 | __error__=""'
    )
    assert params["start"] == str(NOON_NS + 123456000)
    assert params["end"] == str(NOON_NS + 123456001)


def test_default_window_uses_stream_creation_and_current_time(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    mocker: MockerFixture,
) -> None:
    """Test the initial time window when bounds are omitted."""
    mocker.patch(
        "zenml.log_stores.loki.loki_log_store.utc_now", return_value=NOON
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    calls = query(make_payload())
    log_store.fetch(logs)
    assert calls[0]["params"]["start"] == str(to_unix_nanos(logs.created))
    assert calls[0]["params"]["end"] == str(NOON_NS + 1)


def test_native_identity_is_stable_and_distinguishes_nanoseconds_and_metadata(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
) -> None:
    """Preserve stable IDs without merging distinct native entries."""
    duplicate = make_entry(NOON_NS + 1, "same", 17)
    values = [
        duplicate,
        duplicate,
        make_entry(NOON_NS + 2, "same", 17),
        make_entry(NOON_NS + 1, "same", 21),
    ]
    other_stream = make_payload(values, labels={"host": "other"})
    calls = query(
        make_payload(values),
        make_payload(list(reversed(values))),
        other_stream,
        make_payload(
            [[str(NOON_NS + 1), "same"]], labels={"severity_number": "17"}
        ),
    )
    logs = logs_model_factory(log_store_id=log_store.id)
    first = log_store.fetch(logs)
    second = log_store.fetch(logs, start="oldest")
    other = log_store.fetch(logs)
    alternate_metadata = log_store.fetch(logs)
    assert len(first.items) == 4
    assert len({entry.id for entry in first.items}) == 3
    assert [entry.id for entry in first.items] == [
        entry.id for entry in second.items
    ]
    assert all(isinstance(entry.id, UUID) for entry in first.items)
    assert {entry.id for entry in first.items}.isdisjoint(
        entry.id for entry in other.items
    )
    assert alternate_metadata.items[0].id in {
        entry.id for entry in first.items
    }
    assert alternate_metadata.items[0].level == LoggingLevels.ERROR
    assert len(calls) == 4


@pytest.mark.parametrize("authentication", ["basic", "bearer"])
def test_secret_references_and_tls_apply_to_reads_and_writes(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    mocker: MockerFixture,
    authentication: str,
) -> None:
    """Test resolved secrets and shared transport configuration."""
    values = {"password": "resolved-password", "token": "resolved-token"}
    client = mocker.patch("zenml.client.Client").return_value
    client.get_secret_by_name_and_private_status.return_value = (
        SimpleNamespace(values=values, secret_values=values)
    )
    auth = (
        {"username": "user", "password": "{{loki.password}}"}
        if authentication == "basic"
        else {"api_key": "{{loki.token}}"}
    )
    store = LokiLogStore(
        name=log_store.name,
        id=log_store.id,
        flavor="loki",
        type=StackComponentType.LOG_STORE,
        user=log_store.user,
        created=NOON,
        updated=NOON,
        config=LokiLogStoreConfig(
            endpoint="https://loki/otlp/v1/logs",
            tenant_id="tenant",
            headers={"X-Custom": "custom"},
            certificate_file="ca.pem",
            client_certificate_file="cert.pem",
            client_key_file="key.pem",
            **auth,
        ),
    )
    exporter = mocker.patch(
        "zenml.log_stores.loki.loki_log_store.OTLPLogExporter"
    )
    store.get_exporter()
    calls = query(make_payload())
    store.fetch(logs_model_factory(log_store_id=store.id))
    expected_auth = (
        "Basic " + base64.b64encode(b"user:resolved-password").decode()
        if authentication == "basic"
        else "Bearer resolved-token"
    )
    expected_headers = {
        "Authorization": expected_auth,
        "X-Scope-OrgID": "tenant",
        "X-Custom": "custom",
    }
    assert (
        calls[0]["headers"]
        == expected_headers
        == exporter.call_args.kwargs["headers"]
    )
    assert calls[0]["verify"] == "ca.pem"
    assert calls[0]["cert"] == ("cert.pem", "key.pem")
    assert calls[0]["allow_redirects"] is False
    assert store.config.headers == {"X-Custom": "custom"}
    assert exporter.call_args.kwargs["certificate_file"] == "ca.pem"
    assert exporter.call_args.kwargs["client_certificate_file"] == "cert.pem"
    assert exporter.call_args.kwargs["client_key_file"] == "key.pem"


@pytest.mark.parametrize(
    "status,exception",
    [
        (403, LogStoreError),
        (302, LogStoreError),
        (429, LogStoreRateLimitError),
        (503, LogStoreUnavailableError),
    ],
)
def test_http_errors_preserve_domain_type_without_provider_body(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    status: int,
    exception: Type[LogStoreError],
) -> None:
    """Test safe errors and retry delays for rejected queries."""
    query(StubResponse({}, status, headers={"Retry-After": "17"}))
    with pytest.raises(exception) as error:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    assert "private provider diagnostic" not in str(error.value)
    if isinstance(error.value, LogStoreRateLimitError):
        assert error.value.retry_after == 17


def test_connection_errors_do_not_expose_request_details(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    mocker: MockerFixture,
) -> None:
    """Suppress potentially sensitive transport diagnostics."""
    mocker.patch(
        "zenml.log_stores.loki.loki_log_store.requests.get",
        side_effect=requests.ConnectionError("private provider diagnostic"),
    )
    with pytest.raises(LogStoreUnavailableError) as error:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    assert "private provider diagnostic" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "response",
    [
        StubResponse({}, malformed=True),
        StubResponse([]),
        StubResponse(
            {"status": "error", "error": "private provider diagnostic"}
        ),
        StubResponse(
            {
                "status": "success",
                "data": {"resultType": "matrix", "result": []},
            }
        ),
        StubResponse(
            {
                "status": "success",
                "data": {"resultType": "streams", "result": [None]},
            }
        ),
        StubResponse(
            make_payload([["invalid", "private provider diagnostic"]])
        ),
        StubResponse(make_payload([[str(NOON_NS), "message", []]])),
    ],
)
def test_invalid_responses_do_not_look_like_empty_batches(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    query: Callable[..., List[Dict[str, Any]]],
    response: StubResponse,
) -> None:
    """Reject malformed responses and entries without exposing their data."""
    query(response)
    with pytest.raises(LogStoreError) as error:
        log_store.fetch(logs_model_factory(log_store_id=log_store.id))
    assert "private provider diagnostic" not in str(error.value)


def test_wrong_store_is_rejected_before_query(
    log_store: LokiLogStore,
    logs_model_factory: Callable[..., LogsResponse],
    mocker: MockerFixture,
) -> None:
    """Reject streams collected by another log store."""
    get = mocker.patch("zenml.log_stores.loki.loki_log_store.requests.get")
    with pytest.raises(ValueError, match="log_store_id"):
        log_store.fetch(logs_model_factory(log_store_id=uuid4()))
    get.assert_not_called()


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "user"},
        {"password": "password"},
        {"username": "user", "password": "password", "api_key": "token"},
        {"client_key_file": "key.pem"},
    ],
)
def test_incomplete_or_ambiguous_authentication_is_rejected(
    credentials: Dict[str, str],
) -> None:
    """Reject incomplete basic authentication and client TLS configuration."""
    with pytest.raises(ValueError):
        LokiLogStoreConfig(endpoint="http://loki/otlp/v1/logs", **credentials)


def test_query_url_follows_endpoint_unless_explicit() -> None:
    """Keep derived URLs current across endpoint updates."""
    values = {"endpoint": "https://loki/prefix/otlp/v1/logs/"}
    config = LokiLogStoreConfig.model_validate(values)
    assert config.get_query_url() == "https://loki/prefix"
    assert "query_url" not in config.model_dump(exclude_unset=True)
    updated = LokiLogStoreConfig.model_validate(
        {
            **config.model_dump(exclude_unset=True),
            "endpoint": "https://new/otlp/v1/logs",
        }
    )
    assert updated.get_query_url() == "https://new"
    assert values == {"endpoint": "https://loki/prefix/otlp/v1/logs/"}
    assert (
        LokiLogStoreConfig(
            endpoint=values["endpoint"], query_url="https://query/prefix/"
        ).get_query_url()
        == "https://query/prefix"
    )
