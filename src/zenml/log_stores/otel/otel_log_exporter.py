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
"""OpenTelemetry exporter that writes logs to any OpenTelemetry backend."""

import json
import threading
from collections import defaultdict
from io import BytesIO
from time import time_ns
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence

import requests
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from zenml import __version__ as zenml_version
from zenml.log_stores.otel.otel_flavor import Compression
from zenml.logger import get_logger
from zenml.utils.json_utils import pydantic_encoder

DEFAULT_TIMEOUT = 10

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LogData

logger = get_logger(__name__)


class OTLPLogExporter(LogExporter):
    """OpenTelemetry exporter using JSON protocol.

    This exporter is a placeholder until the actual implementation of the
    OpenTelemetry exporter is available in the opentelemetry-exporter-otlp-proto-json package.
    """

    def __init__(
        self,
        endpoint: str,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        compression: Compression = Compression.NoCompression,
    ):
        """Initialize the exporter.

        Args:
            endpoint: The endpoint to export logs to.
            certificate_file: The certificate file to use for the export.
            client_key_file: The client key file to use for the export.
            client_certificate_file: The client certificate file to use for the export.
            headers: The headers to use for the export.
            timeout: The timeout to use for the export.
            compression: The compression to use for the export.
        """
        self._shutdown_is_occurring = threading.Event()
        self._endpoint = endpoint
        self._certificate_file = certificate_file
        self._client_key_file = client_key_file
        self._client_certificate_file = client_certificate_file
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        self._timeout = timeout
        self._compression = compression
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"zenml/{zenml_version}",
            }
        )
        if headers:
            self._session.headers.update(headers)

        # Retries are triggered on specific HTTP status codes:
        #
        #     408: Request Timeout.
        #     429: Too Many Requests.
        #     502: Bad Gateway.
        #     503: Service Unavailable.
        #     504: Gateway Timeout
        #
        # This also handles connection level errors, if a connection attempt
        # fails due to transient issues like:
        #
        #     DNS resolution errors.
        #     Connection timeouts.
        #     Network disruptions.
        #
        # Additional errors retried:
        #
        #     Read Timeouts: If the server does not send a response within
        #     the timeout period.
        #     Connection Refused: If the server refuses the connection.
        #
        retries = Retry(
            connect=5,
            read=5,
            redirect=3,
            status=5,
            allowed_methods=[
                "POST",
            ],
            status_forcelist=[
                408,  # Request Timeout
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            ],
            other=3,
            backoff_factor=0.5,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        http_adapter = HTTPAdapter(
            max_retries=retries,
            pool_maxsize=1,
        )
        self._session.mount("https://", http_adapter)
        self._session.mount("http://", http_adapter)

        self._shutdown = False

    def _export(
        self, serialized_data: bytes, timeout_sec: float
    ) -> requests.Response:
        """Export a batch of logs to the OpenTelemetry backend.

        Args:
            serialized_data: The serialized data to export.
            timeout_sec: The timeout to use for the export.

        Returns:
            The response from the export.
        """
        data = serialized_data
        if self._compression == Compression.Gzip:
            try:
                import gzip
            except ImportError:
                logger.warning(
                    "gzip module not found, compression not supported"
                )
            else:
                gzip_data = BytesIO()
                with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                    gzip_stream.write(serialized_data)
                data = gzip_data.getvalue()
                self._session.headers.update(
                    {"Content-Encoding": self._compression.value}
                )
        elif self._compression == Compression.Deflate:
            try:
                import zlib
            except ImportError:
                logger.warning(
                    "zlib module not found, compression not supported"
                )
            else:
                data = zlib.compress(serialized_data)
                self._session.headers.update(
                    {"Content-Encoding": self._compression.value}
                )

        resp = self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=timeout_sec,
            cert=self._client_cert,
        )

        return resp

    @classmethod
    def _encode_value(cls, value: Any, allow_null: bool = False) -> Any:
        if allow_null is True and value is None:
            return None
        if isinstance(value, bool):
            return dict(bool_value=value)
        if isinstance(value, str):
            return dict(string_value=value)
        if isinstance(value, int):
            return dict(int_value=value)
        if isinstance(value, float):
            return dict(double_value=value)
        if isinstance(value, bytes):
            return dict(bytes_value=value)
        if isinstance(value, Sequence):
            return dict(
                array_value=dict(
                    values=[
                        cls._encode_value(v, allow_null=allow_null)
                        for v in value
                    ]
                )
            )
        elif isinstance(value, Mapping):
            return dict(
                kvlist_value=dict(
                    values=[
                        {
                            str(k): cls._encode_value(v, allow_null=allow_null)
                            for k, v in value.items()
                        }
                    ]
                )
            )
        raise ValueError(f"Invalid type {type(value)} of value {value}")

    @classmethod
    def _encode_attributes(cls, attributes: Mapping[str, Any]) -> Any:
        return [
            dict(key=k, value=cls._encode_value(v, allow_null=True))
            for k, v in attributes.items()
        ]

    @classmethod
    def _encode_log(cls, log_data: "LogData") -> Dict[str, Any]:
        """Encode a log data object to a dictionary.

        Args:
            log_data: The log data object to encode.

        Returns:
            A dictionary representing the log data.
        """
        span_id = (
            None
            if log_data.log_record.span_id == 0
            else log_data.log_record.span_id
        )
        trace_id = (
            None
            if log_data.log_record.trace_id == 0
            else log_data.log_record.trace_id
        )
        body = log_data.log_record.body
        log_record = dict(
            time_unix_nano=log_data.log_record.timestamp,
            observed_time_unix_nano=time_ns(),
            span_id=span_id,
            trace_id=trace_id,
            flags=int(log_data.log_record.trace_flags),
            body=cls._encode_value(body, allow_null=True),
            severity_text=log_data.log_record.severity_text,
            attributes=cls._encode_attributes(log_data.log_record.attributes)
            if log_data.log_record.attributes
            else None,
            dropped_attributes_count=log_data.log_record.dropped_attributes,
            severity_number=getattr(
                log_data.log_record.severity_number, "value", None
            ),
            event_name=log_data.log_record.event_name,
        )

        return {k: v for k, v in log_record.items() if v is not None}

    def _encode_logs(self, logs: Sequence["LogData"]) -> Any:
        """Encode a sequence of log data objects to a list of dictionaries.

        Args:
            logs: The sequence of log data objects to encode.

        Returns:
            The log data.
        """
        resource_logs: Dict[Any, Dict[Any, List[Any]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for log_data in logs:
            resource = log_data.log_record.resource
            instrumentation = log_data.instrumentation_scope or None
            json_log = self._encode_log(log_data)

            resource_logs[resource][instrumentation].append(json_log)

        json_resource_logs = []

        for resource, instrumentations in resource_logs.items():
            scope_logs = []
            for instrumentation, json_logs in instrumentations.items():
                if isinstance(instrumentation, InstrumentationScope):
                    scope = dict(
                        name=instrumentation.name,
                        version=instrumentation.version,
                        schema_url=instrumentation.schema_url,
                        attributes=self._encode_attributes(
                            instrumentation.attributes
                        )
                        if instrumentation.attributes
                        else None,
                    )
                else:
                    scope = None

                scope_logs.append(
                    dict(
                        scope=scope,
                        log_records=json_logs,
                        schema_url=instrumentation.schema_url
                        if instrumentation
                        else None,
                        attributes=self._encode_attributes(
                            instrumentation.attributes
                        )
                        if instrumentation.attributes
                        else None,
                    )
                )

            json_resource_logs.append(
                dict(
                    resource=dict(
                        attributes=self._encode_attributes(resource.attributes)
                        if resource.attributes
                        else None,
                    ),
                    scope_logs=scope_logs,
                    schema_url=resource.schema_url,
                )
            )

        return dict(resource_logs=json_resource_logs)

    def export(self, batch: Sequence["LogData"]) -> LogExportResult:
        """Export a batch of logs to the OpenTelemetry backend.

        Args:
            batch: The batch of logs to export.

        Returns:
            LogExportResult indicating success or failure.
        """
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return LogExportResult.FAILURE
        encoded_logs = self._encode_logs(batch)

        serialized_data = json.dumps(
            encoded_logs,
            default=pydantic_encoder,
        ).encode("utf-8")

        try:
            resp = self._export(serialized_data, self._timeout)
            if resp.ok:
                return LogExportResult.SUCCESS
            return LogExportResult.FAILURE
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            return LogExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_is_occurring.set()
        self._session.close()
