"""Steps for comparing prompts."""

import difflib
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from zenml import step
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


class PromptComparison(BaseModel):
    """Comparison results between two prompts."""

    prompt1_template: str = Field(..., description="First prompt template")
    prompt2_template: str = Field(..., description="Second prompt template")
    similarity_score: float = Field(..., description="Similarity score 0-1")
    common_variables: List[str] = Field(default_factory=list)
    unique_to_first: List[str] = Field(default_factory=list)
    unique_to_second: List[str] = Field(default_factory=list)
    diff_lines: List[str] = Field(default_factory=list)


@step
def compare_prompts(
    prompt1: Prompt,
    prompt2: Prompt,
) -> PromptComparison:
    """Compare two prompts and return detailed comparison.

    Args:
        prompt1: First prompt to compare
        prompt2: Second prompt to compare

    Returns:
        PromptComparison with detailed comparison results
    """
    # Calculate similarity
    similarity = difflib.SequenceMatcher(
        None, prompt1.template, prompt2.template
    ).ratio()

    # Compare variables
    vars1 = set(prompt1.get_variable_names())
    vars2 = set(prompt2.get_variable_names())

    common_vars = list(vars1 & vars2)
    unique_to_first = list(vars1 - vars2)
    unique_to_second = list(vars2 - vars1)

    # Generate diff
    diff_lines = list(
        difflib.unified_diff(
            prompt1.template.splitlines(),
            prompt2.template.splitlines(),
            fromfile="prompt1",
            tofile="prompt2",
            lineterm="",
        )
    )

    comparison = PromptComparison(
        prompt1_template=prompt1.template,
        prompt2_template=prompt2.template,
        similarity_score=similarity,
        common_variables=common_vars,
        unique_to_first=unique_to_first,
        unique_to_second=unique_to_second,
        diff_lines=diff_lines,
    )

    logger.info(f"Compared prompts: {similarity:.2f} similarity")
    return comparison


@step
def compare_multiple_prompts(
    prompts: List[Prompt],
) -> List[PromptComparison]:
    """Compare multiple prompts pairwise.

    Args:
        prompts: List of prompts to compare

    Returns:
        List of pairwise comparisons
    """
    comparisons = []

    for i in range(len(prompts)):
        for j in range(i + 1, len(prompts)):
            comparison = compare_prompts(prompts[i], prompts[j])
            comparisons.append(comparison)

    logger.info(f"Generated {len(comparisons)} pairwise comparisons")
    return comparisons


@step
def select_best_prompt(
    prompts: List[Prompt],
    evaluation_results: List[Dict[str, Any]],
    metric: str = "accuracy",
) -> Prompt:
    """Select the best prompt based on evaluation results.

    Args:
        prompts: List of prompts that were evaluated
        evaluation_results: List of evaluation results for each prompt
        metric: Metric to use for selection

    Returns:
        The best performing prompt
    """
    if len(prompts) != len(evaluation_results):
        raise ValueError("Number of prompts and evaluation results must match")

    best_idx = 0
    best_score = evaluation_results[0].get(metric, 0)

    for i, result in enumerate(evaluation_results):
        score = result.get(metric, 0)
        if score > best_score:
            best_score = score
            best_idx = i

    best_prompt = prompts[best_idx]
    logger.info(f"Selected best prompt with {metric}={best_score:.3f}")

    return best_prompt
