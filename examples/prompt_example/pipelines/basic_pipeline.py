"""Basic prompt pipeline demonstrating core prompt functionality."""

from steps.evaluation import evaluate_prompt_response
from steps.llm_simulation import simulate_llm_response
from steps.prompt_creation import create_basic_prompt

from zenml import pipeline
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.types import Prompt


@pipeline(name="basic_prompt_pipeline")
def basic_prompt_pipeline() -> None:
    """Basic pipeline showing prompt creation, usage, and evaluation."""

    # Create a prompt
    prompt = create_basic_prompt()

    # Simulate LLM response
    response = simulate_llm_response(prompt)

    # Evaluate the response
    evaluation = evaluate_prompt_response(prompt, response)


@pipeline(name="basic_prompt_pipeline_with_external")
def basic_prompt_pipeline_with_external(
    external_prompt: ExternalArtifact[Prompt],
) -> None:
    """Basic pipeline using external prompt artifact."""

    # Use external prompt
    response = simulate_llm_response(external_prompt)

    # Evaluate the response
    evaluation = evaluate_prompt_response(external_prompt, response)
