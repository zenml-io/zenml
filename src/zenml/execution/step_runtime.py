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
"""Step runtime facade for step execution responsibilities.

This scaffolds a minimal, behavior-preserving runtime abstraction that the
step runner can call into for artifact I/O and input resolution. The default
implementation delegates to existing ZenML utilities.

Enable usage by setting environment variable `ZENML_ENABLE_STEP_RUNTIME=true`.
"""

import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from zenml.client import Client
from zenml.models import ArtifactVersionResponse

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.step_configurations import Step
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.models.v2.core.step_run import StepRunInputResponse
    from zenml.stack import Stack
    from zenml.steps.utils import OutputSignature


class BaseStepRuntime(ABC):
    """Abstract execution-time interface for step I/O and interactions.

    Implementations may optimize persistence, caching, logging, and server
    updates based on capture policy. This base class only covers the minimal
    responsibilities we want to centralize first.
    """

    @abstractmethod
    def resolve_step_inputs(
        self,
        *,
        step: "Step",
        pipeline_run: "PipelineRunResponse",
        step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
    ) -> Dict[str, "StepRunInputResponse"]:
        """Resolve input artifacts for the given step.

        Args:
            step: The step to resolve inputs for.
            pipeline_run: The pipeline run to resolve inputs for.
            step_runs: The step runs to resolve inputs for.

        Returns:
            The resolved inputs.
        """

    @abstractmethod
    def load_input_artifact(
        self,
        *,
        artifact: ArtifactVersionResponse,
        data_type: Type[Any],
        stack: "Stack",
    ) -> Any:
        """Load materialized value for an input artifact.

        Args:
            artifact: The artifact to load.
            data_type: The data type of the artifact.
            stack: The stack to load the artifact from.
        """

    @abstractmethod
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
        """Materialize and persist output artifacts and return their versions.

        Args:
            output_data: The output data.
            output_materializers: The output materializers.
            output_artifact_uris: The output artifact URIs.
            output_annotations: The output annotations.
            artifact_metadata_enabled: Whether artifact metadata is enabled.
            artifact_visualization_enabled: Whether artifact visualization is enabled.
        """

    # --- Cache Helpers (optional) ---
    def compute_cache_key(
        self,
        *,
        step: "Step",
        input_artifact_ids: Dict[str, UUID],
        artifact_store: "BaseArtifactStore",
        project_id: UUID,
    ) -> str:
        """Compute a cache key for a step using existing utilities.

        Default implementation delegates to `cache_utils`.

        Args:
            step: The step to compute the cache key for.
            input_artifact_ids: The input artifact IDs.
            artifact_store: The artifact store to compute the cache key for.
            project_id: The project ID to compute the cache key for.

        Returns:
            The computed cache key.
        """
        from zenml.orchestrators import cache_utils

        return cache_utils.generate_cache_key(
            step=step,
            input_artifact_ids=input_artifact_ids,
            artifact_store=artifact_store,
            project_id=project_id,
        )

    def get_cached_step_run(
        self, *, cache_key: str
    ) -> Optional["StepRunResponse"]:
        """Return a cached step run if available.

        Default implementation delegates to `cache_utils`.

        Args:
            cache_key: The cache key to get the cached step run for.

        Returns:
            The cached step run if available, otherwise None.
        """
        from zenml.orchestrators import cache_utils

        return cache_utils.get_cached_step_run(cache_key=cache_key)

    # --- Server update helpers (may be batched/async by implementations) ---
    def start(self) -> None:
        """Optional start hook for runtime lifecycles."""

    def on_step_start(self) -> None:
        """Optional hook when a step begins execution."""

    def publish_pipeline_run_metadata(
        self, *, pipeline_run_id: Any, pipeline_run_metadata: Any
    ) -> None:
        """Publish pipeline run metadata.

        Args:
            pipeline_run_id: The pipeline run ID.
            pipeline_run_metadata: The pipeline run metadata.
        """
        from zenml.orchestrators.publish_utils import (
            publish_pipeline_run_metadata,
        )

        publish_pipeline_run_metadata(
            pipeline_run_id=pipeline_run_id,
            pipeline_run_metadata=pipeline_run_metadata,
        )

    def publish_step_run_metadata(
        self, *, step_run_id: Any, step_run_metadata: Any
    ) -> None:
        """Publish step run metadata.

        Args:
            step_run_id: The step run ID.
            step_run_metadata: The step run metadata.
        """
        from zenml.orchestrators.publish_utils import publish_step_run_metadata

        publish_step_run_metadata(
            step_run_id=step_run_id, step_run_metadata=step_run_metadata
        )

    def publish_successful_step_run(
        self, *, step_run_id: Any, output_artifact_ids: Any
    ) -> None:
        """Publish a successful step run.

        Args:
            step_run_id: The step run ID.
            output_artifact_ids: The output artifact IDs.
        """
        from zenml.orchestrators.publish_utils import (
            publish_successful_step_run,
        )

        publish_successful_step_run(
            step_run_id=step_run_id, output_artifact_ids=output_artifact_ids
        )

    def publish_failed_step_run(self, *, step_run_id: Any) -> None:
        """Publish a failed step run.

        Args:
            step_run_id: The step run ID.
        """
        from zenml.orchestrators.publish_utils import publish_failed_step_run

        publish_failed_step_run(step_run_id)

    def flush(self) -> None:
        """Ensure all queued updates are sent."""

    def on_step_end(self) -> None:
        """Optional hook when a step finishes execution."""

    def shutdown(self) -> None:
        """Optional shutdown hook for runtime lifecycles."""

    def get_metrics(self) -> Dict[str, Any]:
        """Optional runtime metrics for observability.

        Default implementation returns an empty dict.
        """
        return {}

    # --- Flush behavior ---
    def should_flush_on_step_end(self) -> bool:
        """Whether the runner should call flush() at step end.

        Implementations may override to disable flush for non-blocking serving.
        """
        return True


