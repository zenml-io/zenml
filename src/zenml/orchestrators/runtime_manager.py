"""Runtime manager for unified runtime-driven execution paths.

Provides helpers to reuse a shared runtime instance across all steps of a
single serving request (e.g., MemoryStepRuntime for memory-only execution),
and utilities to reset per-run state when the request completes.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from zenml.execution.memory_runtime import MemoryStepRuntime
from zenml.execution.step_runtime import BaseStepRuntime

# Shared runtime context for the lifetime of a single request.
_shared_runtime: ContextVar[Optional[BaseStepRuntime]] = ContextVar(
    "zenml_shared_runtime", default=None
)


def set_shared_runtime(runtime: BaseStepRuntime) -> None:
    """Set a runtime instance to be reused across steps for the current request.

    Args:
        runtime: The runtime instance to set.
    """
    _shared_runtime.set(runtime)


def get_shared_runtime() -> Optional[BaseStepRuntime]:
    """Get the shared runtime instance for the current request, if any.

    Returns:
        The shared runtime instance for the current request, if any.
    """
    return _shared_runtime.get()


def clear_shared_runtime() -> None:
    """Clear the shared runtime instance for the current request.

    Returns:
        The shared runtime instance for the current request, if any.
    """
    _shared_runtime.set(None)


def get_or_create_shared_memory_runtime() -> MemoryStepRuntime:
    """Get or create a shared MemoryStepRuntime for the current request.

    Returns:
        The shared runtime instance for the current request, if any.
    """
    rt = _shared_runtime.get()
    if isinstance(rt, MemoryStepRuntime):
        return rt
    mem = MemoryStepRuntime()
    set_shared_runtime(mem)
    return mem


def reset_memory_runtime_for_run(run_id: str) -> None:
    """Reset per-run memory state on the shared memory runtime if present.

    Args:
        run_id: The run ID.
    """
    rt = _shared_runtime.get()
    if isinstance(rt, MemoryStepRuntime):
        try:
            rt.reset(run_id)
        except Exception as e:
            # Best-effort cleanup; log at debug level and continue
            try:
                from zenml.logger import get_logger

                get_logger(__name__).debug(
                    "Ignoring error during memory runtime reset for run %s: %s",
                    run_id,
                    e,
                )
            except Exception:
                pass
