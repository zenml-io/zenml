"""Simple dynamic pipeline examples.

This module showcases a few dynamic pipeline patterns:

- Sequential execution in regular Python control flow.
- Parallel step execution with `submit`/`Future` APIs.
- Runtime configuration overrides via `with_options`.

Run the module directly to execute all examples on the active ZenML stack.
"""

from typing import List

from zenml import pipeline, step


@step
def generate_iteration_count() -> int:
    """Provide the number of loop iterations used in the examples."""
    for i in range(0, 3):
        compute_value.submit(index=i, factor=i + 1)
    return 3


@step
def compute_value(index: int, factor: int = 2) -> int:
    """Scale an index by a configurable factor and return the result."""

    result = index * factor
    print(f"[compute_value] index={index}, factor={factor}, result={result}")
    return result


@step
def log_results(results: List[int]) -> None:
    """Log the collected results to the console."""

    print(f"[log_results] results={results}")


@pipeline
def sequential_dynamic_pipeline() -> None:
    """Run steps sequentially inside regular Python control flow."""

    iteration_count = generate_iteration_count().load()

    values: List[int] = []
    for idx in range(iteration_count):
        artifact = compute_value(index=idx)
        values.append(artifact.load())

    log_results(results=values)


@pipeline(enable_cache=False)
def parallel_dynamic_pipeline() -> None:
    """Execute step instances concurrently using the ``submit`` API."""

    iteration_count = generate_iteration_count() 
    # futures = [
    #     compute_value(index=idx, factor=idx + 1)
    #     for idx in range(iteration_count)
    # ]

    # iteration_count = generate_iteration_count().load()

    # futures = [
    #     compute_value.submit(index=idx, factor=idx + 1)
    #     for idx in range(iteration_count)
    # ]

    # # breakpoint()
    # results = []
    # for future in futures:
    #     future.wait()
    #     results.append(future.load())

    # log_results(results=results)


@pipeline
def parameterized_dynamic_pipeline() -> None:
    """Demonstrate runtime configuration overrides for individual steps."""

    no_cache_compute = compute_value.with_options(enable_cache=False)
    triple_compute = compute_value.with_options(parameters={"factor": 3})

    artifacts = [
        no_cache_compute(index=0),
        triple_compute(index=1),
    ]

    results = [artifact.load() for artifact in artifacts]
    log_results(results=results)


if __name__ == "__main__":
    print("Running sequential dynamic pipeline...")
    # sequential_dynamic_pipeline()

    print("\nRunning parallel dynamic pipeline...")
    parallel_dynamic_pipeline()

    print("\nRunning parameterized dynamic pipeline...")
    # parameterized_dynamic_pipeline()

