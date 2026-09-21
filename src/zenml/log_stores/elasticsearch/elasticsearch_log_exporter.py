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
"""Log exporter that writes logs to Elasticsearch."""

import json
from time import monotonic, sleep
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

import requests
from opentelemetry.sdk._logs import ReadableLogRecord

from zenml.log_stores.elasticsearch.elasticsearch_flavor import (
    EVENT_ID_FIELD,
    MESSAGE_FIELD,
    SEVERITY_NUMBER_FIELD,
    TIMESTAMP_FIELD,
)
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.utils.json_utils import pydantic_encoder
from zenml.utils.time_utils import from_unix_nanos


class ElasticsearchLogExporter(OTLPLogExporter):
    """Elasticsearch log exporter.

    Writes log records to the bulk API as flat documents, in a shape the query
    side can sort and filter without a parser at read time.
    """

    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the exporter.

        Args:
            headers: The headers to use for the export.
            **kwargs: Keyword arguments for the base exporter.
        """
        super().__init__(
            headers={
                **(headers or {}),
                "Content-Type": "application/x-ndjson",
            },
            **kwargs,
        )

    def _encode_document(self, readable: ReadableLogRecord) -> Dict[str, Any]:
        """Encode a readable log record as an Elasticsearch document.

        Args:
            readable: SDK readable log record from the batch processor.

        Returns:
            The document.
        """
        record = readable.log_record
        attributes = dict(record.attributes) if record.attributes else {}

        if readable.resource.attributes:
            attributes.update(dict(readable.resource.attributes))

        scope = readable.instrumentation_scope
        if scope and scope.attributes:
            attributes.update(dict(scope.attributes))

        timestamp = record.timestamp or 0
        document: Dict[str, Any] = dict(attributes)
        document.update(
            {
                TIMESTAMP_FIELD: timestamp,
                EVENT_ID_FIELD: str(uuid4()),
                MESSAGE_FIELD: str(record.body),
                SEVERITY_NUMBER_FIELD: record.severity_number.value
                if record.severity_number is not None
                else None,
                "severity_text": record.severity_text,
                "@timestamp": from_unix_nanos(timestamp).isoformat(),
            }
        )

        return {k: v for k, v in document.items() if v is not None}

    def _encode_logs(self, logs: Sequence[ReadableLogRecord]) -> List[Any]:
        """Encode log records as the action and document lines of a bulk request.

        Args:
            logs: Readable log records from the batch processor.

        Returns:
            The lines of the bulk request, in order.
        """
        lines: List[Any] = []
        for log in logs:
            document = self._encode_document(log)
            lines.append({"create": {"_id": document[EVENT_ID_FIELD]}})
            lines.append(document)

        return lines

    def _serialize(self, encoded_logs: Any) -> bytes:
        """Serialize bulk request lines into newline-delimited JSON.

        Args:
            encoded_logs: The lines of the bulk request.

        Returns:
            The request body, which the bulk API requires to end in a newline.
        """
        body = "".join(
            f"{json.dumps(line, default=pydantic_encoder)}\n"
            for line in encoded_logs
        )

        return body.encode("utf-8")

    def _export(
        self, serialized_data: bytes, timeout_sec: float
    ) -> requests.Response:
        """Export a batch, retrying transient item failures up to three attempts.

        Args:
            serialized_data: The serialized bulk request.
            timeout_sec: The request timeout in seconds.

        Returns:
            The HTTP response.

        Raises:
            ValueError: If the request fails or returns failed writes
                or invalid bulk results.
        """
        lines = serialized_data.splitlines(keepends=True)
        pending = [b"".join(lines[i : i + 2]) for i in range(0, len(lines), 2)]
        deadline = monotonic() + timeout_sec
        permanent_failure = False
        for attempt in range(3):
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            response = super()._export(b"".join(pending), remaining)
            if not 200 <= response.status_code < 300:
                raise ValueError(
                    f"Elasticsearch rejected the bulk export with status "
                    f"{response.status_code}."
                )
            try:
                payload = response.json()
            except ValueError as e:
                raise ValueError(
                    "Elasticsearch returned an invalid bulk result."
                ) from e
            if (
                not isinstance(payload, dict)
                or type(payload.get("errors")) is not bool
            ):
                raise ValueError(
                    "Elasticsearch returned an invalid bulk result."
                )
            items = payload.get("items")
            if not isinstance(items, list) or len(items) != len(pending):
                raise ValueError(
                    "Elasticsearch returned an incomplete bulk result."
                )
            retry = []
            for document, item in zip(pending, items):
                result = item.get("create") if isinstance(item, dict) else None
                if (
                    not isinstance(result, dict)
                    or type(result.get("status")) is not int
                ):
                    raise ValueError(
                        "Elasticsearch returned an invalid bulk result."
                    )
                status = result["status"]
                # IDs are generated once, so a create conflict after an uncertain
                # HTTP retry means the same record was already written.
                if status == 409 or (
                    200 <= status < 300 and not result.get("error")
                ):
                    continue
                if status == 429 or 500 <= status < 600:
                    retry.append(document)
                else:
                    permanent_failure = True
            if not retry:
                if permanent_failure:
                    break
                return response
            pending = retry
            if attempt < 2:
                delay = 0.25 * 2**attempt
                if monotonic() + delay >= deadline:
                    break
                sleep(delay)
        raise ValueError(
            "Elasticsearch failed to export one or more log entries."
        )