class DefaultStepRuntime(BaseStepRuntime):
    """Default runtime delegating to existing ZenML utilities.

    This keeps current behavior intact while providing a single place for the
    step runner to call into. It intentionally mirrors logic from
    `step_runner.py` and `orchestrators/input_utils.py`.
    """

    # --- Input Resolution ---
    def resolve_step_inputs(
        self,
        *,
        step: "Step",
        pipeline_run: "PipelineRunResponse",
        step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
    ) -> Dict[str, "StepRunInputResponse"]:
        """Resolve step inputs.

        Args:
            step: The step to resolve inputs for.
            pipeline_run: The pipeline run to resolve inputs for.
            step_runs: The step runs to resolve inputs for.
        """
        from zenml.orchestrators import input_utils

        return input_utils.resolve_step_inputs(
            step=step, pipeline_run=pipeline_run, step_runs=step_runs
        )

    # --- Artifact Load ---
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
            stack: The stack to load the artifact from.
        """
        from typing import Any as _Any

        from zenml.artifacts.unmaterialized_artifact import (
            UnmaterializedArtifact,
        )
        from zenml.materializers.base_materializer import BaseMaterializer
        from zenml.orchestrators.utils import (
            register_artifact_store_filesystem,
        )
        from zenml.utils import source_utils
        from zenml.utils.typing_utils import get_origin, is_union

        # Skip materialization for `UnmaterializedArtifact`.
        if data_type == UnmaterializedArtifact:
            return UnmaterializedArtifact(
                **artifact.get_hydrated_version().model_dump()
            )

        if data_type in (None, _Any) or is_union(get_origin(data_type)):
            # Use the stored artifact datatype when function annotation is not specific
            data_type = source_utils.load(artifact.data_type)

        materializer_class: Type[BaseMaterializer] = (
            source_utils.load_and_validate_class(
                artifact.materializer, expected_class=BaseMaterializer
            )
        )

        def _load(artifact_store: "BaseArtifactStore") -> Any:
            materializer: BaseMaterializer = materializer_class(
                uri=artifact.uri, artifact_store=artifact_store
            )
            materializer.validate_load_type_compatibility(data_type)
            return materializer.load(data_type=data_type)

        if artifact.artifact_store_id == stack.artifact_store.id:
            stack.artifact_store._register()
            return _load(artifact_store=stack.artifact_store)
        else:
            with register_artifact_store_filesystem(
                artifact.artifact_store_id
            ) as target_store:
                return _load(artifact_store=target_store)

    # --- Artifact Store ---
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
        from typing import Type as _Type

        from zenml.artifacts.utils import (
            _store_artifact_data_and_prepare_request,
        )
        from zenml.enums import ArtifactSaveType
        from zenml.materializers.base_materializer import BaseMaterializer
        from zenml.steps.step_context import get_step_context
        from zenml.utils import materializer_utils, source_utils, tag_utils

        step_context = get_step_context()
        artifact_requests: List[Any] = []

        for output_name, return_value in output_data.items():
            data_type = type(return_value)
            materializer_classes = output_materializers[output_name]
            if materializer_classes:
                materializer_class: _Type[BaseMaterializer] = (
                    materializer_utils.select_materializer(
                        data_type=data_type,
                        materializer_classes=materializer_classes,
                    )
                )
            else:
                # Runtime selection if no explicit materializer recorded
                from zenml.materializers.materializer_registry import (
                    materializer_registry,
                )

                default_materializer_source = (
                    step_context.step_run.config.outputs[
                        output_name
                    ].default_materializer_source
                    if step_context and step_context.step_run
                    else None
                )

                if default_materializer_source:
                    default_materializer_class: _Type[BaseMaterializer] = (
                        source_utils.load_and_validate_class(
                            default_materializer_source,
                            expected_class=BaseMaterializer,
                        )
                    )
                    materializer_registry.default_materializer = (
                        default_materializer_class
                    )

                materializer_class = materializer_registry[data_type]

            uri = output_artifact_uris[output_name]
            artifact_config = output_annotations[output_name].artifact_config

            artifact_type = None
            if artifact_config is not None:
                has_custom_name = bool(artifact_config.name)
                version = artifact_config.version
                artifact_type = artifact_config.artifact_type
            else:
                has_custom_name, version = False, None

            # Name resolution mirrors existing behavior
            if has_custom_name:
                artifact_name = output_name
            else:
                if step_context.pipeline_run.pipeline:
                    pipeline_name = step_context.pipeline_run.pipeline.name
                else:
                    pipeline_name = "unlisted"
                step_name = step_context.step_run.name
                artifact_name = f"{pipeline_name}::{step_name}::{output_name}"

            # Collect user metadata and tags
            user_metadata = step_context.get_output_metadata(output_name)
            tags = step_context.get_output_tags(output_name)
            if step_context.pipeline_run.config.tags is not None:
                for tag in step_context.pipeline_run.config.tags:
                    if isinstance(tag, tag_utils.Tag) and tag.cascade is True:
                        tags.append(tag.name)

            artifact_request = _store_artifact_data_and_prepare_request(
                name=artifact_name,
                data=return_value,
                materializer_class=materializer_class,
                uri=uri,
                artifact_type=artifact_type,
                store_metadata=artifact_metadata_enabled,
                store_visualizations=artifact_visualization_enabled,
                has_custom_name=has_custom_name,
                version=version,
                tags=tags,
                save_type=ArtifactSaveType.STEP_OUTPUT,
                metadata=user_metadata,
            )
            artifact_requests.append(artifact_request)

        responses = Client().zen_store.batch_create_artifact_versions(
            artifact_requests
        )
        return dict(zip(output_data.keys(), responses))


class OffStepRuntime(DefaultStepRuntime):
    """OFF mode runtime: minimize overhead but keep correctness.

    Notes:
    - We intentionally keep artifact persistence and success/failure status
      updates to avoid breaking input resolution across steps.
    - We no-op metadata publishing calls to reduce server traffic.
    """

    def publish_pipeline_run_metadata(
        self, *, pipeline_run_id: Any, pipeline_run_metadata: Any
    ) -> None:
        """Publish pipeline run metadata.

        Args:
            pipeline_run_id: The pipeline run ID.
            pipeline_run_metadata: The pipeline run metadata.
        """
        # No-op: skip pipeline run metadata in OFF mode
        return

    def publish_step_run_metadata(
        self, *, step_run_id: Any, step_run_metadata: Any
    ) -> None:
        """Publish step run metadata.

        Args:
            step_run_id: The step run ID.
            step_run_metadata: The step run metadata.
        """
        # No-op: skip step run metadata in OFF mode
        return


class MemoryStepRuntime(BaseStepRuntime):
    """Pure in-memory execution runtime: no server calls, no persistence."""

    # Global registry keyed by run_id to isolate concurrent runs
    _STORE: Dict[str, Dict[Tuple[str, str], Any]] = {}
    _RUN_LOCKS: Dict[str, Any] = {}
    _GLOBAL_LOCK: Any = threading.RLock()  # protects registry structures

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
        from zenml.utils import string_utils

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
        """
        handle_id_any = getattr(artifact, "id", None)
        if not isinstance(handle_id_any, str):
            raise ValueError("Invalid memory handle id")
        run_id, step_name, output_name = self.parse_handle_id(handle_id_any)
        # Use per-run lock to avoid cross-run interference
        with MemoryStepRuntime._GLOBAL_LOCK:
            rlock = MemoryStepRuntime._RUN_LOCKS.setdefault(
                run_id, threading.RLock()
            )
        with rlock:
            return MemoryStepRuntime._STORE.get(run_id, {}).get(
                (step_name, output_name)
            )

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
        from zenml.steps.step_context import get_step_context

        ctx = get_step_context()
        run_id = str(getattr(ctx.pipeline_run, "id", "local"))
        try:
            if run_id:
                self._active_run_ids.add(run_id)
        except Exception:
            pass
        step_name = str(getattr(ctx.step_run, "name", "step"))
        handles: Dict[str, Any] = {}
        with MemoryStepRuntime._GLOBAL_LOCK:
            rlock = MemoryStepRuntime._RUN_LOCKS.setdefault(
                run_id, threading.RLock()
            )
        with rlock:
            rr = MemoryStepRuntime._STORE.setdefault(run_id, {})
            for output_name, value in output_data.items():
                rr[(step_name, output_name)] = value
                handle_id = self.make_handle_id(run_id, step_name, output_name)
                handles[output_name] = MemoryStepRuntime.Handle(handle_id)
        return handles

    def compute_cache_key(
        self,
        *,
        step: Any,
        input_artifact_ids: Dict[str, Any],
        artifact_store: Any,
        project_id: Any,
    ) -> str:
        """Compute a cache key.

        Args:
            step: The step to compute the cache key for.
            input_artifact_ids: The input artifact IDs.
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
        with MemoryStepRuntime._GLOBAL_LOCK:
            try:
                MemoryStepRuntime._STORE.pop(run_id, None)
            finally:
                MemoryStepRuntime._RUN_LOCKS.pop(run_id, None)
