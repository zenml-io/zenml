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

Activates only when a base or per-signal OTLP/HTTP endpoint is configured in
``ServerConfiguration``. Without it the server runs with zero OTel overhead.

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
from typing import TYPE_CHECKING, Any, Callable, Optional

from zenml.logger import add_zenml_filters, get_logger, get_logging_level

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.sdk.resources import Resource

    from zenml.zen_stores.sql_zen_store import SqlZenStore

logger = get_logger(__name__)

_otel_configured = False
_otel_log_handler: Optional[logging.Handler] = None

# list of OTel providers, logger, tracer, meter, to shutdown on server exit.
_otel_providers: list[Any] = []

# list of callbacks to uninstrument the libraries when we shutdown OTel.
_otel_uninstrument_callbacks: list[Callable[[], None]] = []


def configure_otel(app: "FastAPI") -> None:
    """Set up OpenTelemetry tracing, metrics, and log export.

    Reads OTel settings from ``ServerConfiguration`` (which in turn reads
    ``ZENML_SERVER_OTEL_*`` and compatible standard OTel environment
    variables). If no OTLP endpoint is configured the function returns
    immediately so the server runs without OTel overhead.

    Args:
        app: The FastAPI application instance to instrument.
    """
    global _otel_configured

    if _otel_configured:
        logger.debug("OpenTelemetry instrumentation already configured.")
        return

    from zenml import __version__
    from zenml.zen_server.utils import server_config

    config = server_config()

    # If no signal has an effective endpoint, then return early.
    if not any(
        [
            config.otel_exporter_otlp_traces_endpoint,
            config.otel_exporter_otlp_metrics_endpoint,
            config.otel_exporter_otlp_logs_endpoint,
        ]
    ):
        return

    try:
        from opentelemetry.sdk.resources import Resource

        resource_attributes = {
            "service.name": config.otel_service_name,
            "service.version": __version__,
            "deployment.environment.name": str(config.deployment_type),
        }

        resource = Resource.create(attributes=resource_attributes)
    except ImportError:
        logger.debug(
            "OpenTelemetry SDK packages not installed — skipping "
            "instrumentation.  Install the [otel] extra to enable."
        )
        return

    traces_configured = _configure_traces(
        endpoint=config.otel_exporter_otlp_traces_endpoint,
        resource=resource,
    )
    metrics_configured = _configure_metrics(
        endpoint=config.otel_exporter_otlp_metrics_endpoint,
        resource=resource,
    )
    logs_configured = _configure_logs(
        endpoint=config.otel_exporter_otlp_logs_endpoint,
        resource=resource,
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
        "OpenTelemetry instrumentation enabled — exporting to %s",
        config.otel_exporter_otlp_endpoint
        or "configured per-signal OTLP endpoints",
    )


def shutdown_otel() -> None:
    """Flush and shut down OpenTelemetry providers configured by ZenML."""
    global _otel_configured, _otel_log_handler

    # If OTel is not configured, return early.
    if (
        not _otel_configured
        and not _otel_log_handler
        and not _otel_providers
        and not _otel_uninstrument_callbacks
    ):
        return

    # Undo instrumentation in reverse registration order so dependent
    # instrumentation (if any) is removed before the lower-level providers it uses.
    for uninstrument in reversed(_otel_uninstrument_callbacks):
        try:
            uninstrument()
        except Exception:
            logger.exception(
                "Failed to uninstrument OpenTelemetry library cleanly."
            )
    # Empty the list of uninstrument callbacks.
    _otel_uninstrument_callbacks.clear()

    # Remove the OTel log handler from the root logger.
    if _otel_log_handler:
        root_logger = logging.getLogger()
        root_logger.removeHandler(_otel_log_handler)
        _otel_log_handler.close()
        _otel_log_handler = None

    # Shut down the OTel providers.
    for provider in reversed(_otel_providers):
        try:
            provider.shutdown()
        except Exception:
            logger.exception(
                "Failed to shut down OpenTelemetry provider cleanly."
            )
    # Empty the list of OTel providers.
    _otel_providers.clear()

    _otel_configured = False


