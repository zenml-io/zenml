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
"""OpenTelemetry instrumentation for the ZenML server.

Activates only when ``otel_exporter_otlp_endpoint`` is configured in
``ServerConfiguration`` (env: ``ZENML_SERVER_OTEL_EXPORTER_OTLP_ENDPOINT``).
Without it the server runs with zero OTel overhead.

We are not doing OTel's auto-instrumentation because it is incompatible with
uvicorn's `--reload` mode. So we are using programmatic instrumentation instead.

More details:

* `--reload` mode is incompatible: Uvicorn's `--reload` development mode spawns child processes in a way that breaks
       auto-instrumentation. For development, you may need to disable `--reload` or use manual instrumentation.

* Multiple workers (`--workers N`) is incompatible: Similar to `--reload`, running Uvicorn with multiple workers in production
       via the `--workers` flag also causes issues with the auto-instrumentation agent.

Ref:
 - https://oneuptime.com/blog/post/2026-02-06-troubleshoot-fastapi-uvicorn-reload/view
 - https://github.com/open-telemetry/opentelemetry-python-contrib/issues/385

"""

import logging
from typing import TYPE_CHECKING

from zenml.logger import add_zenml_filters, get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.sdk.resources import Resource

logger = get_logger(__name__)


def configure_otel(app: "FastAPI") -> None:
    """Set up OpenTelemetry tracing, metrics, and log export.

    Reads OTel settings from ``ServerConfiguration`` (which in turn reads
    ``ZENML_SERVER_OTEL_*`` environment variables).  If the OTLP endpoint
    is not configured the function returns immediately so the server runs
    without OTel overhead.

    Args:
        app: The FastAPI application instance to instrument.
    """
    from zenml.zen_server.utils import server_config

    config = server_config()
    endpoint = config.otel_exporter_otlp_endpoint
    if not endpoint:
        return

    try:
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": config.otel_service_name})

        _configure_traces(endpoint=endpoint, resource=resource)
        _configure_metrics(endpoint=endpoint, resource=resource)
        _configure_logs(
            endpoint=endpoint,
            resource=resource,
            log_level=config.otel_python_log_level,
        )
    except ImportError:
        logger.debug(
            "OpenTelemetry SDK packages not installed — skipping "
            "instrumentation.  Install the [otel] extra to enable."
        )
        return

    _instrument_libraries(app=app)

    logger.info(
        "OpenTelemetry instrumentation enabled — exporting to %s", endpoint
    )


def _configure_traces(endpoint: str, resource: "Resource") -> None:
    """Configure OpenTelemetry trace export.

    Args:
        endpoint: Base OTLP endpoint.
        resource: Resource attributes shared by all telemetry signals.
    """
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)


def _configure_metrics(endpoint: str, resource: "Resource") -> None:
    """Configure OpenTelemetry metric export.

    Args:
        endpoint: Base OTLP endpoint.
        resource: Resource attributes shared by all telemetry signals.
    """
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)


def _configure_logs(
    endpoint: str,
    resource: "Resource",
    log_level: str,
) -> None:
    """Configure OpenTelemetry log export.

    Args:
        endpoint: Base OTLP endpoint.
        resource: Resource attributes shared by all telemetry signals.
        log_level: Python logging level name for the OTel handler.
    """
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import (
        OTLPLogExporter,
    )
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=f"{endpoint}/v1/logs")
        )
    )
    set_logger_provider(logger_provider)

    otel_log_level = getattr(logging, log_level.upper(), logging.INFO)
    otel_handler = LoggingHandler(
        level=otel_log_level,
        logger_provider=logger_provider,
    )

    # Attach the ZenML filters that add structlog contextvars
    # and step name to the log record to the OTel handler
    otel_handler = add_zenml_filters(otel_handler)

    # Add the OTel handler to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(otel_handler)


def _instrument_libraries(app: "FastAPI") -> None:
    """Instrument supported libraries when their OTel packages are present.

    Args:
        app: The FastAPI application instance to instrument.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.sqlalchemy import (
            SQLAlchemyInstrumentor,
        )

        SQLAlchemyInstrumentor().instrument()
    except ImportError:
        pass
