"""Run entity manager scaffolding for unified execution.

Abstracts creation and finalization of pipeline/step runs so we can plug in
either DB-backed behavior or stubbed in-memory entities for memory-only runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple, cast


class RunEntityManager(Protocol):
    """Protocol for managing pipeline/step run entities."""

    def create_or_reuse_run(self) -> Tuple[Any, bool]:
        """Create or reuse a pipeline run entity.

        Returns:
            A tuple of (pipeline_run, was_created).
        """

    def create_step_run(self, request: Any) -> Any:
        """Create a step run entity.

        Args:
            request: StepRunRequest-like object.

        Returns:
            A step run entity.
        """

    def finalize_step_run_success(
        self, step_run_id: Any, outputs: Any
    ) -> None:
        """Mark a step run successful."""

    def finalize_step_run_failed(self, step_run_id: Any) -> None:
        """Mark a step run failed."""


@dataclass
class DefaultRunEntityManager:
    """Placeholder for DB-backed manager (to be wired in Phase 2)."""

    launcher: Any

    def create_or_reuse_run(self) -> Tuple[Any, bool]:
        """Create or reuse a pipeline run entity.

        Returns:
            A tuple of (pipeline_run, was_created).
        """
        return cast(Tuple[Any, bool], self.launcher._create_or_reuse_run())

    def create_step_run(self, request: Any) -> Any:
        """Create a step run entity.

        Args:
            request: StepRunRequest-like object.

        Returns:
            A step run entity.
        """
        from zenml.client import Client

        return Client().zen_store.create_run_step(request)

    def finalize_step_run_success(
        self, step_run_id: Any, outputs: Any
    ) -> None:
        """Mark a step run successful.

        Args:
            step_run_id: The step run ID.
            outputs: The outputs of the step run.
        """
        # Defer to runtime publish for now.
        return None

    def finalize_step_run_failed(self, step_run_id: Any) -> None:
        """Mark a step run failed.

        Args:
            step_run_id: The step run ID.
        """
        # Defer to runtime publish for now.
        return None


@dataclass
class MemoryRunEntityManager:
    """Stubbed manager for memory-only execution (Phase 2 wiring)."""

    launcher: Any

    def create_or_reuse_run(self) -> Tuple[Any, bool]:
        """Create or reuse a pipeline run entity.

        Returns:
            A tuple of (pipeline_run, was_created).
        """
        # Build a minimal pipeline run stub compatible with StepRunner expectations
        run_id = self.launcher._orchestrator_run_id  # noqa: SLF001

        @dataclass
        class _PRCfg:
            tags: Any = None
            enable_step_logs: Any = False
            enable_artifact_metadata: Any = False
            enable_artifact_visualization: Any = False

        @dataclass
        class _PipelineRunStub:
            id: str
            name: str
            model_version: Any = None
            pipeline: Any = None
            config: Any = _PRCfg()

        return _PipelineRunStub(id=run_id, name=run_id), True

    def create_step_run(self, request: Any) -> Any:
        """Create a step run entity.

        Args:
            request: StepRunRequest-like object.

        Returns:
            A step run entity.
        """
        # Return a minimal step run stub
        run_id = self.launcher._orchestrator_run_id  # noqa: SLF001
        step_name = self.launcher._step_name  # noqa: SLF001

        @dataclass
        class _StatusStub:
            is_finished: bool = False

        @dataclass
        class _StepRunStub:
            id: str
            name: str
            model_version: Any = None
            logs: Optional[Any] = None
            status: Any = _StatusStub()
            outputs: Dict[str, Any] = None  # type: ignore[assignment]
            regular_inputs: Dict[str, Any] = None  # type: ignore[assignment]

            def __post_init__(self) -> None:  # noqa: D401
                self.outputs = {}
                self.regular_inputs = {}

        return _StepRunStub(id=run_id, name=step_name)

    def finalize_step_run_success(
        self, step_run_id: Any, outputs: Any
    ) -> None:
        """Mark a step run successful.

        Args:
            step_run_id: The step run ID.
            outputs: The outputs of the step run.
        """
        return None

    def finalize_step_run_failed(self, step_run_id: Any) -> None:
        """Mark a step run failed.

        Args:
            step_run_id: The step run ID.
        """
        return None
