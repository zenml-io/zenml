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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Tuple, Type
from uuid import UUID

from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.models import ArtifactVersionResponse

# Note: avoid importing zenml.orchestrators modules at import time to prevent
# circular dependencies. Where needed, import locally within methods.

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.step_configurations import Step
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.models.v2.core.step_run import StepRunInputResponse
    from zenml.stack import Stack
    from zenml.steps.utils import OutputSignature

logger = get_logger(__name__)


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
        input_artifacts: Mapping[str, "ArtifactVersionResponse"],
        artifact_store: "BaseArtifactStore",
        project_id: UUID,
    ) -> str:
        """Compute a cache key for a step using existing utilities.

        Default implementation delegates to `cache_utils`.

        Args:
            step: The step to compute the cache key for.
            input_artifacts: The input artifacts.
            artifact_store: The artifact store to compute the cache key for.
            project_id: The project ID to compute the cache key for.

        Returns:
            The computed cache key.
        """
        # Local import to avoid circular import issues
        from zenml.orchestrators import cache_utils

        return cache_utils.generate_cache_key(
            step=step,
            input_artifacts=input_artifacts,
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
        # Local import to avoid circular import issues
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
        if not bool(getattr(self, "_metadata_enabled", True)):
            return
        from zenml.orchestrators.publish_utils import (
            publish_pipeline_run_metadata as _pub_run_md,
        )

        _pub_run_md(
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
        if not bool(getattr(self, "_metadata_enabled", True)):
            return
        from zenml.orchestrators.publish_utils import (
            publish_step_run_metadata as _pub_step_md,
        )

        _pub_step_md(
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
            publish_successful_step_run as _pub_step_success,
        )

        _pub_step_success(
            step_run_id=step_run_id, output_artifact_ids=output_artifact_ids
        )

    def publish_failed_step_run(self, *, step_run_id: Any) -> None:
        """Publish a failed step run.

        Args:
            step_run_id: The step run ID.
        """
        from zenml.orchestrators.publish_utils import (
            publish_failed_step_run as _pub_step_failed,
        )

        _pub_step_failed(step_run_id)

    def flush(self) -> None:
        """Ensure all queued updates are sent."""

    def on_step_end(self) -> None:
        """Optional hook when a step finishes execution."""

    def shutdown(self) -> None:
        """Optional shutdown hook for runtime lifecycles."""

    def get_metrics(self) -> Dict[str, Any]:
        """Optional runtime metrics for observability.

        Returns:
            Dictionary of runtime metrics; empty by default.
        """
        return {}

    # --- Flush behavior ---
    def should_flush_on_step_end(self) -> bool:
        """Whether the runner should call flush() at step end.

        Implementations may override to disable flush for non-blocking serving.

        Returns:
            True to flush on step end; False otherwise.
        """
        return True
