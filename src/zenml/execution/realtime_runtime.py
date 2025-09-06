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
    """Realtime runtime optimized for low-latency loads via memory cache."""

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
        self._cache: "OrderedDict[str, Tuple[Any, float]]" = OrderedDict()
        self._lock = threading.RLock()
        # Event queue: (kind, args, kwargs)
        Event = Tuple[str, Tuple[Any, ...], Dict[str, Any]]
        self._q: "queue.Queue[Event]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._errors_since_last_flush: int = 0
        self._total_errors: int = 0
        self._last_error: Optional[BaseException] = None
        self._logger = get_logger(__name__)
        self._queued_count: int = 0
        self._processed_count: int = 0
        # Tunables via env: TTL seconds and max entries
        # Options precedence: explicit args > env > defaults
        if ttl_seconds is not None:
            self._ttl_seconds = int(ttl_seconds)
        else:
            try:
                self._ttl_seconds = int(
                    os.getenv("ZENML_RT_CACHE_TTL_SECONDS", "300")
                )
            except Exception:
                self._ttl_seconds = 300
        if max_entries is not None:
            self._max_entries = int(max_entries)
        else:
            try:
                self._max_entries = int(
                    os.getenv("ZENML_RT_CACHE_MAX_ENTRIES", "1024")
                )
            except Exception:
                self._max_entries = 1024
        # Flush behavior (can be disabled for serving non-blocking)
        self._flush_on_step_end: bool = True

    # --- lifecycle ---
    def start(self) -> None:
        """Start the realtime runtime."""
        if self._worker is not None:
            return

        def _run() -> None:
            while not self._stop.is_set():
                try:
                    kind, args, kwargs = self._q.get(timeout=0.1)
                except queue.Empty:
                    # Opportunistic cache sweep: evict expired from head
                    self._sweep_expired()
                    continue
                try:
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
                    self._q.task_done()

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
                    return value
                else:
                    # Expired
                    try:
                        del self._cache[key]
                    except KeyError:
                        pass

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
        # Enqueue for async processing
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
        self._q.put(("step_failed", (), {"step_run_id": step_run_id}))
        with self._lock:
            self._queued_count += 1

    def flush(self) -> None:
        """Flush the realtime runtime by draining queued events synchronously."""
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
                raise RuntimeError(
                    f"Realtime runtime encountered {count} error(s) while publishing. Last error: {last}"
                )

    def on_step_end(self) -> None:
        """Optional hook when a step ends execution."""
        # no-op for now
        return

    def shutdown(self) -> None:
        """Shutdown the realtime runtime."""
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
        with self._lock:
            queued = self._queued_count
            processed = self._processed_count
            failed_total = self._total_errors
            ttl_seconds = getattr(self, "_ttl_seconds", None)
            max_entries = getattr(self, "_max_entries", None)
        try:
            depth = self._q.qsize()
        except Exception:
            depth = 0
        return {
            "queued": queued,
            "processed": processed,
            "failed_total": failed_total,
            "queue_depth": depth,
            "ttl_seconds": ttl_seconds,
            "max_entries": max_entries,
        }

    # --- internal helpers ---
    def _sweep_expired(self) -> None:
        """Remove expired entries from the head (LRU) side."""
        with self._lock:
            now = time.time()
            # Pop from head while expired
            keys = list(self._cache.keys())
            for k in keys[:32]:  # limit per sweep to bound work
                try:
                    value, expires_at = self._cache[k]
                except KeyError:
                    continue
                if now > expires_at:
                    try:
                        del self._cache[k]
                    except KeyError:
                        pass
                else:
                    # Stop at first non-expired near head
                    break
