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
"""Tests for custom exporters with the OpenTelemetry logging SDK."""

import json
import logging
from typing import Any, Dict

import pytest
import requests
from opentelemetry._logs import LogRecord
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from pytest_mock import MockerFixture

from zenml.log_stores.datadog.datadog_log_exporter import DatadogLogExporter
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter


@pytest.mark.parametrize(
    "trace_id,span_id",
    [
        (0, 0),
        (1, 2),
        (0x0AF7651916CD43DD8448EB211C80319C, 0xB7AD6B7169203331),
    ],
)
def test_otlp_exports_hex_trace_identifiers(
    trace_id: int, span_id: int, mocker: MockerFixture
) -> None:
    """Encode fixed-width hex IDs, omitting IDs when no trace is present."""
    response = requests.Response()
    response.status_code = 200
    post = mocker.patch("requests.Session.post", return_value=response)
    provider = LoggerProvider()
    provider.add_log_record_processor(
        SimpleLogRecordProcessor(
            OTLPLogExporter(endpoint="http://collector.invalid/v1/logs")
        )
    )
    try:
        provider.get_logger("pipeline").emit(
            LogRecord(
                body="correlated log", trace_id=trace_id, span_id=span_id
            )
        )
        post.assert_called_once()
        payload = json.loads(post.call_args.kwargs["data"])
        record = payload["resource_logs"][0]["scope_logs"][0]["log_records"][0]
        if trace_id:
            assert record["trace_id"] == trace_id.to_bytes(16, "big").hex()
            assert record["span_id"] == span_id.to_bytes(8, "big").hex()
        else:
            assert "trace_id" not in record
            assert "span_id" not in record
    finally:
        provider.shutdown()


@pytest.mark.parametrize(
    "event_attributes",
    [
        {},
        {"otel.event.name": "pipeline.completed"},
        {"event.name": "pipeline.completed"},
        {"otel.event.name": "pipeline.completed", "event.name": "legacy"},
    ],
)
def test_datadog_preserves_event_names(
    event_attributes: Dict[str, str],
    mocker: MockerFixture,
) -> None:
    """Preserve searchable event names after conversion by the SDK handler."""
    response = requests.Response()
    response.status_code = 200
    post = mocker.patch("requests.Session.post", return_value=response)
    provider = LoggerProvider()
    provider.add_log_record_processor(
        SimpleLogRecordProcessor(
            DatadogLogExporter(endpoint="http://collector.invalid/v1/logs")
        )
    )
    handler = LoggingHandler(logger_provider=provider)
    record = logging.LogRecord(
        name="pipeline",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="pipeline log",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(event_attributes)
    try:
        handler.handle(record)
        post.assert_called_once()
        payload = json.loads(post.call_args.kwargs["data"])
        event_name = event_attributes.get(
            "otel.event.name", event_attributes.get("event.name")
        )
        assert payload[0]["message"] == "pipeline log"
        assert payload[0].get("otel.event.name") == event_name
        assert payload[0].get("event.name") == event_name
    finally:
        handler.close()
        provider.shutdown()


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, {}),
        (
            [1, "text", None],
            {
                "array_value": {
                    "values": [
                        {"int_value": "1"},
                        {"string_value": "text"},
                        {},
                    ]
                }
            },
        ),
        (
            [None, [None]],
            {
                "array_value": {
                    "values": [{}, {"array_value": {"values": [{}]}}]
                }
            },
        ),
    ],
)
def test_export_null_values_as_empty_any_values(
    value: Any, expected: Dict[str, Any], mocker: MockerFixture
) -> None:
    """Export nulls and mixed arrays as valid OTLP values without losing slots."""
    json_format = pytest.importorskip("google.protobuf.json_format")
    common = pytest.importorskip("opentelemetry.proto.common.v1.common_pb2")
    response = requests.Response()
    response.status_code = 200
    post = mocker.patch("requests.Session.post", return_value=response)
    provider = LoggerProvider()
    provider.add_log_record_processor(
        SimpleLogRecordProcessor(
            OTLPLogExporter(endpoint="http://collector.invalid/v1/logs")
        )
    )
    try:
        provider.get_logger("pipeline").emit(
            LogRecord(body="pipeline log", attributes={"values": value})
        )
        post.assert_called_once()
        payload = json.loads(post.call_args.kwargs["data"])
        record = payload["resource_logs"][0]["scope_logs"][0]["log_records"][0]
        assert record["body"]["string_value"] == "pipeline log"
        encoded = next(
            item["value"]
            for item in record["attributes"]
            if item["key"] == "values"
        )
        parsed = json_format.ParseDict(encoded, common.AnyValue())
        assert parsed == json_format.ParseDict(expected, common.AnyValue())
    finally:
        provider.shutdown()
