#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

Why programmatic instrumentation instead of auto-instrumentation?

The `opentelemetry-instrument` CLI wrapper does not work reliably with
uvicorn `--reload` — the SDK initializes but traces and logs never reach
the collector (only auto-collected runtime metrics get through).

Programmatic setup avoids this entirely because it runs inside the app
process after the FastAPI instance already exists, so `instrument_app(app)`
targets the real object.

Note the following limitations when using Uvicorn with zero-code auto-instrumentation:

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

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_OTEL_SAFE_TYPES = (type(None), bool, bytes, int, float, str, list, tuple)


class _OTelSanitizeFilter(logging.Filter):
    """Strip non-serializable attributes from LogRecords before OTel export.

    When structlog's ProcessorFormatter processes a log record, it attaches an
    internal _logger attribute (a BoundLoggerFilteringAtLevel wrapper) to the
    LogRecord object. OTel's LoggingHandler then iterates over record.__dict__
    to convert all attributes into OTLP log record attributes, and it only knows
    how to serialize primitives (str, int, float, bool, bytes, list, tuple). When
    it hits the _logger object, it emits a warning like:

    ``Failed to encode attribute _logger of type BoundLoggerFilteringAtLevel``

    This warning fires on every single log record, flooding the logs.
    The filter strips any private (`_`-prefixed) attribute whose value isn't an
    OTel-safe primitive. It doesn't drops log records — it just cleans them before
    OTel sees them.

    Ref:
     - https://github.com/open-telemetry/opentelemetry-python/issues/3649
     - https://github.com/open-telemetry/opentelemetry-python/issues/3370
     - https://github.com/open-telemetry/opentelemetry-python/issues/3389
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Remove non-serializable private attributes from the record.

        Args:
            record: The log record to sanitize.

        Returns:
            Always True — records are never dropped, only cleaned.
        """
        for key in list(record.__dict__):
            if key.startswith("_") and not isinstance(
                record.__dict__[key], _OTEL_SAFE_TYPES
            ):
                del record.__dict__[key]
        return True


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
        from opentelemetry import trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            PeriodicExportingMetricReader,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.debug(
            "OpenTelemetry SDK packages not installed — skipping "
            "instrumentation.  Install the [otel] extra to enable."
        )
        return

    resource = Resource.create({"service.name": config.otel_service_name})

    # --- Traces ---
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ---
    from opentelemetry import metrics

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # --- Logs ---
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=f"{endpoint}/v1/logs")
        )
    )
    set_logger_provider(logger_provider)

    otel_log_level = getattr(
        logging, config.otel_python_log_level.upper(), logging.INFO
    )
    otel_handler = LoggingHandler(
        level=otel_log_level,
        logger_provider=logger_provider,
    )
    otel_handler.addFilter(_OTelSanitizeFilter())
    logging.getLogger().addHandler(otel_handler)

    # Instrumenting FastAPI, Requests, and SQLAlchemy
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

    logger.info(
        "OpenTelemetry instrumentation enabled — exporting to %s", endpoint
    )
