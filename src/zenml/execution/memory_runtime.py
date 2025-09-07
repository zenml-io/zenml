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
"""Memory-only step runtime (in-process handoff, no DB/FS persistence)."""

import threading
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Tuple, Type

from zenml.execution.step_runtime import BaseStepRuntime
from zenml.logger import get_logger
from zenml.steps.step_context import get_step_context
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineRunResponse, StepRunResponse

logger = get_logger(__name__)


class MemoryStepRuntime(BaseStepRuntime):
    """Pure in-memory execution runtime: no server calls, no persistence.

    Instance-scoped store to isolate requests. Values are accessible within the
    same process for the same run id and step chain only.
    """

    @staticmethod
    def make_handle_id(run_id: str, step_name: str, output_name: str) -> str:
        """Make a handle ID for an output artifact.

        Args:
            run_id: The run ID.
            step_name: The step name.
            output_name: The output name.

        Returns:
            The handle ID.
        """
        return f"mem://{run_id}/{step_name}/{output_name}"

    @staticmethod
    def parse_handle_id(handle_id: str) -> Tuple[str, str, str]:
        """Parse a handle ID for an output artifact.

        Args:
            handle_id: The handle ID.

        Returns:
            The run ID, step name, and output name.

        Raises:
            ValueError: If the handle id is malformed.
        """
        if not isinstance(handle_id, str) or not handle_id.startswith(
            "mem://"
        ):
            raise ValueError("Invalid memory handle id")
        rest = handle_id[len("mem://") :]
        # split into exactly 3 parts: run_id, step_name, output_name
        parts = rest.split("/", 2)
        if len(parts) != 3:
            raise ValueError("Invalid memory handle id")
        run_id, step_name, output_name = parts
        # basic sanitization
        for p in (run_id, step_name, output_name):
            if not p or "\n" in p or "\r" in p:
                raise ValueError("Invalid memory handle component")
        return run_id, step_name, output_name

    class Handle:
        """A handle for an output artifact."""

        def __init__(self, id: str) -> None:
            """Initialize the handle.

            Args:
                id: The handle ID.
            """
            self.id = id

    # Instance-scoped context for handle resolution (set by launcher)
    def __init__(self) -> None:
        """Initialize the memory runtime."""
        super().__init__()
        self._ctx_run_id: Optional[str] = None
        self._ctx_substitutions: Dict[str, str] = {}
        self._active_run_ids: set[str] = set()
        # Instance-scoped storage and locks per run_id
        self._store: Dict[str, Dict[Tuple[str, str], Any]] = {}
        self._run_locks: Dict[str, Any] = {}
        self._global_lock: Any = threading.RLock()

    def set_context(
        self, *, run_id: str, substitutions: Optional[Dict[str, str]] = None
    ) -> None:
        """Set current memory-only context for handle resolution.

        Args:
            run_id: The run ID.
            substitutions: The substitutions.
        """
        self._ctx_run_id = run_id
        self._ctx_substitutions = substitutions or {}
        try:
            if run_id:
                self._active_run_ids.add(run_id)
        except Exception:
            pass

    def resolve_step_inputs(
        self,
        *,
        step: "Step",
        pipeline_run: "PipelineRunResponse",
        step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
    ) -> Dict[str, Any]:
        """Resolve step inputs by constructing in-memory handles.

        Args:
            step: The step to resolve inputs for.
            pipeline_run: The pipeline run to resolve inputs for.
            step_runs: The step runs to resolve inputs for.

        Returns:
            A mapping of input name to MemoryStepRuntime.Handle.
        """
        run_id = self._ctx_run_id or str(getattr(pipeline_run, "id", "local"))
        subs = self._ctx_substitutions or {}
        handles: Dict[str, Any] = {}
        for name, input_ in step.spec.inputs.items():
            resolved_output_name = string_utils.format_name_template(
                input_.output_name, substitutions=subs
            )
            handle_id = self.make_handle_id(
                run_id=run_id,
                step_name=input_.step_name,
                output_name=resolved_output_name,
            )
            handles[name] = MemoryStepRuntime.Handle(handle_id)
        return handles

    def load_input_artifact(
        self, *, artifact: Any, data_type: Type[Any], stack: Any
    ) -> Any:
        """Load an input artifact.

        Args:
            artifact: The artifact to load.
            data_type: The data type of the artifact.
            stack: The stack to load the artifact from.

        Returns:
            The loaded artifact.

        Raises:
            ValueError: If the memory handle id is invalid or malformed.
        """
        handle_id_any = getattr(artifact, "id", None)
        if not isinstance(handle_id_any, str):
            raise ValueError("Invalid memory handle id")
        run_id, step_name, output_name = self.parse_handle_id(handle_id_any)
        # Use per-run lock to avoid cross-run interference
        with self._global_lock:
            rlock = self._run_locks.setdefault(run_id, threading.RLock())
        with rlock:
            return self._store.get(run_id, {}).get((step_name, output_name))

    def store_output_artifacts(
        self,
        *,
        output_data: Dict[str, Any],
        output_materializers: Dict[str, Tuple[Type[Any], ...]],
        output_artifact_uris: Dict[str, str],
        output_annotations: Dict[str, Any],
        artifact_metadata_enabled: bool,
        artifact_visualization_enabled: bool,
    ) -> Dict[str, Any]:
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
        ctx = get_step_context()
        run_id = str(getattr(ctx.pipeline_run, "id", "local"))
        try:
            if run_id:
                self._active_run_ids.add(run_id)
        except Exception:
            pass
        step_name = str(getattr(ctx.step_run, "name", "step"))
        handles: Dict[str, Any] = {}
        with self._global_lock:
            rlock = self._run_locks.setdefault(run_id, threading.RLock())
        with rlock:
            rr = self._store.setdefault(run_id, {})
            for output_name, value in output_data.items():
                rr[(step_name, output_name)] = value
                handle_id = self.make_handle_id(run_id, step_name, output_name)
                handles[output_name] = MemoryStepRuntime.Handle(handle_id)
        return handles

    def compute_cache_key(
        self,
        *,
        step: Any,
        input_artifacts: Mapping[str, Any],
        artifact_store: Any,
        project_id: Any,
    ) -> str:
        """Compute a cache key.

        Args:
            step: The step to compute the cache key for.
            input_artifacts: The input artifacts for the step.
            artifact_store: The artifact store to compute the cache key for.
            project_id: The project ID to compute the cache key for.

        Returns:
            The computed cache key.
        """
        return ""

    def get_cached_step_run(self, *, cache_key: str) -> None:
        """Get a cached step run.

        Args:
            cache_key: The cache key to get the cached step run for.

        Returns:
            The cached step run if available, otherwise None.
        """
        return None

    def publish_pipeline_run_metadata(
        self, *, pipeline_run_id: Any, pipeline_run_metadata: Any
    ) -> None:
        """Publish pipeline run metadata.

        Args:
            pipeline_run_id: The pipeline run ID.
            pipeline_run_metadata: The pipeline run metadata.
        """
        return

    def publish_step_run_metadata(
        self, *, step_run_id: Any, step_run_metadata: Any
    ) -> None:
        """Publish step run metadata.

        Args:
            step_run_id: The step run ID.
            step_run_metadata: The step run metadata.
        """
        return

    def publish_successful_step_run(
        self, *, step_run_id: Any, output_artifact_ids: Any
    ) -> None:
        """Publish a successful step run.

        Args:
            step_run_id: The step run ID.
            output_artifact_ids: The output artifact IDs.
        """
        return

    def publish_failed_step_run(self, *, step_run_id: Any) -> None:
        """Publish a failed step run.

        Args:
            step_run_id: The step run ID.
        """
        return

    def start(self) -> None:
        """Start the memory runtime."""
        return

    def on_step_start(self) -> None:
        """Optional hook when a step starts execution."""
        return

    def flush(self) -> None:
        """Flush the memory runtime."""
        return

    def on_step_end(self) -> None:
        """Optional hook when a step ends execution."""
        return

    def shutdown(self) -> None:
        """Shutdown the memory runtime."""
        return

    def __del__(self) -> None:  # noqa: D401
        """Best-effort cleanup of per-run memory when GC collects the runtime."""
        try:
            for run_id in list(self._active_run_ids):
                try:
                    self.reset(run_id)
                except Exception:
                    pass
        except Exception:
            pass

    # --- Unified path helpers ---
    def reset(self, run_id: str) -> None:
        """Clear all in-memory data associated with a specific run.

        Args:
            run_id: The run id to clear.
        """
        with self._global_lock:
            try:
                self._store.pop(run_id, None)
            finally:
                self._run_locks.pop(run_id, None)
