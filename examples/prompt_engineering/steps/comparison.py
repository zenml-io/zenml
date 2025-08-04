"""Step for comparing different prompt versions using ZenML's core diff functionality."""

from zenml import step
from zenml.prompts import Prompt, compare_text_outputs


@step
def compare_prompt_versions(
    results_v1: dict, results_v2: dict, prompt_v1: Prompt, prompt_v2: Prompt
) -> dict:
    """Compare two prompt versions using ZenML's core diff functionality.

    Args:
        results_v1: Evaluation results from prompt v1 (includes outputs)
        results_v2: Evaluation results from prompt v2 (includes outputs)
        prompt_v1: The first prompt version
        prompt_v2: The second prompt version

    Returns:
        Comprehensive comparison with text diffs and output analysis
    """
    # Use ZenML's core diff functionality
    prompt_comparison = prompt_v1.diff(prompt_v2, "Prompt V1", "Prompt V2")

    # Compare actual outputs if available in results
    output_comparison = None
    if "outputs" in results_v1 and "outputs" in results_v2:
        output_comparison = compare_text_outputs(
            results_v1["outputs"],
            results_v2["outputs"],
            "V1 Outputs",
            "V2 Outputs",
        )

    # Add performance comparison
    v1_avg_length = results_v1["metrics"]["average_prompt_length"]
    v2_avg_length = results_v2["metrics"]["average_prompt_length"]

    # Combine ZenML's core comparison with additional analysis
    return {
        **prompt_comparison,  # Include all core diff analysis
        "output_comparison": output_comparison,
        "performance_metrics": {
            "v1_avg_prompt_length": v1_avg_length,
            "v2_avg_prompt_length": v2_avg_length,
            "length_difference": abs(v2_avg_length - v1_avg_length),
        },
        "v1_results": results_v1,
        "v2_results": results_v2,
        "enhanced_summary": {
            **prompt_comparison["summary"],  # Include core summary
            "output_similarity": output_comparison["aggregate_stats"][
                "average_similarity"
            ]
            if output_comparison and output_comparison["comparable"]
            else None,
            "performance_change": "improved"
            if v2_avg_length > v1_avg_length
            else "similar",
        },
    }
