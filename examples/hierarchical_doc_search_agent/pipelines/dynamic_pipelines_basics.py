# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Dynamic Pipelines Basics - Educational Examples.

This module demonstrates key dynamic pipeline capabilities step by step:
1. Basic dynamic looping
2. Map/reduce pattern
3. Parallel execution with submit()
4. Cartesian product
5. Broadcasting with unmapped()
6. Unpacking multi-output mapped steps
7. Manual chunking for custom iteration

Each pipeline is self-contained and demonstrates a single concept.
"""

from typing import Annotated, List, Tuple

from zenml import pipeline, step, unmapped


# =============================================================================
# SHARED STEPS - Reused across multiple examples
# =============================================================================


@step
def generate_count() -> int:
    """Generate a count value at runtime."""
    return 4


@step
def generate_numbers() -> List[int]:
    """Generate a list of numbers."""
    return [1, 2, 3, 4, 5]


@step
def generate_letters() -> List[str]:
    """Generate a list of letters."""
    return ["a", "b", "c"]


@step
def process_item(index: int) -> str:
    """Process a single item by index."""
    return f"Processed item {index}"


@step
def double_value(value: int) -> int:
    """Double an integer value."""
    return value * 2


@step
def add_prefix(value: int, prefix: str) -> str:
    """Add a prefix to a value."""
    return f"{prefix}_{value}"


@step
def sum_values(values: List[int]) -> int:
    """Sum a list of values (reducer)."""
    return sum(values)


@step
def concatenate_strings(values: List[str]) -> str:
    """Concatenate strings (reducer)."""
    return " | ".join(values)


@step
def combine_pair(num: int, letter: str) -> str:
    """Combine a number and letter."""
    return f"{letter}{num}"


@step
def compute_pair(value: int) -> Tuple[
    Annotated[int, "doubled"],
    Annotated[int, "tripled"],
]:
    """Return two outputs: doubled and tripled values."""
    return value * 2, value * 3


@step
def process_with_context(item: int, full_context: List[int]) -> str:
    """Process an item with access to the full context list."""
    context_sum = sum(full_context)
    return f"Item {item} processed with context sum={context_sum}"


@step
def report_results(
    description: str, result: str
) -> Annotated[str, "final_report"]:
    """Generate a final report."""
    return f"=== {description} ===\nResult: {result}"


# =============================================================================
# EXAMPLE 1: Basic Dynamic Looping
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def basic_dynamic_loop_pipeline() -> Annotated[str, "loop_result"]:
    """Demonstrate basic dynamic looping based on runtime values.

    The number of `process_item` steps depends on the value returned
    by `generate_count`, which is only known at runtime.
    """
    count = generate_count()
    count_value = count.load()

    results = []
    for idx in range(count_value):
        result = process_item(index=idx)
        results.append(result.load())

    return report_results(
        description="Basic Dynamic Loop",
        result=f"Processed {len(results)} items: {results}",
    )


# =============================================================================
# EXAMPLE 2: Map/Reduce Pattern
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def map_reduce_pipeline() -> Annotated[int, "map_reduce_result"]:
    """Demonstrate the map/reduce pattern using step.map().

    Fan-out: Apply `double_value` to each item in the list.
    Reduce: Sum all the doubled values.
    """
    numbers = generate_numbers()  # [1, 2, 3, 4, 5]

    # Fan out: map step over the list
    doubled = double_value.map(numbers)

    # Reduce: pass the list of results to a reducer step
    total = sum_values(doubled)

    return total


# =============================================================================
# EXAMPLE 3: Parallel Execution with submit()
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def parallel_submit_pipeline() -> Annotated[str, "parallel_result"]:
    """Demonstrate parallel step execution using submit().

    Unlike regular step calls that execute sequentially,
    submit() returns a future and allows parallel execution.
    """
    numbers = generate_numbers()
    numbers_data = numbers.load()

    # Submit multiple steps in parallel
    futures = []
    for num in numbers_data:
        future = double_value.submit(value=num)
        futures.append(future)

    # Wait for all results
    results = [f.load() for f in futures]

    return report_results(
        description="Parallel Submit",
        result=f"Parallel doubled values: {results}",
    )


# =============================================================================
# EXAMPLE 4: Cartesian Product with product()
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def cartesian_product_pipeline() -> Annotated[str, "product_result"]:
    """Demonstrate cartesian product using step.product().

    Creates steps for each combination of inputs:
    [1, 2, 3, 4, 5] x ["a", "b", "c"] = 15 combinations
    """
    numbers = generate_numbers()  # [1, 2, 3, 4, 5]
    letters = generate_letters()  # ["a", "b", "c"]

    # Cartesian product: 5 numbers x 3 letters = 15 mapped steps
    combinations = combine_pair.product(num=numbers, letter=letters)

    # Reduce all combinations
    result = concatenate_strings(combinations)

    return result


# =============================================================================
# EXAMPLE 5: Broadcasting with unmapped()
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def broadcast_unmapped_pipeline() -> Annotated[str, "broadcast_result"]:
    """Demonstrate broadcasting a full artifact using unmapped().

    When mapping, sometimes you want to pass the entire list to each
    mapped step rather than splitting it. Use unmapped() for this.
    """
    numbers = generate_numbers()  # [1, 2, 3, 4, 5]
    context = generate_numbers()  # Same list, but passed as full context

    # Map over numbers, but pass the full context list to each call
    results = process_with_context.map(
        item=numbers,  # Split: each step gets one item
        full_context=unmapped(context),  # Broadcast: each step gets full list
    )

    combined = concatenate_strings(results)

    return combined


# =============================================================================
# EXAMPLE 6: Unpacking Multi-Output Mapped Steps
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def unpack_outputs_pipeline() -> Annotated[str, "unpack_result"]:
    """Demonstrate unpacking outputs from multi-output mapped steps.

    When a mapped step returns multiple outputs, use unpack() to
    separate them into individual lists of artifacts.
    """
    numbers = generate_numbers()  # [1, 2, 3, 4, 5]

    # Map over numbers; each step returns (doubled, tripled)
    results = compute_pair.map(value=numbers)

    # Unpack into separate lists
    doubled_list, tripled_list = results.unpack()

    # Load the values
    doubled_values = [f.load() for f in doubled_list]
    tripled_values = [f.load() for f in tripled_list]

    return report_results(
        description="Unpack Multi-Output",
        result=f"Doubled: {doubled_values}, Tripled: {tripled_values}",
    )


# =============================================================================
# EXAMPLE 7: Manual Chunking with chunk()
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def manual_chunk_pipeline() -> Annotated[str, "chunk_result"]:
    """Demonstrate manual chunking for custom iteration patterns.

    Use artifact.chunk(index) when you need fine-grained control
    over which items to process, such as filtering.
    """
    numbers = generate_numbers()  # [1, 2, 3, 4, 5]
    numbers_data = numbers.load()

    results = []
    for idx, value in enumerate(numbers_data):
        # Only process even values
        if value % 2 == 0:
            # Get artifact chunk at this index
            chunk = numbers.chunk(index=idx)
            result = double_value(value=chunk)
            results.append(result.load())

    return report_results(
        description="Manual Chunk (Even Numbers Only)",
        result=f"Doubled even values: {results}",
    )


# =============================================================================
# EXAMPLE 8: Conditional Branching
# =============================================================================


@step
def check_threshold(value: int) -> bool:
    """Check if value exceeds threshold."""
    return value > 10


@step
def handle_small(value: int) -> str:
    """Handle small values."""
    return f"Small value: {value}"


@step
def handle_large(value: int) -> str:
    """Handle large values."""
    return f"Large value: {value}"


@pipeline(dynamic=True, enable_cache=False)
def conditional_branching_pipeline(
    input_value: int = 15,
) -> Annotated[str, "conditional_result"]:
    """Demonstrate conditional branching based on runtime data.

    The pipeline structure adapts based on the input value.
    """
    is_large = check_threshold(value=input_value)

    if is_large.load():
        result = handle_large(value=input_value)
    else:
        result = handle_small(value=input_value)

    return result


# =============================================================================
# EXAMPLE 9: Dynamic Step Configuration with with_options()
# =============================================================================


@pipeline(dynamic=True, enable_cache=False)
def dynamic_configuration_pipeline(
    use_cache: bool = False,
) -> Annotated[str, "config_result"]:
    """Demonstrate dynamic step configuration using with_options().

    Step behavior can be modified at runtime based on parameters.
    """
    numbers = generate_numbers()
    numbers_data = numbers.load()

    results = []
    for idx, _ in enumerate(numbers_data):
        # Configure step dynamically based on runtime condition
        configured_step = process_item.with_options(
            enable_cache=use_cache,
            extra={"run_index": idx},  # Custom metadata
        )
        result = configured_step(index=idx)
        results.append(result.load())

    return report_results(
        description="Dynamic Configuration",
        result=f"Configured results: {results}",
    )


# =============================================================================
# EXAMPLE 10: Nested Dynamic Patterns
# =============================================================================


@step
def generate_batches() -> List[List[int]]:
    """Generate batches of numbers."""
    return [[1, 2], [3, 4, 5], [6]]


@step
def process_batch(batch: List[int]) -> int:
    """Process a batch and return sum."""
    return sum(batch)


@pipeline(dynamic=True, enable_cache=False)
def nested_dynamic_pipeline() -> Annotated[str, "nested_result"]:
    """Demonstrate nested dynamic patterns.

    Process a variable number of batches, where each batch
    has a variable number of items.
    """
    batches = generate_batches()
    batches_data = batches.load()

    batch_sums = []
    for idx, _ in enumerate(batches_data):
        batch_chunk = batches.chunk(index=idx)
        batch_sum = process_batch(batch=batch_chunk)
        batch_sums.append(batch_sum.load())

    total = sum(batch_sums)

    return report_results(
        description="Nested Dynamic (Batches)",
        result=f"Batch sums: {batch_sums}, Total: {total}",
    )
