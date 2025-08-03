"""Step for creating prompt versions."""

from typing import Tuple

from zenml import step
from zenml.prompts import Prompt


@step
def create_prompt_versions() -> Tuple[Prompt, Prompt]:
    """Create two versions of a prompt for comparison.
    
    Returns:
        Tuple of (prompt_v1, prompt_v2) for A/B testing
    """
    prompt_v1 = Prompt(
        template="Answer: {question}",
        version="1.0",
        variables={"question": "What is machine learning?"}
    )
    
    prompt_v2 = Prompt(
        template="Please provide a detailed answer: {question}",
        version="2.0", 
        variables={"question": "What is machine learning?"}
    )
    
    return prompt_v1, prompt_v2


@step
def create_single_prompt(
    template: str = "Answer: {question}",
    version: str = "1.0"
) -> Prompt:
    """Create a single prompt with given template and version.
    
    Args:
        template: The prompt template string
        version: Version identifier for the prompt
        
    Returns:
        Configured Prompt artifact
    """
    return Prompt(
        template=template,
        version=version,
        variables={"question": "What is machine learning?"}
    )