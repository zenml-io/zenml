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
"""OpenTelemetry exporter that writes metrics to any OpenTelemetry backend.

Hand-rolls an OTLP/JSON-over-HTTP exporter using ``requests`` so the
base package does not need ``opentelemetry-exporter-otlp-proto-http``.
The official ``OTLPMetricExporter`` from that package is stable and is
a reasonable drop-in replacement for environments that already pull in
the proto exporter.
"""

import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence

import requests
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
)
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from zenml import __version__ as zenml_version
from zenml.logger import get_logger
from zenml.utils.json_utils import pydantic_encoder

DEFAULT_TIMEOUT = 10

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics.export import MetricsData

logger = get_logger(__name__)


class OTLPMetricExporter(MetricExporter):
    """OpenTelemetry metric exporter using the OTLP/JSON protocol.

    The encoding intentionally follows the snake_case shape used by
    ``OTLPLogExporter`` (the OTLP/HTTP JSON receiver parses it leniently),
    so the two exporters stay structurally identical and easy to review
    side by side.
    """

    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the exporter.

        Args:
            endpoint: The OTLP HTTP endpoint to export metrics to.
            headers: Optional headers to attach to every export request.
            timeout: Per-request network timeout in seconds.
        """
        # A synchronous gauge has a single (cumulative-agnostic) value per
        # attribute set, so temporality does not change semantics here; we
        # declare CUMULATIVE because that is what collectors expect by
        # default for the gauge data we emit.
        super().__init__(
            preferred_temporality={},
            preferred_aggregation={},
        )
        self._endpoint = endpoint
        self._timeout = timeout
        self._shutdown = False
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

        # Retry transient failures (connection-level errors + standard
        # retryable status codes) so a flaky collector does not drop a
        # step's metrics on the floor.
        retries = Retry(
            connect=5,
            read=5,
            redirect=3,
            status=5,
            allowed_methods=["POST"],
            status_forcelist=[408, 429, 500, 502, 503, 504],
            other=3,
            backoff_factor=0.5,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        http_adapter = HTTPAdapter(max_retries=retries, pool_maxsize=1)
        self._session.mount("https://", http_adapter)
        self._session.mount("http://", http_adapter)

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
    def _encode_data_point(cls, point: Any) -> Dict[str, Any]:
        encoded = dict(
            attributes=cls._encode_attributes(point.attributes)
            if point.attributes
            else None,
            start_time_unix_nano=getattr(point, "start_time_unix_nano", None),
            time_unix_nano=point.time_unix_nano,
            as_double=float(point.value),
        )
        return {k: v for k, v in encoded.items() if v is not None}

    @classmethod
    def _encode_metric(cls, metric: Any) -> Dict[str, Any]:
        data_points = [
            cls._encode_data_point(p) for p in metric.data.data_points
        ]
        encoded = dict(
            name=metric.name,
            description=metric.description or None,
            unit=metric.unit or None,
            gauge=dict(data_points=data_points),
        )
        return {k: v for k, v in encoded.items() if v is not None}

    def _encode_metrics(self, metrics_data: "MetricsData") -> Dict[str, Any]:
        """Encode SDK ``MetricsData`` into the OTLP/JSON request body.

        Args:
            metrics_data: The metrics data handed in by the SDK reader.

        Returns:
            A JSON-serializable OTLP ``resource_metrics`` envelope.
        """
        json_resource_metrics = []

        for resource_metrics in metrics_data.resource_metrics:
            resource = resource_metrics.resource
            scope_buckets: Dict[Any, List[Any]] = defaultdict(list)

            for scope_metrics in resource_metrics.scope_metrics:
                scope = scope_metrics.scope
                for metric in scope_metrics.metrics:
                    scope_buckets[scope].append(self._encode_metric(metric))

            scope_metrics_json = []
            for scope, json_metrics in scope_buckets.items():
                if isinstance(scope, InstrumentationScope):
                    scope_json = dict(
                        name=scope.name,
                        version=scope.version,
                        schema_url=scope.schema_url,
                    )
                else:
                    scope_json = None
                scope_metrics_json.append(
                    {
                        k: v
                        for k, v in dict(
                            scope=scope_json,
                            metrics=json_metrics,
                            schema_url=scope.schema_url if scope else None,
                        ).items()
                        if v is not None
                    }
                )

            json_resource_metrics.append(
                dict(
                    resource=dict(
                        attributes=self._encode_attributes(resource.attributes)
                        if resource.attributes
                        else None,
                    ),
                    scope_metrics=scope_metrics_json,
                    schema_url=resource.schema_url,
                )
            )

        return dict(resource_metrics=json_resource_metrics)

    def export(
        self,
        metrics_data: "MetricsData",
        timeout_millis: float = 10_000,
        **kwargs: Any,
    ) -> MetricExportResult:
        """Export a batch of metrics to the OpenTelemetry backend.

        Args:
            metrics_data: The metrics data to export.
            timeout_millis: Export timeout in milliseconds (unused; the
                request timeout is fixed at construction time to match
                ``OTLPLogExporter``).
            **kwargs: Ignored; present for SDK signature compatibility.

        Returns:
            ``MetricExportResult`` indicating success or failure.
        """
        if self._shutdown:
            logger.warning("Metric exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE

        try:
            serialized_data = json.dumps(
                self._encode_metrics(metrics_data),
                default=pydantic_encoder,
            ).encode("utf-8")
            resp = self._session.post(
                url=self._endpoint,
                data=serialized_data,
                timeout=self._timeout,
            )
            if resp.ok:
                return MetricExportResult.SUCCESS
            logger.warning(
                f"Metric export failed with status {resp.status_code}"
            )
            return MetricExportResult.FAILURE
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return MetricExportResult.FAILURE

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Force flush the exporter.

        There is no internal buffer in this exporter (the SDK reader owns
        batching), so this is a no-op that always succeeds.

        Args:
            timeout_millis: Unused; present for SDK signature compatibility.

        Returns:
            Always True.
        """
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs: Any) -> None:
        """Shutdown the exporter and release the HTTP session.

        Args:
            timeout_millis: Unused; present for SDK signature compatibility.
            **kwargs: Ignored; present for SDK signature compatibility.
        """
        if self._shutdown:
            return
        self._shutdown = True
        self._session.close()
