"""Simple text summarization pipeline using prompts."""

from steps.data_loading import load_sample_articles
from steps.evaluation import evaluate_summaries
from steps.prompt_processing import (
    apply_prompt_to_text,
    create_summarization_prompt_v1,
)

from zenml import pipeline


@pipeline
def text_summarization_pipeline() -> dict:
    """
    Simple pipeline that demonstrates real prompt usage:
    1. Load some sample articles
    2. Create a summarization prompt (versioned)
    3. Apply prompt to generate summaries
    4. Evaluate the results

    This shows prompts being used for actual work, not just comparison.
    """
    # Load sample articles to summarize
    articles = load_sample_articles()

    # Create a prompt for summarization (ZenML will auto-version this as artifact)
    summarization_prompt = create_summarization_prompt_v1()

    # Apply the prompt to generate summaries
    summaries = apply_prompt_to_text(
        prompt=summarization_prompt, texts=articles
    )

    # Evaluate the quality of summaries
    evaluation_results = evaluate_summaries(
        original_texts=articles,
        summaries=summaries,
        prompt_used=summarization_prompt,
    )

    return evaluation_results
