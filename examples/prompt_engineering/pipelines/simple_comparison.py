"""Simple prompt comparison pipeline - the core use case."""

from steps.prompt_creation import create_prompt_versions
from steps.prompt_testing import compare_prompt_versions

from zenml import pipeline
from zenml.prompts import Prompt


@pipeline
def simple_prompt_comparison() -> dict:
    """Simple pipeline demonstrating the core prompt engineering workflow
        1. Create versioned prompts.
        2. Compare them with A/B testing.
        3. Show results in dashboard.
    
    Returns:
        Comparison results with winner determination
    """
    # Create two prompt versions for comparison
    prompt_v1, prompt_v2 = create_prompt_versions()
    
    # Compare the prompts and determine winner
    comparison_results = compare_prompt_versions(prompt_v1, prompt_v2)
    
    return comparison_results