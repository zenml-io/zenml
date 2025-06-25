"""Prompt comparison pipeline for A/B testing different prompt variants."""

from steps.comparison import analyze_best_prompt, compare_prompt_variants
from steps.evaluation import evaluate_multiple_responses
from steps.llm_simulation import simulate_multiple_responses
from steps.prompt_creation import create_prompt_variants

from zenml import pipeline


@pipeline(name="prompt_comparison_pipeline")
def prompt_comparison_pipeline(num_variants: int = 3) -> None:
    """Pipeline for comparing multiple prompt variants."""

    # Create prompt variants
    variants = create_prompt_variants(num_variants=num_variants)

    # Simulate responses for all variants
    responses = simulate_multiple_responses(variants)

    # Evaluate all responses
    evaluations = evaluate_multiple_responses(variants, responses)

    # Compare variants and find best
    comparison = compare_prompt_variants(variants, responses, evaluations)

    # Analyze best performing prompt
    best_analysis = analyze_best_prompt(comparison)
