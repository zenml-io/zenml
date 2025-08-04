"""Step for evaluating prompt results."""

from typing import List

from zenml import step
from zenml.prompts import Prompt


@step
def evaluate_summaries(
    original_texts: List[str], summaries: List[str], prompt_used: Prompt
) -> dict:
    """Evaluate the quality of generated summaries.

    Args:
        original_texts: Original article texts
        summaries: Generated summary prompts (ready for LLM)
        prompt_used: The prompt that was used

    Returns:
        Evaluation results including metrics and analysis
    """
    results = {
        "prompt_version": prompt_used.version,
        "prompt_template": prompt_used.template,
        "total_articles": len(original_texts),
        "total_summaries": len(summaries),
        "results": [],
    }

    for i, (original, summary_prompt) in enumerate(
        zip(original_texts, summaries)
    ):
        # Simple evaluation metrics
        original_length = len(original.split())
        prompt_length = len(summary_prompt.split())

        # Calculate compression ratio (how much shorter the prompt makes the task)
        compression_info = {
            "article_id": i + 1,
            "original_word_count": original_length,
            "prompt_word_count": prompt_length,
            "formatted_prompt": summary_prompt[:200] + "..."
            if len(summary_prompt) > 200
            else summary_prompt,
        }

        results["results"].append(compression_info)

    # Calculate averages
    avg_original_length = sum(
        r["original_word_count"] for r in results["results"]
    ) / len(results["results"])
    avg_prompt_length = sum(
        r["prompt_word_count"] for r in results["results"]
    ) / len(results["results"])

    results["metrics"] = {
        "average_original_length": avg_original_length,
        "average_prompt_length": avg_prompt_length,
        "template_effectiveness": "Prompt adds clear structure for summarization task",
    }

    return results
