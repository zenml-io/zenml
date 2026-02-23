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

from typing import TYPE_CHECKING, Any, Dict, Sequence

from zenml.log_stores.otel.otel_log_exporter import OTLPLogExporter
from zenml.logger import get_logger

DEFAULT_TIMEOUT = 10

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData

logger = get_logger(__name__)


class DatadogLogExporter(OTLPLogExporter):
    """Datadog log exporter.

    This exporter writes OpenTelemetry logs to Datadog's HTTP intake API
    with slightly modified log records to adapt to Datadog's format.
    """

    @classmethod
    def _encode_log(cls, log_data: "LogData") -> Dict[str, Any]:
        """Encode a log data object to a dictionary.

        Args:
            log_data: The log data object to encode.

        Returns:
            A dictionary representing the log data.
        """
        body = log_data.log_record.body
        attributes = (
            dict(log_data.log_record.attributes)
            if log_data.log_record.attributes
            else {}
        )

        resource = log_data.log_record.resource
        instrumentation = log_data.instrumentation_scope

        if resource.attributes:
            attributes.update(dict(resource.attributes))

        if instrumentation.attributes:
            attributes.update(dict(instrumentation.attributes))

        log_record = dict(
            **attributes,
            service=attributes.get("service.name"),
            version=attributes.get("service.version"),
            timestamp=int(log_data.log_record.timestamp / 1e6)
            if log_data.log_record.timestamp
            else None,
            message=str(body),
            status=log_data.log_record.severity_text.lower()
            if log_data.log_record.severity_text
            else "info",
            source="zenml",
        )

        return {k: v for k, v in log_record.items() if v is not None}

    def _encode_logs(self, logs: Sequence["LogData"]) -> Any:
        """Encode a sequence of log data objects to a list of dictionaries.

        Args:
            logs: The sequence of log data objects to encode.

        Returns:
            The log data.
        """
        return [self._encode_log(log) for log in logs]
