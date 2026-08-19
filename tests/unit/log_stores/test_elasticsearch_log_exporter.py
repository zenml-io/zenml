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

import pytest

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


@pytest.fixture
def exporter() -> ElasticsearchLogExporter:
    """An exporter that never reaches a cluster."""
    return ElasticsearchLogExporter(
        endpoint="http://elasticsearch:9200/zenml-logs/_bulk"
    )


def export_lines(exporter, *records):
    """Encode records the way `export` does, and split the request body."""
    body = exporter._serialize(exporter._encode_logs(records)).decode("utf-8")

    assert body.endswith("\n"), "the bulk API rejects a body without one"

    return [json.loads(line) for line in body.splitlines()]


def test_every_document_is_preceded_by_an_action(exporter):
    """A bulk request interleaves what to do with what to write."""
    lines = export_lines(
        exporter, make_record(1, "first"), make_record(2, "second")
    )

    assert lines[0] == {"create": {}}
    assert lines[2] == {"create": {}}
    assert [lines[1]["message"], lines[3]["message"]] == ["first", "second"]


def test_a_document_carries_what_the_query_side_sorts_and_filters_on(exporter):
    """Reading logs back depends on these fields being written flat."""
    document = export_lines(exporter, make_record(1_700_000_000, "hello"))[1]

    assert document["timestamp_nanos"] == 1_700_000_000
    assert document["severity_number"] == 17
    assert document["message"] == "hello"
    assert document["zenml.log.id"] == "log-id"
    assert document["@timestamp"] == "1970-01-01T00:00:01.700000+00:00"


def test_sequence_numbers_order_entries_within_a_nanosecond(exporter):
    """A timestamp alone cannot order two entries written at the same instant."""
    lines = export_lines(
        exporter, make_record(1, "first"), make_record(1, "second")
    )

    assert lines[1]["sequence_number"] < lines[3]["sequence_number"]


def test_sequence_numbers_keep_counting_across_batches(exporter):
    """Batches are exported one after another, and so is a log stream."""
    first = export_lines(exporter, make_record(1, "first"))
    second = export_lines(exporter, make_record(1, "second"))

    assert first[1]["sequence_number"] < second[1]["sequence_number"]
