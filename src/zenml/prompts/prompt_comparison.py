#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Simple prompt comparison utilities for A/B testing."""

from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


class PromptComparisonResult(BaseModel):
    """Result of comparing two prompts."""

    prompt_a_version: str
    prompt_b_version: str
    prompt_a_metrics: Dict[str, Any]
    prompt_b_metrics: Dict[str, Any]
    winner: Optional[str] = None
    comparison_summary: Dict[str, Any] = {}


def compare_prompts(
    prompt_a: Prompt,
    prompt_b: Prompt,
    test_cases: List[Dict[str, Any]],
    llm_function: Callable,
    metric_functions: Dict[str, Callable],
) -> PromptComparisonResult:
    """Compare two prompts using provided test cases and metrics.

    This is a simple utility for A/B testing prompts. It runs both prompts
    through the same test cases and compares the results using provided metrics.

    Args:
        prompt_a: First prompt to compare
        prompt_b: Second prompt to compare
        test_cases: List of test cases (each with variables for the prompts)
        llm_function: Function that takes formatted prompt and returns response
        metric_functions: Dictionary of metric names to metric calculation functions

    Returns:
        PromptComparisonResult with metrics and comparison

    Example:
        ```python
        def accuracy_metric(responses, ground_truth):
            # Calculate accuracy
            return 0.85

        def response_length_metric(responses, ground_truth):
            # Average response length
            return sum(len(r) for r in responses) / len(responses)

        result = compare_prompts(
            prompt_a=Prompt(template="Answer: {question}", version="1.0"),
            prompt_b=Prompt(template="Respond to: {question}", version="2.0"),
            test_cases=[{"question": "What is ML?"}, {"question": "What is AI?"}],
            llm_function=my_llm_call,
            metric_functions={
                "accuracy": accuracy_metric,
                "avg_length": response_length_metric
            }
        )
        ```
    """
    logger.info(
        f"Comparing prompts: v{prompt_a.version} vs v{prompt_b.version}"
    )

    # Run test cases for both prompts
    responses_a = []
    responses_b = []

    for test_case in test_cases:
        # Format and run prompt A
        try:
            formatted_a = prompt_a.format(**test_case)
            response_a = llm_function(formatted_a)
            responses_a.append(response_a)
        except Exception as e:
            logger.warning(f"Error with prompt A on test case: {e}")
            responses_a.append(None)

        # Format and run prompt B
        try:
            formatted_b = prompt_b.format(**test_case)
            response_b = llm_function(formatted_b)
            responses_b.append(response_b)
        except Exception as e:
            logger.warning(f"Error with prompt B on test case: {e}")
            responses_b.append(None)

    # Calculate metrics for both prompts
    metrics_a = {}
    metrics_b = {}

    for metric_name, metric_fn in metric_functions.items():
        try:
            metrics_a[metric_name] = metric_fn(responses_a, test_cases)
            metrics_b[metric_name] = metric_fn(responses_b, test_cases)
        except Exception as e:
            logger.warning(f"Error calculating metric {metric_name}: {e}")
            metrics_a[metric_name] = None
            metrics_b[metric_name] = None

    # Determine winner (simple: count which prompt wins more metrics)
    wins_a = 0
    wins_b = 0
    comparison_details = {}

    for metric_name in metric_functions:
        val_a = metrics_a.get(metric_name)
        val_b = metrics_b.get(metric_name)

        if val_a is not None and val_b is not None:
            if isinstance(val_a, (int, float)) and isinstance(
                val_b, (int, float)
            ):
                if val_a > val_b:
                    wins_a += 1
                    comparison_details[metric_name] = "A"
                elif val_b > val_a:
                    wins_b += 1
                    comparison_details[metric_name] = "B"
                else:
                    comparison_details[metric_name] = "Tie"

    winner = None
    if wins_a > wins_b:
        winner = "A"
    elif wins_b > wins_a:
        winner = "B"

    return PromptComparisonResult(
        prompt_a_version=prompt_a.version,
        prompt_b_version=prompt_b.version,
        prompt_a_metrics=metrics_a,
        prompt_b_metrics=metrics_b,
        winner=winner,
        comparison_summary={
            "total_metrics": len(metric_functions),
            "wins_a": wins_a,
            "wins_b": wins_b,
            "metric_winners": comparison_details,
            "test_cases_count": len(test_cases),
        },
    )


def run_prompt_comparison_pipeline(
    pipeline_func: Callable,
    prompts: List[Prompt],
    pipeline_args: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, Any]]:
    """Run the same pipeline with different prompts for comparison.

    This utility makes it easy to trigger experimental runs with different
    prompts, which can then be compared in the dashboard.

    Args:
        pipeline_func: The pipeline function to run
        prompts: List of prompts to test
        pipeline_args: Additional arguments for the pipeline

    Returns:
        List of tuples (prompt_version, pipeline_run)

    Example:
        ```python
        prompts_to_test = [
            Prompt(template="Be concise: {question}", version="1.0"),
            Prompt(template="Be detailed: {question}", version="2.0"),
        ]

        runs = run_prompt_comparison_pipeline(
            pipeline_func=my_llm_pipeline,
            prompts=prompts_to_test,
            pipeline_args={"test_data": my_dataset}
        )

        # Dashboard will show both runs with their prompt versions
        ```
    """
    runs = []
    pipeline_args = pipeline_args or {}

    for prompt in prompts:
        logger.info(f"Running pipeline with prompt v{prompt.version}")
        try:
            # Run pipeline with this prompt
            run = pipeline_func(prompt=prompt, **pipeline_args)
            runs.append((prompt.version, run))
        except Exception as e:
            logger.error(
                f"Failed to run pipeline with prompt v{prompt.version}: {e}"
            )
            runs.append((prompt.version, None))

    logger.info(f"Completed {len(runs)} comparison runs")
    return runs
