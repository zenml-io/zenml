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
from typing import TYPE_CHECKING, Any, Optional

from zenml.logger import add_zenml_filters, get_logger, get_logging_level

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.sdk.resources import Resource

logger = get_logger(__name__)

_otel_configured = False
_otel_log_handler: Optional[logging.Handler] = None
_otel_providers: list[Any] = []
# ^^^list of OTel providers: logger, tracer, meter


def configure_otel(app: "FastAPI") -> None:
    """Set up OpenTelemetry tracing, metrics, and log export.

    Reads OTel settings from ``ServerConfiguration`` (which in turn reads
    ``ZENML_SERVER_OTEL_*`` environment variables).  If the OTLP endpoint
    is not configured the function returns immediately so the server runs
    without OTel overhead.

    Args:
        app: The FastAPI application instance to instrument.
    """
    global _otel_configured

    from zenml.zen_server.utils import server_config

    if _otel_configured:
        logger.debug("OpenTelemetry instrumentation already configured.")
        return

    config = server_config()

    # If the endpoint is not configured, then return early.
    endpoint = config.otel_exporter_otlp_endpoint
    if not endpoint:
        return

    # If all the signals are disabled, then return early.
    signals_enabled = any(
        [
            config.otel_traces_enabled,
            config.otel_metrics_enabled,
            config.otel_logs_enabled,
        ]
    )
    if not signals_enabled:
        return

    try:
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": config.otel_service_name})
    except ImportError:
        logger.debug(
            "OpenTelemetry SDK packages not installed — skipping "
            "instrumentation.  Install the [otel] extra to enable."
        )
        return

    traces_configured = _configure_traces(
        endpoint=endpoint,
        resource=resource,
        enabled=config.otel_traces_enabled,
    )
    metrics_configured = _configure_metrics(
        endpoint=endpoint,
        resource=resource,
        enabled=config.otel_metrics_enabled,
    )
    logs_configured = _configure_logs(
        endpoint=endpoint,
        resource=resource,
        enabled=config.otel_logs_enabled,
    )

    # If all the signals were enabled but none of the exports were configured, then warn.
    if not any([traces_configured, metrics_configured, logs_configured]):
        logger.warning(
            "OpenTelemetry endpoint is configured, but no telemetry signals "
            "could be initialized. Install the [otel] extra to enable."
        )
        return

    _instrument_libraries(app=app)
    _otel_configured = True

    logger.info(
        "OpenTelemetry instrumentation enabled — exporting to %s", endpoint
    )


def shutdown_otel() -> None:
    """Flush and shut down OpenTelemetry providers configured by ZenML."""
    global _otel_configured, _otel_log_handler

    if not _otel_configured and not _otel_log_handler and not _otel_providers:
        return

    if _otel_log_handler:
        root_logger = logging.getLogger()
        root_logger.removeHandler(_otel_log_handler)
        _otel_log_handler.close()
        _otel_log_handler = None

    while _otel_providers:
        provider = _otel_providers.pop()
        try:
            provider.shutdown()
        except Exception:
            logger.exception(
                "Failed to shut down OpenTelemetry provider cleanly."
            )

    _otel_configured = False


def _configure_traces(
    endpoint: str, resource: "Resource", enabled: bool
) -> bool:
    """Configure OpenTelemetry trace export.

    Args:
        endpoint: Base OTLP endpoint.
        resource: Resource attributes shared by all telemetry signals.
        enabled: Whether trace export is enabled.

    Returns:
        True if trace export was configured, otherwise False.
    """
    if not enabled:
        logger.debug("OpenTelemetry trace export is disabled.")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
            )
        )
        trace.set_tracer_provider(tracer_provider)
        _otel_providers.append(tracer_provider)
        return True
    except Exception:
        logger.exception("Failed to configure OpenTelemetry trace export.")
        return False


def _configure_metrics(
    endpoint: str, resource: "Resource", enabled: bool
) -> bool:
    """Configure OpenTelemetry metric export.

    Args:
        endpoint: Base OTLP endpoint.
        resource: Resource attributes shared by all telemetry signals.
        enabled: Whether metric export is enabled.

    Returns:
        True if metric export was configured, otherwise False.
    """
    if not enabled:
        logger.debug("OpenTelemetry metric export is disabled.")
        return False

    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            PeriodicExportingMetricReader,
        )

        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
        )
        meter_provider = MeterProvider(
            resource=resource, metric_readers=[reader]
        )
        metrics.set_meter_provider(meter_provider)
        _otel_providers.append(meter_provider)
        return True
    except Exception:
        logger.exception("Failed to configure OpenTelemetry metric export.")
        return False


def _configure_logs(
    endpoint: str,
    resource: "Resource",
    enabled: bool,
) -> bool:
    """Configure OpenTelemetry log export.

    Args:
        endpoint: Base OTLP endpoint.
        resource: Resource attributes shared by all telemetry signals.
        enabled: Whether log export is enabled.

    Returns:
        True if log export was configured, otherwise False.
    """
    global _otel_log_handler

    if not enabled:
        logger.debug("OpenTelemetry log export is disabled.")
        return False

    try:
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

        otel_handler = LoggingHandler(
            level=get_logging_level().value,
            logger_provider=logger_provider,
        )
        # Attach the ZenML filters that add structlog contextvars
        # and step name to the log record to the OTel handler.
        otel_handler = add_zenml_filters(otel_handler)  # type: ignore[assignment]

        # Attach the OTel handler to the root logger.
        # init_logging() attaches ZenML's console and log-storage handlers to
        # the root logger, and server startup configures uvicorn to propagate
        # there too. Attach OTel to the same logger so one logging pipeline
        # exports ZenML, uvicorn, and third-party records with the same filters.
        root_logger = logging.getLogger()
        root_logger.addHandler(otel_handler)

        # Store the OTel handler so it can be removed on shutdown.
        _otel_log_handler = otel_handler
        _otel_providers.append(logger_provider)
        return True
    except Exception:
        logger.exception("Failed to configure OpenTelemetry log export.")
        return False


def _instrument_libraries(app: "FastAPI") -> None:
    """Instrument supported libraries when their OTel packages are present.

    Args:
        app: The FastAPI application instance to instrument.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        logger.debug(
            "OpenTelemetry FastAPI instrumentation package not installed. "
            "Install `opentelemetry-instrumentation-fastapi`."
        )
        pass

    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except ImportError:
        logger.debug(
            "OpenTelemetry requests instrumentation package not installed. "
            "Install `opentelemetry-instrumentation-requests`."
        )
        pass

    try:
        from opentelemetry.instrumentation.sqlalchemy import (
            SQLAlchemyInstrumentor,
        )

        from zenml.zen_server.utils import initialize_zen_store, zen_store

        # if the zen store is not initialized, initialize it. Else, use the existing store.
        # The zen-store is initialized during the server startup, but otel is configured
        # before the server starts, during the module-level import. (see zen_server_api.py)
        try:
            store = zen_store()
        except RuntimeError:
            initialize_zen_store()
            store = zen_store()

        SQLAlchemyInstrumentor().instrument(engine=store.engine)
    except ImportError:
        logger.debug(
            "OpenTelemetry SQLAlchemy instrumentation package not installed. "
            "Install `opentelemetry-instrumentation-sqlalchemy`."
        )
        pass
    except Exception:
        logger.exception("Failed to instrument SQLAlchemy with OpenTelemetry.")
