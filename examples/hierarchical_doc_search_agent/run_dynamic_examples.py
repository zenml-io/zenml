#!/usr/bin/env python3
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
"""Run Dynamic Pipeline Examples.

This script demonstrates ZenML's dynamic pipeline capabilities through
a series of self-contained examples. Each example showcases a specific
feature of dynamic pipelines.

Usage:
    # Run all examples
    python run_dynamic_examples.py

    # Run a specific example
    python run_dynamic_examples.py --example basic_loop
    python run_dynamic_examples.py --example map_reduce
    python run_dynamic_examples.py --example parallel
    python run_dynamic_examples.py --example cartesian
    python run_dynamic_examples.py --example broadcast
    python run_dynamic_examples.py --example unpack
    python run_dynamic_examples.py --example chunk
    python run_dynamic_examples.py --example conditional
    python run_dynamic_examples.py --example config
    python run_dynamic_examples.py --example nested

    # List all available examples
    python run_dynamic_examples.py --list
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from pipelines.dynamic_pipelines_basics import (
    basic_dynamic_loop_pipeline,
    broadcast_unmapped_pipeline,
    cartesian_product_pipeline,
    conditional_branching_pipeline,
    dynamic_configuration_pipeline,
    manual_chunk_pipeline,
    map_reduce_pipeline,
    nested_dynamic_pipeline,
    parallel_submit_pipeline,
    unpack_outputs_pipeline,
)

# Registry of available examples
EXAMPLES = {
    "basic_loop": {
        "pipeline": basic_dynamic_loop_pipeline,
        "description": "Basic dynamic looping based on runtime values",
        "kwargs": {},
    },
    "map_reduce": {
        "pipeline": map_reduce_pipeline,
        "description": "Map/reduce pattern using step.map()",
        "kwargs": {},
    },
    "parallel": {
        "pipeline": parallel_submit_pipeline,
        "description": "Parallel step execution using submit()",
        "kwargs": {},
    },
    "cartesian": {
        "pipeline": cartesian_product_pipeline,
        "description": "Cartesian product using step.product()",
        "kwargs": {},
    },
    "broadcast": {
        "pipeline": broadcast_unmapped_pipeline,
        "description": "Broadcasting artifacts using unmapped()",
        "kwargs": {},
    },
    "unpack": {
        "pipeline": unpack_outputs_pipeline,
        "description": "Unpacking multi-output mapped steps",
        "kwargs": {},
    },
    "chunk": {
        "pipeline": manual_chunk_pipeline,
        "description": "Manual chunking for custom iteration",
        "kwargs": {},
    },
    "conditional": {
        "pipeline": conditional_branching_pipeline,
        "description": "Conditional branching based on runtime data",
        "kwargs": {"input_value": 15},
    },
    "config": {
        "pipeline": dynamic_configuration_pipeline,
        "description": "Dynamic step configuration with with_options()",
        "kwargs": {"use_cache": False},
    },
    "nested": {
        "pipeline": nested_dynamic_pipeline,
        "description": "Nested dynamic patterns (batches)",
        "kwargs": {},
    },
}


def print_banner(title: str) -> None:
    """Print a formatted banner."""
    width = 60
    print("\n" + "=" * width)
    print(f" {title}".center(width))
    print("=" * width + "\n")


def list_examples() -> None:
    """List all available examples."""
    print_banner("Dynamic Pipeline Examples")
    print("Available examples:\n")
    for name, info in EXAMPLES.items():
        print(f"  {name:15} - {info['description']}")
    print("\nUsage: python run_dynamic_examples.py --example <name>")
    print("       python run_dynamic_examples.py  # runs all examples")


def run_example(name: str) -> None:
    """Run a single example."""
    if name not in EXAMPLES:
        print(f"Error: Unknown example '{name}'")
        print(f"Available: {', '.join(EXAMPLES.keys())}")
        sys.exit(1)

    info = EXAMPLES[name]
    print_banner(f"Example: {name}")
    print(f"Description: {info['description']}\n")

    pipeline_fn = info["pipeline"]
    kwargs = info["kwargs"]

    # Get pipeline name - works for both DynamicPipeline and regular functions
    pipeline_name = getattr(pipeline_fn, "name", name)
    print(f"Running pipeline: {pipeline_name}")
    print("-" * 40)

    result = pipeline_fn(**kwargs)

    print("-" * 40)
    print("Pipeline completed successfully!")
    print(f"Result: {result}")


def run_all_examples() -> None:
    """Run all examples sequentially."""
    print_banner("Running All Dynamic Pipeline Examples")

    for name in EXAMPLES:
        try:
            run_example(name)
        except Exception as e:
            print(f"\nError in example '{name}': {e}")
            print("Continuing with next example...\n")

    print_banner("All Examples Complete")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run ZenML Dynamic Pipeline Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dynamic_examples.py                    # Run all examples
  python run_dynamic_examples.py --example parallel # Run parallel example
  python run_dynamic_examples.py --list             # List all examples
        """,
    )
    parser.add_argument(
        "--example",
        "-e",
        type=str,
        help="Run a specific example",
        choices=list(EXAMPLES.keys()),
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all available examples",
    )

    args = parser.parse_args()

    if args.list:
        list_examples()
    elif args.example:
        run_example(args.example)
    else:
        run_all_examples()


if __name__ == "__main__":
    main()