def _configure_traces(endpoint: Optional[str], resource: "Resource") -> bool:
    """Configure OpenTelemetry trace export.

    Args:
        endpoint: OTLP/HTTP trace endpoint.
        resource: Resource attributes shared by all telemetry signals.

    Returns:
        True if trace export was configured, otherwise False.
    """
    if not endpoint:
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
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(tracer_provider)
        _otel_providers.append(tracer_provider)
        return True
    except Exception:
        logger.exception("Failed to configure OpenTelemetry trace export.")
        return False


def _configure_metrics(endpoint: Optional[str], resource: "Resource") -> bool:
    """Configure OpenTelemetry metric export.

    Args:
        endpoint: OTLP/HTTP metric endpoint.
        resource: Resource attributes shared by all telemetry signals.

    Returns:
        True if metric export was configured, otherwise False.
    """
    if not endpoint:
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
            OTLPMetricExporter(endpoint=endpoint)
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
    endpoint: Optional[str],
    resource: "Resource",
) -> bool:
    """Configure OpenTelemetry log export.

    Args:
        endpoint: OTLP/HTTP log endpoint.
        resource: Resource attributes shared by all telemetry signals.

    Returns:
        True if log export was configured, otherwise False.
    """
    global _otel_log_handler

    if not endpoint:
        logger.debug("OpenTelemetry log export is disabled.")
        return False

    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.instrumentation.logging.handler import (
            LoggingHandler,
        )
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
        )
        set_logger_provider(logger_provider)

        otel_handler = LoggingHandler(
            level=get_logging_level().value,
            logger_provider=logger_provider,
            log_code_attributes=True,
        )
        # Attach the ZenML filters that add structlog contextvars
        # and step name to the log record to the OTel handler.
        add_zenml_filters(otel_handler)

        # Attach the OTel handler to the root logger.
        # init_logging() attaches ZenML's console and log-storage handlers to
        # the root logger, and server startup configures uvicorn to propagate
        # there too. Attach OTel to the same logger so one logging pipeline
        # exports ZenML, uvicorn, and third-party records with the same filters.
        root_logger = logging.getLogger()
        root_logger.addHandler(otel_handler)

        _otel_log_handler = otel_handler
        _otel_providers.append(logger_provider)
        return True
    except Exception:
        logger.exception("Failed to configure OpenTelemetry log export.")
        return False


def instrument_sqlalchemy_store(store: "SqlZenStore") -> None:
    """Instrument the initialized server SQL store with OpenTelemetry.

    Args:
        store: The SQL Zen store used by the server.
    """
    if not _otel_configured:
        return

    try:
        from opentelemetry.instrumentation.sqlalchemy import (
            SQLAlchemyInstrumentor,
        )

        sqlalchemy_instrumentor = SQLAlchemyInstrumentor()
        sqlalchemy_instrumentor.instrument(engine=store.engine)
        _otel_uninstrument_callbacks.append(
            sqlalchemy_instrumentor.uninstrument
        )
    except ImportError:
        logger.debug(
            "OpenTelemetry SQLAlchemy instrumentation package not installed. "
            "Install `opentelemetry-instrumentation-sqlalchemy`."
        )
    except Exception:
        logger.exception("Failed to instrument SQLAlchemy with OpenTelemetry.")


def _instrument_libraries(app: "FastAPI") -> None:
    """Instrument supported libraries when their OTel packages are present.

    Args:
        app: The FastAPI application instance to instrument.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # Exclude low-level ASGI send/receive event spans; the main request
        # span is enough for normal API tracing, and these add noise.
        # Ref: https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html#request-response-hooks
        FastAPIInstrumentor.instrument_app(
            app,
            exclude_spans=["send", "receive"],
        )
        _otel_uninstrument_callbacks.append(
            lambda: FastAPIInstrumentor.uninstrument_app(app)
        )
    except ImportError:
        logger.debug(
            "OpenTelemetry FastAPI instrumentation package not installed. "
            "Install `opentelemetry-instrumentation-fastapi`."
        )

    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        requests_instrumentor = RequestsInstrumentor()
        requests_instrumentor.instrument()
        _otel_uninstrument_callbacks.append(requests_instrumentor.uninstrument)
    except ImportError:
        logger.debug(
            "OpenTelemetry requests instrumentation package not installed. "
            "Install `opentelemetry-instrumentation-requests`."
        )
