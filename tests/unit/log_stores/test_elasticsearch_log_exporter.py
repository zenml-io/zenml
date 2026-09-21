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
"""Tests for the documents written to the Elasticsearch bulk API."""

import json
from types import SimpleNamespace
from uuid import UUID

import pytest
import requests
from opentelemetry.sdk._logs.export import LogRecordExportResult

from zenml.log_stores.elasticsearch.elasticsearch_log_exporter import (
    ElasticsearchLogExporter,
)


def make_record(timestamp_ns: int, message: str) -> SimpleNamespace:
    """Build the parts of a readable log record the exporter reads."""
    return SimpleNamespace(
        log_record=SimpleNamespace(
            timestamp=timestamp_ns,
            body=message,
            severity_text="ERROR",
            severity_number=SimpleNamespace(value=17),
            attributes={"zenml.log.id": "log-id"},
        ),
        resource=SimpleNamespace(attributes={"service.name": "zenml"}),
        instrumentation_scope=None,
    )


def make_response(payload: object, status: int = 200) -> requests.Response:
    """Build a bulk response."""
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload).encode()
    return response


def test_bulk_documents_have_unique_sort_ids_across_writers(mocker):
    """Each writer persists its event IDs in both bulk actions and documents."""
    exporters = [
        ElasticsearchLogExporter(
            endpoint="https://elasticsearch:9200/zenml-logs/_bulk"
        )
        for _ in range(2)
    ]
    post = mocker.patch(
        "requests.Session.post",
        return_value=make_response(
            {"errors": False, "items": [{"create": {"status": 201}}]}
        ),
    )
    for exporter in exporters:
        assert (
            exporter.export([make_record(1_700_000_000, "hello")])
            == LogRecordExportResult.SUCCESS
        )
        exporter.shutdown()

    event_ids = set()
    for call in post.call_args_list:
        body = call.kwargs["data"]
        assert body.endswith(b"\n")
        action, document = [json.loads(line) for line in body.splitlines()]
        event_id = document["event_id"]
        assert UUID(event_id)
        event_ids.add(event_id)
        assert action == {"create": {"_id": event_id}}
        assert document["timestamp_nanos"] == 1_700_000_000
        assert document["@timestamp"] == "1970-01-01T00:00:01.700000+00:00"
        assert document["message"] == "hello"
        assert document["severity_number"] == 17
        assert document["zenml.log.id"] == "log-id"
    assert len(event_ids) == 2


@pytest.mark.parametrize(
    "response",
    [
        make_response(
            {
                "errors": True,
                "items": [
                    {
                        "create": {
                            "status": 400,
                            "error": {"reason": "private document"},
                        }
                    }
                ],
            }
        ),
        make_response(
            {"errors": False, "items": [{"create": {"status": 400}}]}
        ),
        make_response({"errors": False, "items": []}),
        make_response({}, status=302),
        make_response({}, status=503),
    ],
)
def test_partial_bulk_writes_and_http_failures_are_reported(mocker, response):
    """HTTP200 is successful only when all bulk create operations succeeded."""
    mocker.patch("requests.Session.post", return_value=response)
    exporter = ElasticsearchLogExporter(
        endpoint="http://elasticsearch:9200/zenml-logs/_bulk"
    )
    assert (
        exporter.export([make_record(1, "hello")])
        == LogRecordExportResult.FAILURE
    )
    exporter.shutdown()


def test_transient_bulk_failures_retry_only_failed_records_with_original_ids(
    mocker,
):
    """Selective retries preserve IDs and accept already-created records."""
    post = mocker.patch(
        "requests.Session.post",
        side_effect=[
            make_response(
                {
                    "errors": True,
                    "items": [
                        {"create": {"status": status}}
                        for status in (201, 429, 503)
                    ],
                }
            ),
            make_response(
                {
                    "errors": True,
                    "items": [
                        {"create": {"status": status}} for status in (201, 409)
                    ],
                }
            ),
        ],
    )
    sleep = mocker.patch(
        "zenml.log_stores.elasticsearch.elasticsearch_log_exporter.sleep"
    )
    exporter = ElasticsearchLogExporter(
        endpoint="http://elasticsearch:9200/zenml-logs/_bulk"
    )
    result = exporter.export(
        [make_record(1, message) for message in ("first", "second", "third")]
    )
    exporter.shutdown()

    assert result == LogRecordExportResult.SUCCESS
    assert post.call_count == 2
    original = post.call_args_list[0].kwargs["data"].splitlines(keepends=True)
    assert post.call_args_list[1].kwargs["data"] == b"".join(original[2:])
    sleep.assert_called_once_with(0.25)


def test_transient_bulk_retries_are_bounded(mocker):
    """Exhausted retries report failure without regenerating event IDs."""
    post = mocker.patch(
        "requests.Session.post",
        return_value=make_response(
            {"errors": True, "items": [{"create": {"status": 429}}]}
        ),
    )
    sleep = mocker.patch(
        "zenml.log_stores.elasticsearch.elasticsearch_log_exporter.sleep"
    )
    exporter = ElasticsearchLogExporter(
        endpoint="http://elasticsearch:9200/zenml-logs/_bulk"
    )
    result = exporter.export([make_record(1, "retry")])
    exporter.shutdown()

    assert result == LogRecordExportResult.FAILURE
    assert post.call_count == 3
    assert len({call.kwargs["data"] for call in post.call_args_list}) == 1
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]
