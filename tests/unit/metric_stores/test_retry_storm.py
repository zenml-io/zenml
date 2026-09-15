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
"""Regression tests for the "retry storm" step-boundary stall.

The bug: when a step finished, the step thread ran a *blocking* flush whose
exporter retried a flaky collector for many minutes, freezing the step (see
``notes/retry_storm_explained.md``). The fix is Option D:

* L1 - the step boundary deregisters its origin *non-blocking*, so the step
  thread never waits on the network (data still ships via the periodic reader
  and the atexit flush).
* L3 - the exporter's retry budget is a hard, collector-independent time bound
  (``total=2`` ceiling, ``respect_retry_after_header=False``), so no single
  ``export()`` can stall for minutes on any thread.

These tests pin both levers against a deliberately flaky collector.
"""

import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Iterator

from opentelemetry.sdk.metrics.export import MetricExportResult, MetricsData

from zenml.metric_stores.otel.otel_metric_exporter import OTLPMetricExporter
from zenml.metric_stores.otel.otel_metric_store import OtelMetricStore

# A blocking flush against a hung/flaky collector used to take minutes. Any
# bound comfortably below "minutes" proves the storm is gone while leaving
# generous slack for slow CI.
BOUNDED_SECONDS = 15.0
# The non-blocking step boundary touches no network at all, so it must return
# effectively instantly even when the collector is a black hole.
INSTANT_SECONDS = 2.0


@contextmanager
def _flaky_collector(
    status: int = 503, sleep_seconds: float = 0.0
) -> Iterator[int]:
    """Run a local OTLP collector that always fails, on an ephemeral port.

    Args:
        status: HTTP status code returned for every POST.
        sleep_seconds: Seconds to stall before responding (simulates a black
            hole / slow collector). 0 responds immediately.

    Yields:
        The port the collector is listening on.
    """

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            if sleep_seconds:
                time.sleep(sleep_seconds)
            self.send_response(status)
            # An aggressive Retry-After the fixed exporter must IGNORE; if it
            # were respected, even two retries would stretch into minutes.
            self.send_header("Retry-After", "30")
            self.end_headers()

        def log_message(self, *args: object) -> None:  # silence test noise
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _build_store(endpoint: str) -> OtelMetricStore:
    """Build an OTel metric store pointed at ``endpoint`` (not yet activated).

    Args:
        endpoint: The OTLP endpoint the store's exporter should target.

    Returns:
        An un-activated ``OtelMetricStore``.
    """
    from zenml.metric_stores.otel.otel_flavor import OtelMetricStoreFlavor

    flavor = OtelMetricStoreFlavor()
    config = flavor.config_class(
        endpoint=endpoint,
        export_interval_seconds=3600,  # never auto-fires during the test
    )
    return flavor.implementation_class(
        name="t",
        id=uuid.uuid4(),
        config=config,
        flavor="otel",
        type=flavor.type,
        user=uuid.uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_exporter_retry_budget_is_collector_independent() -> None:
    """L3: the retry budget caps attempts and ignores the Retry-After header.

    These two settings are what make a single ``export()`` time-bounded
    regardless of how the collector behaves; reverting either reopens the
    storm, so they are pinned explicitly.
    """
    exporter = OTLPMetricExporter(endpoint="http://collector:4318/v1/metrics")
    try:
        retries = exporter._session.get_adapter("http://").max_retries
        assert retries.total == 2
        assert retries.respect_retry_after_header is False
    finally:
        exporter.shutdown()


def test_export_gives_up_quickly_against_flaky_collector() -> None:
    """L3: one export() returns fast even when the collector 503s forever.

    With ``Retry-After: 30`` on every reply, a header-respecting exporter
    would burn minutes here; the bounded budget must give up in seconds.
    """
    with _flaky_collector(status=503) as port:
        exporter = OTLPMetricExporter(
            endpoint=f"http://127.0.0.1:{port}/v1/metrics"
        )
        try:
            start = time.monotonic()
            result = exporter.export(MetricsData(resource_metrics=[]))
            elapsed = time.monotonic() - start
        finally:
            exporter.shutdown()

    assert result == MetricExportResult.FAILURE
    assert elapsed < BOUNDED_SECONDS


def test_step_boundary_does_not_block_on_flaky_collector() -> None:
    """L1: deregistering an origin at step end never waits on the network.

    The collector is a black hole (stalls past the per-request timeout). A
    blocking flush would freeze the "step" here; the non-blocking boundary
    must return instantly and let the periodic reader / atexit ship the data.
    """
    with _flaky_collector(status=503, sleep_seconds=30.0) as port:
        store = _build_store(endpoint=f"http://127.0.0.1:{port}/v1/metrics")
        origin = store.register_origin(name="step-a", metadata={})
        store.record(origin=origin, measurements={"cpu_percent": 1.0})

        start = time.monotonic()
        store.deregister_origin(origin, blocking=False)
        elapsed = time.monotonic() - start

    # Tear down after the black-hole server is gone, so the provider's final
    # flush hits a closed port (connection refused, fast) rather than the
    # stalling handler.
    store.cleanup()

    assert elapsed < INSTANT_SECONDS
