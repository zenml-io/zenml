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
"""Realtime runtime with simple in-memory caching and async updates.

This implementation prioritizes in-memory loads when available and otherwise
delegates to the default runtime persistence. It lays groundwork for future
write-behind persistence without changing current behavior.
"""

import os
import queue
import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type

from zenml.execution.step_runtime import DefaultStepRuntime
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.models import ArtifactVersionResponse
from zenml.orchestrators import publish_utils
from zenml.stack.stack import Stack
from zenml.steps.utils import OutputSignature

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.metadata.metadata_types import MetadataType


class RealtimeStepRuntime(DefaultStepRuntime):
    """Realtime runtime optimized for low-latency loads via memory cache.

    TODO(beta->prod): scale background publishing either by
    - adding a small multi-worker thread pool (ThreadPoolExecutor), or
    - migrating to an asyncio-based runtime once the client/publish calls have
      async variants and we want an async mode in serving.
    Both paths must keep bounded backpressure and orderly shutdown.
    """

    def __init__(
        self,
        ttl_seconds: Optional[int] = None,
        max_entries: Optional[int] = None,
    ) -> None:
        """Initialize the realtime runtime.

        Args:
            ttl_seconds: The TTL in seconds.
            max_entries: The maximum number of entries in the cache.
        """
        super().__init__()
        # Simple LRU cache with TTL
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        # Event queue: (kind, args, kwargs)
        Event = Tuple[str, Tuple[Any, ...], Dict[str, Any]]
        self._q: queue.Queue[Event] = queue.Queue(maxsize=1024)
        # TODO(beta->prod): when scaling per-process publishing, prefer either
        # (1) a small thread pool consuming this queue, or (2) an asyncio loop
        # with an asyncio.Queue and async workers, once the client has async
        # publish calls and we opt into async serving.
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._errors_since_last_flush: int = 0
        self._total_errors: int = 0
        self._last_error: Optional[BaseException] = None
        self._error_reported: bool = False
        self._last_report_ts: float = 0.0
        self._logger = get_logger(__name__)
        self._queued_count: int = 0
        self._processed_count: int = 0
        # Metrics: cache and op latencies
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._op_latencies: List[float] = []
        # TODO(beta->prod): add process memory monitoring and expose worker
        # liveness/health at the service layer.
        # Tunables via env: TTL seconds and max entries
        # Options precedence: explicit args > env > defaults
        if ttl_seconds is not None:
            self._ttl_seconds = int(ttl_seconds)
        else:
            try:
                self._ttl_seconds = int(
                    os.getenv("ZENML_RT_CACHE_TTL_SECONDS", "60")
                )
            except Exception:
                self._ttl_seconds = 60
        if max_entries is not None:
            self._max_entries = int(max_entries)
        else:
            try:
                self._max_entries = int(
                    os.getenv("ZENML_RT_CACHE_MAX_ENTRIES", "256")
                )
            except Exception:
                self._max_entries = 256
        # Circuit breaker controls
        try:
            self._cb_threshold = float(
                os.getenv("ZENML_RT_CB_ERR_THRESHOLD", "0.1")
            )
            self._cb_min_events = int(
                os.getenv("ZENML_RT_CB_MIN_EVENTS", "100")
            )
            self._cb_open_seconds = float(
                os.getenv("ZENML_RT_CB_OPEN_SECONDS", "300")
            )
        except Exception:
            self._cb_threshold = 0.1
            self._cb_min_events = 100
            self._cb_open_seconds = 300.0
        self._cb_errors_window: int = 0
        self._cb_total_window: int = 0
        self._cb_open_until_ts: float = 0.0
        # Error report interval (seconds)
        try:
            self._err_report_interval = float(
                os.getenv("ZENML_RT_ERR_REPORT_INTERVAL", "15")
            )
        except Exception:
            self._err_report_interval = 15.0
        # Serving is async by default (non-blocking)
        self._flush_on_step_end: bool = False

    # --- lifecycle ---
    def start(self) -> None:
        """Start the realtime runtime."""
        if self._worker is not None:
            return

        def _run() -> None:
            idle_sleep = 0.05
            while not self._stop.is_set():
                try:
                    kind, args, kwargs = self._q.get(timeout=idle_sleep)
                except queue.Empty:
                    # Opportunistic cache sweep: evict expired from head
                    self._sweep_expired()
                    idle_sleep = min(idle_sleep * 2.0, 2.0)
                    continue
                try:
                    start = time.time()
                    if kind == "pipeline_metadata":
                        publish_utils.publish_pipeline_run_metadata(
                            *args, **kwargs
                        )
                    elif kind == "step_metadata":
                        publish_utils.publish_step_run_metadata(
                            *args, **kwargs
                        )
                    elif kind == "step_success":
                        publish_utils.publish_successful_step_run(
                            *args, **kwargs
                        )
                    elif kind == "step_failed":
                        publish_utils.publish_failed_step_run(*args, **kwargs)
                except BaseException as e:  # noqa: BLE001
                    with self._lock:
                        self._errors_since_last_flush += 1
                        self._total_errors += 1
                        self._last_error = e
                    self._logger.warning(
                        "Realtime runtime failed to publish '%s': %s", kind, e
                    )
                finally:
                    with self._lock:
                        self._processed_count += 1
                        # Update circuit breaker window
                        self._cb_total_window += 1
                        if self._last_error is not None:
                            self._cb_errors_window += 1
                        # Record latency (bounded sample)
                        try:
                            self._op_latencies.append(
                                max(0.0, time.time() - start)
                            )
                            if len(self._op_latencies) > 512:
                                self._op_latencies = self._op_latencies[-256:]
                        except Exception:
                            pass
                    self._q.task_done()
                    idle_sleep = 0.01

        self._worker = threading.Thread(
            target=_run, name="zenml-realtime-runtime", daemon=True
        )
        self._worker.start()

    def on_step_start(self) -> None:
        """Optional hook when a step begins execution."""
        # no-op for now
        return

    # Prefer in-memory values if available
    def load_input_artifact(
        self,
        *,
        artifact: ArtifactVersionResponse,
        data_type: Type[Any],
        stack: "Stack",
    ) -> Any:
        """Load an input artifact.

        Args:
            artifact: The artifact to load.
            data_type: The data type of the artifact.
            stack: The stack of the artifact.

        Returns:
            The loaded artifact.
        """
        key = str(artifact.id)
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache.get(key, (None, 0))
                now = time.time()
                if now <= expires_at:
                    # Touch entry for LRU
                    self._cache.move_to_end(key)
                    self._cache_hits += 1
                    return value
                else:
                    # Expired
                    try:
                        del self._cache[key]
                    except KeyError:
                        pass
            self._cache_misses += 1

        # Fallback to default loading
        return super().load_input_artifact(
            artifact=artifact, data_type=data_type, stack=stack
        )

    # Store synchronously (behavior parity), and cache the raw values in memory
    def store_output_artifacts(
        self,
        *,
        output_data: Dict[str, Any],
        output_materializers: Dict[str, Tuple[Type["BaseMaterializer"], ...]],
        output_artifact_uris: Dict[str, str],
        output_annotations: Dict[str, "OutputSignature"],
        artifact_metadata_enabled: bool,
        artifact_visualization_enabled: bool,
    ) -> Dict[str, ArtifactVersionResponse]:
        """Store output artifacts.

        Args:
            output_data: The output data.
            output_materializers: The output materializers.
            output_artifact_uris: The output artifact URIs.
            output_annotations: The output annotations.
            artifact_metadata_enabled: Whether artifact metadata is enabled.
            artifact_visualization_enabled: Whether artifact visualization is enabled.

        Returns:
            The stored artifacts.
        """
        responses = super().store_output_artifacts(
            output_data=output_data,
            output_materializers=output_materializers,
            output_artifact_uris=output_artifact_uris,
            output_annotations=output_annotations,
            artifact_metadata_enabled=artifact_metadata_enabled,
            artifact_visualization_enabled=artifact_visualization_enabled,
        )

        # Cache by artifact id for later fast loads with TTL and LRU bounds
        with self._lock:
            now = time.time()
            for name, resp in responses.items():
                if name in output_data:
                    expires_at = now + max(0, self._ttl_seconds)
                    self._cache[str(resp.id)] = (output_data[name], expires_at)
                    # Touch to end (most recently used)
                    self._cache.move_to_end(str(resp.id))
            # Enforce size bound
            while len(self._cache) > max(1, self._max_entries):
                try:
                    self._cache.popitem(last=False)  # Evict LRU
                except KeyError:
                    break

        return responses

    # --- async server updates ---
    def publish_pipeline_run_metadata(
        self,
        *,
        pipeline_run_id: "UUID",
        pipeline_run_metadata: Dict["UUID", Dict[str, "MetadataType"]],
    ) -> None:
        """Publish pipeline run metadata.

        Args:
            pipeline_run_id: The pipeline run ID.
            pipeline_run_metadata: The pipeline run metadata.
        """
        # Inline if circuit open, else enqueue
        if self._should_process_inline():
            publish_utils.publish_pipeline_run_metadata(
                pipeline_run_id=pipeline_run_id,
                pipeline_run_metadata=pipeline_run_metadata,
            )
            return
        self._q.put(
            (
                "pipeline_metadata",
                (),
                {
                    "pipeline_run_id": pipeline_run_id,
                    "pipeline_run_metadata": pipeline_run_metadata,
                },
            )
        )
        with self._lock:
            self._queued_count += 1

    def publish_step_run_metadata(
        self,
        *,
        step_run_id: "UUID",
        step_run_metadata: Dict["UUID", Dict[str, "MetadataType"]],
    ) -> None:
        """Publish step run metadata.

        Args:
            step_run_id: The step run ID.
            step_run_metadata: The step run metadata.
        """
        if self._should_process_inline():
            publish_utils.publish_step_run_metadata(
                step_run_id=step_run_id, step_run_metadata=step_run_metadata
            )
            return
        self._q.put(
            (
                "step_metadata",
                (),
                {
                    "step_run_id": step_run_id,
                    "step_run_metadata": step_run_metadata,
                },
            )
        )
        with self._lock:
            self._queued_count += 1

    def publish_successful_step_run(
        self,
        *,
        step_run_id: "UUID",
        output_artifact_ids: Dict[str, List["UUID"]],
    ) -> None:
        """Publish a successful step run.

        Args:
            step_run_id: The step run ID.
            output_artifact_ids: The output artifact IDs.
        """
        if self._should_process_inline():
            publish_utils.publish_successful_step_run(
                step_run_id=step_run_id,
                output_artifact_ids=output_artifact_ids,
            )
            return
        self._q.put(
            (
                "step_success",
                (),
                {
                    "step_run_id": step_run_id,
                    "output_artifact_ids": output_artifact_ids,
                },
            )
        )
        with self._lock:
            self._queued_count += 1

    def publish_failed_step_run(
        self,
        *,
        step_run_id: "UUID",
    ) -> None:
        """Publish a failed step run.

        Args:
            step_run_id: The step run ID.
        """
        if self._should_process_inline():
            publish_utils.publish_failed_step_run(step_run_id)
            return
        try:
            self._q.put_nowait(
                ("step_failed", (), {"step_run_id": step_run_id})
            )
            with self._lock:
                self._queued_count += 1
        except queue.Full:
            self._logger.debug("Queue full, processing step_failed inline")
            try:
                publish_utils.publish_failed_step_run(step_run_id)
            except Exception as e:
                self._logger.warning("Inline processing failed: %s", e)

    def flush(self) -> None:
        """Flush the realtime runtime by draining queued events synchronously.

        Raises:
            RuntimeError: If background errors were encountered while draining.
        """
        # Drain the queue in the calling thread to avoid waiting on the worker
        while True:
            try:
                kind, args, kwargs = self._q.get_nowait()
            except queue.Empty:
                break
            try:
                if kind == "pipeline_metadata":
                    publish_utils.publish_pipeline_run_metadata(
                        *args, **kwargs
                    )
                elif kind == "step_metadata":
                    publish_utils.publish_step_run_metadata(*args, **kwargs)
                elif kind == "step_success":
                    publish_utils.publish_successful_step_run(*args, **kwargs)
                elif kind == "step_failed":
                    publish_utils.publish_failed_step_run(*args, **kwargs)
            except BaseException as e:  # noqa: BLE001
                with self._lock:
                    self._errors_since_last_flush += 1
                    self._total_errors += 1
                    self._last_error = e
                self._logger.warning(
                    "Realtime runtime flush failed to publish '%s': %s",
                    kind,
                    e,
                )
            finally:
                with self._lock:
                    self._processed_count += 1
                try:
                    self._q.task_done()
                except ValueError:
                    # If task_done called more than put() count due to races, ignore
                    pass
        # Post-flush maintenance
        self._sweep_expired()
        with self._lock:
            if self._errors_since_last_flush:
                count = self._errors_since_last_flush
                last = self._last_error
                self._errors_since_last_flush = 0
                self._error_reported = True
                raise RuntimeError(
                    f"Realtime runtime encountered {count} error(s) while publishing. Last error: {last}"
                )

    def on_step_end(self) -> None:
        """Optional hook when a step ends execution."""
        # no-op for now
        return

    def shutdown(self) -> None:
        """Shutdown the realtime runtime.

        TODO(beta->prod): expose worker liveness/health signals to the service.
        """
        # Wait for remaining tasks and stop
        self.flush()
        self._stop.set()
        # Join worker with timeout
        worker = self._worker
        if worker is not None:
            worker.join(timeout=15.0)
            if worker.is_alive():
                self._logger.warning(
                    "Realtime runtime worker did not terminate gracefully within timeout."
                )
        self._worker = None

    # Flush behavior controls
    def set_flush_on_step_end(self, value: bool) -> None:
        """Set the flush on step end behavior.

        Args:
            value: The value to set.
        """
        self._flush_on_step_end = bool(value)

    def should_flush_on_step_end(self) -> bool:
        """Whether the runtime should flush on step end.

        Returns:
            Whether the runtime should flush on step end.
        """
        return self._flush_on_step_end

    def get_metrics(self) -> Dict[str, Any]:
        """Return runtime metrics snapshot.

        Returns:
            The runtime metrics snapshot.
        """
        # TODO(beta->prod): export to an external sink (e.g., Prometheus) and
        # expand with additional histograms / event counters as needed.
        if bool(getattr(self, "_metrics_disabled", False)):
            return {}
        with self._lock:
            queued = self._queued_count
            processed = self._processed_count
            failed_total = self._total_errors
            ttl_seconds = getattr(self, "_ttl_seconds", None)
            max_entries = getattr(self, "_max_entries", None)
            cache_hits = self._cache_hits
            cache_misses = self._cache_misses
            latencies = list(self._op_latencies)
        try:
            depth = self._q.qsize()
        except Exception:
            depth = 0
        # Compute simple percentiles
        p50 = p95 = p99 = 0.0
        if latencies:
            s = sorted(latencies)
            n = len(s)
            p50 = s[int(0.5 * (n - 1))]
            p95 = s[int(0.95 * (n - 1))]
            p99 = s[int(0.99 * (n - 1))]
        hit_rate = (
            float(cache_hits) / float(cache_hits + cache_misses)
            if (cache_hits + cache_misses) > 0
            else 0.0
        )
        return {
            "queued": queued,
            "processed": processed,
            "failed_total": failed_total,
            "queue_depth": depth,
            "ttl_seconds": ttl_seconds,
            "max_entries": max_entries,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_rate": hit_rate,
            "op_latency_p50_s": p50,
            "op_latency_p95_s": p95,
            "op_latency_p99_s": p99,
        }

    # Surface background errors even when not flushing
    def check_async_errors(self) -> None:
        """Log and mark any background errors on an interval."""
        with self._lock:
            if self._last_error:
                now = time.time()
                if (not self._error_reported) or (
                    now - self._last_report_ts > self._err_report_interval
                ):
                    self._logger.error(
                        "Background realtime runtime error: %s",
                        self._last_error,
                    )
                    self._error_reported = True
                    self._last_report_ts = now

    # --- internal helpers ---
    def _sweep_expired(self) -> None:
        """Remove expired entries using a snapshot within a small time budget."""
        deadline = time.time() + 0.005
        with self._lock:
            snapshot = list(self._cache.items())
        expired: List[str] = []
        now = time.time()
        for key, (_val, expires_at) in snapshot:
            if time.time() > deadline:
                break
            if now > expires_at:
                expired.append(key)
        if expired:
            with self._lock:
                for key in expired:
                    self._cache.pop(key, None)

    def _should_process_inline(self) -> bool:
        """Return True if circuit breaker is open and we should publish inline.

        Returns:
            True if inline processing should be used, False otherwise.
        """
        with self._lock:
            now = time.time()
            if now < self._cb_open_until_ts:
                return True
            total = self._cb_total_window
            errors = self._cb_errors_window
            if total >= self._cb_min_events:
                err_rate = (float(errors) / float(total)) if total > 0 else 0.0
                if err_rate >= self._cb_threshold:
                    self._cb_open_until_ts = now + self._cb_open_seconds
                    self._logger.warning(
                        "Realtime runtime circuit opened for %.0fs due to error rate %.2f",
                        self._cb_open_seconds,
                        err_rate,
                    )
                    return True
            return False
