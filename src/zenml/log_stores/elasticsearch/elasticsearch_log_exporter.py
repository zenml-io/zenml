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

import itertools
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from opentelemetry.sdk._logs import ReadableLogRecord

from zenml.log_stores.elasticsearch.elasticsearch_flavor import (
    MESSAGE_FIELD,
    SEQUENCE_FIELD,
    SEVERITY_NUMBER_FIELD,
    TIMESTAMP_FIELD,
)
from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.logger import get_logger
from zenml.utils.json_utils import pydantic_encoder

logger = get_logger(__name__)

# A data stream only accepts `create`, and a plain index accepts it too with an
# automatically assigned document ID, so one action serves both.
BULK_ACTION: Dict[str, Dict[str, Any]] = {"create": {}}


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

        # Entries written within the same nanosecond are ordered by this
        # counter. A log stream has exactly one writer, so counting per exporter
        # is enough to keep the order of a stream stable.
        self._sequence_numbers = itertools.count()

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
                SEQUENCE_FIELD: next(self._sequence_numbers),
                MESSAGE_FIELD: str(record.body),
                SEVERITY_NUMBER_FIELD: getattr(
                    record.severity_number, "value", None
                ),
                "severity_text": record.severity_text,
                # Kibana and every other Elasticsearch consumer expects a date
                # field; the nanosecond field above only exists to sort on.
                "@timestamp": datetime.fromtimestamp(
                    timestamp / 1_000_000_000, tz=timezone.utc
                ).isoformat(),
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
            lines.append(BULK_ACTION)
            lines.append(self._encode_document(log))

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
