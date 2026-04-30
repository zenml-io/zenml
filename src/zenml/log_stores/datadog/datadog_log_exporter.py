#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Log exporter that writes logs to Datadog."""

from typing import Any, Dict, Sequence

from opentelemetry.sdk._logs import ReadableLogRecord

from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.logger import get_logger

DEFAULT_TIMEOUT = 10

logger = get_logger(__name__)


class DatadogLogExporter(OTLPLogExporter):
    """Datadog log exporter.

    This exporter writes OpenTelemetry logs to Datadog's HTTP intake API
    with slightly modified log records to adapt to Datadog's format.
    """

    @classmethod
    def _encode_log(cls, readable: ReadableLogRecord) -> Dict[str, Any]:
        """Encode a readable log record to a dictionary.

        Args:
            readable: SDK readable log record from the batch processor.

        Returns:
            A dictionary representing the log data.
        """
        lr = readable.log_record
        body = lr.body
        attributes = dict(lr.attributes) if lr.attributes else {}

        resource = readable.resource
        instrumentation = readable.instrumentation_scope

        if resource.attributes:
            attributes.update(dict(resource.attributes))

        if instrumentation and instrumentation.attributes:
            attributes.update(dict(instrumentation.attributes))

        log_record = dict(
            **attributes,
            service=attributes.get("service.name"),
            version=attributes.get("service.version"),
            timestamp=int(lr.timestamp / 1e6) if lr.timestamp else None,
            message=str(body),
            status=lr.severity_text.lower() if lr.severity_text else "info",
            source="zenml",
        )

        return {k: v for k, v in log_record.items() if v is not None}

    def _encode_logs(self, logs: Sequence[ReadableLogRecord]) -> Any:
        """Encode a sequence of readable log records to a list of dictionaries.

        Args:
            logs: Readable log records from the batch processor.

        Returns:
            The log data.
        """
        return [self._encode_log(log) for log in logs]
