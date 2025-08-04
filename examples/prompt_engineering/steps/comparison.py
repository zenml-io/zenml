"""Step for comparing different prompt versions."""

from zenml import step
from zenml.prompts import Prompt


@step
def compare_prompt_versions(
    results_v1: dict, results_v2: dict, prompt_v1: Prompt, prompt_v2: Prompt
) -> dict:
    """Compare two prompt versions based on their evaluation results.

    Args:
        results_v1: Evaluation results from prompt v1
        results_v2: Evaluation results from prompt v2
        prompt_v1: The first prompt version
        prompt_v2: The second prompt version

    Returns:
        Comparison results with winner determination
    """
    v1_avg_length = results_v1["metrics"]["average_prompt_length"]
    v2_avg_length = results_v2["metrics"]["average_prompt_length"]

    # Simple comparison: more structured prompt (longer) might be better
    # In practice, you'd use actual LLM evaluation or human feedback
    winner = "v2.0" if v2_avg_length > v1_avg_length else "v1.0"
    winner_prompt = prompt_v2 if winner == "v2.0" else prompt_v1

    return {
        "prompt_v1": prompt_v1,  # Dashboard visualization
        "prompt_v2": prompt_v2,  # Dashboard visualization
        "winner": winner,
        "winner_prompt": winner_prompt,
        "comparison_metrics": {
            "v1_avg_prompt_length": v1_avg_length,
            "v2_avg_prompt_length": v2_avg_length,
            "length_difference": abs(v2_avg_length - v1_avg_length),
        },
        "v1_results": results_v1,
        "v2_results": results_v2,
        "conclusion": f"Prompt {winner} provides better structure for summarization task",
    }
