"""Steps for evaluating prompts."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from zenml import step
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


class EvaluationResult(BaseModel):
    """Results from prompt evaluation."""

    prompt_template: str = Field(
        ..., description="Template that was evaluated"
    )
    accuracy: float = Field(default=0.0, description="Accuracy score")
    relevance: float = Field(default=0.0, description="Relevance score")
    fluency: float = Field(default=0.0, description="Fluency score")
    total_responses: int = Field(
        default=0, description="Total responses evaluated"
    )
    avg_response_time: float = Field(
        default=0.0, description="Average response time"
    )
    avg_tokens: int = Field(
        default=0, description="Average tokens per response"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


@step
def evaluate_prompt(
    prompt: Prompt,
    test_results: Dict[str, Any],
    human_scores: Optional[List[float]] = None,
) -> EvaluationResult:
    """Evaluate a prompt based on test results.

    Args:
        prompt: The prompt that was tested
        test_results: Results from testing the prompt
        human_scores: Optional human evaluation scores

    Returns:
        EvaluationResult with metrics
    """
    # Extract metrics from test results
    responses = test_results.get("responses", [])
    total_responses = len(responses)

    # Calculate basic metrics
    avg_response_time = sum(
        r.get("response_time", 0) for r in responses
    ) / max(total_responses, 1)
    avg_tokens = sum(r.get("token_count", 0) for r in responses) / max(
        total_responses, 1
    )

    # Calculate accuracy (example - this would depend on your specific evaluation)
    accuracy = test_results.get("accuracy", 0.0)

    # Use human scores if available
    relevance = sum(human_scores) / len(human_scores) if human_scores else 0.0

    # Simple fluency calculation (example)
    fluency = test_results.get("fluency", 0.0)

    result = EvaluationResult(
        prompt_template=prompt.template,
        accuracy=accuracy,
        relevance=relevance,
        fluency=fluency,
        total_responses=total_responses,
        avg_response_time=avg_response_time,
        avg_tokens=avg_tokens,
        metadata=test_results.get("metadata", {}),
    )

    logger.info(
        f"Evaluated prompt: accuracy={accuracy:.3f}, relevance={relevance:.3f}"
    )
    return result


@step
def calculate_prompt_complexity(prompt: Prompt) -> Dict[str, Any]:
    """Calculate complexity metrics for a prompt.

    Args:
        prompt: The prompt to analyze

    Returns:
        Dictionary with complexity metrics
    """
    template_length = len(prompt.template)
    variable_count = len(prompt.variables)
    unique_variables = len(prompt.get_variable_names())

    # Simple complexity score
    complexity_score = min(
        (template_length / 1000) * 0.5
        + (variable_count / 10) * 0.3
        + (unique_variables / 5) * 0.2,
        1.0,
    )

    return {
        "template_length": template_length,
        "variable_count": variable_count,
        "unique_variables": unique_variables,
        "complexity_score": complexity_score,
        "readability_score": 1.0 - complexity_score,  # Inverse of complexity
    }


@step
def estimate_prompt_cost(
    prompt: Prompt,
    model_pricing: Dict[str, float],
    expected_usage: Dict[str, int],
) -> Dict[str, Any]:
    """Estimate cost of using a prompt.

    Args:
        prompt: The prompt to estimate cost for
        model_pricing: Pricing per token for different models
        expected_usage: Expected usage patterns

    Returns:
        Dictionary with cost estimates
    """
    # Simple token estimation (4 chars per token)
    formatted_prompt = prompt.format(**prompt.variables)
    estimated_tokens = len(formatted_prompt) // 4

    # Calculate costs for different models
    cost_estimates = {}
    for model, price_per_token in model_pricing.items():
        daily_requests = expected_usage.get("daily_requests", 1000)
        monthly_cost = estimated_tokens * price_per_token * daily_requests * 30
        cost_estimates[model] = {
            "tokens_per_request": estimated_tokens,
            "cost_per_request": estimated_tokens * price_per_token,
            "monthly_cost": monthly_cost,
        }

    return {
        "estimated_tokens": estimated_tokens,
        "model_costs": cost_estimates,
        "optimization_suggestions": _get_cost_optimization_suggestions(
            estimated_tokens
        ),
    }


def _get_cost_optimization_suggestions(token_count: int) -> List[str]:
    """Get suggestions for optimizing prompt cost."""
    suggestions = []

    if token_count > 500:
        suggestions.append("Consider shortening the prompt template")

    if token_count > 1000:
        suggestions.append("Break down into smaller, focused prompts")

    suggestions.append("Use cheaper models for simple tasks")
    suggestions.append("Implement caching for repeated prompts")

    return suggestions
