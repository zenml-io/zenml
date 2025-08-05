"""Pipeline for comparing different prompt versions on the same task."""

from steps.comparison import compare_prompt_versions
from steps.data_loading import load_sample_articles
from steps.evaluation import evaluate_summaries
from steps.prompt_processing import (
    apply_prompt_to_text,
    create_summarization_prompt_v1,
    create_summarization_prompt_v2,
)

from zenml import pipeline


@pipeline
def prompt_version_comparison() -> dict:
    """Compare different versions of prompts on the same task.

    This shows:
    1. Same real task (text summarization)
    2. Two different prompt versions (v1.0 vs v2.0)
    3. Side-by-side comparison of results
    4. Which version works better for the task
    """
    # Load the same articles for both versions
    articles = load_sample_articles()

    # Create two different versions of the summarization prompt
    # Each will be automatically versioned by ZenML as separate artifacts
    prompt_v1 = create_summarization_prompt_v1()
    prompt_v2 = create_summarization_prompt_v2()

    # Apply both prompts to the same articles
    summaries_v1 = apply_prompt_to_text(prompt=prompt_v1, texts=articles)
    summaries_v2 = apply_prompt_to_text(prompt=prompt_v2, texts=articles)

    # Evaluate both versions
    results_v1 = evaluate_summaries(
        original_texts=articles, summaries=summaries_v1, prompt_used=prompt_v1
    )

    results_v2 = evaluate_summaries(
        original_texts=articles, summaries=summaries_v2, prompt_used=prompt_v2
    )

    # Compare the two versions
    comparison = compare_prompt_versions(
        results_v1=results_v1,
        results_v2=results_v2,
        prompt_v1=prompt_v1,
        prompt_v2=prompt_v2,
    )

    return comparison
