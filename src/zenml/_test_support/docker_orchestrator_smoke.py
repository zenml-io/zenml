"""Importable smoke pipeline definitions for Docker orchestrator tests.

Docker step containers load step callables by source module path. Keeping these
definitions inside the installed ZenML package makes the smoke test independent
from whether the test tree is available in the runtime image.
"""

from zenml import pipeline, step


@step(enable_cache=False)
def smoke_constant_step() -> int:
    """Return a constant value for the Docker orchestrator smoke pipeline."""
    return 7


@step(enable_cache=False)
def smoke_increment_step(input_value: int) -> int:
    """Increment the smoke pipeline input value."""
    return input_value + 1


@pipeline(name="connected_two_step_pipeline")
def smoke_pipeline() -> None:
    """Run a minimal two-step pipeline."""
    smoke_increment_step(smoke_constant_step())
