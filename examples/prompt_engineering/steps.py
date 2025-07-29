"""Simplified steps for prompt engineering pipelines."""

from typing import Annotated, Any, Dict, List, Optional

from zenml import step
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


@step
def create_prompt_step(
    template: str,
    prompt_type: str = "user",
    variables: Optional[Dict[str, Any]] = None,
) -> Annotated[Prompt, "created_prompt"]:
    """Create a new prompt artifact.

    Args:
        template: The prompt template string
        prompt_type: Type of prompt (system, user, assistant)
        variables: Default variable values

    Returns:
        Created Prompt artifact
    """
    prompt = Prompt(
        template=template,
        prompt_type=prompt_type,
        variables=variables or {},
    )

    logger.info(f"Created prompt: {prompt}")
    return prompt


@step
def load_test_dataset_step(
    dataset_name: str = "default",
) -> Annotated[List[Dict[str, Any]], "test_dataset"]:
    """Load test dataset for prompt evaluation.

    Args:
        dataset_name: Name of the dataset to load

    Returns:
        List of test cases
    """
    # Example test cases - in practice, load from file or database
    test_cases = [
        {"question": "What is machine learning?"},
        {"question": "How does gradient descent work?"},
        {"question": "What are neural networks?"},
        {"question": "Explain overfitting in ML"},
        {
            "question": "What is the difference between supervised and unsupervised learning?"
        },
    ]

    logger.info(f"Loaded {len(test_cases)} test cases")
    return test_cases


@step
def test_prompt_with_llm_step(
    prompt: Prompt,
    test_cases: List[Dict[str, Any]],
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> Annotated[Dict[str, Any], "llm_test_results"]:
    """Test a prompt with an LLM.

    Args:
        prompt: The prompt to test
        test_cases: Test cases to run
        model: LLM model to use
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate

    Returns:
        Test results including responses and metrics
    """
    # Mock implementation - replace with actual LLM calls
    responses = []

    for case in test_cases:
        try:
            formatted_prompt = prompt.format(**case)

            # Mock LLM response
            response = {
                "input": case,
                "formatted_prompt": formatted_prompt,
                "response": f"Mock response for: {case.get('question', 'N/A')}",
                "response_time": 1.2,
                "token_count": 50,
                "model": model,
            }
            responses.append(response)

        except Exception as e:
            logger.error(f"Error processing test case {case}: {e}")
            responses.append(
                {
                    "input": case,
                    "error": str(e),
                    "response": None,
                }
            )

    results = {
        "prompt_template": prompt.template,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "responses": responses,
        "success_rate": len([r for r in responses if "error" not in r])
        / len(responses),
        "avg_response_time": sum(r.get("response_time", 0) for r in responses)
        / len(responses),
        "avg_tokens": sum(r.get("token_count", 0) for r in responses)
        / len(responses),
    }

    logger.info(
        f"Tested prompt with {len(responses)} cases, success rate: {results['success_rate']:.2f}"
    )
    return results


@step
def evaluate_prompt_step(
    prompt: Prompt,
    test_results: Dict[str, Any],
) -> Annotated[Dict[str, Any], "evaluation_metrics"]:
    """Evaluate prompt performance.

    Args:
        prompt: The prompt that was tested
        test_results: Results from testing

    Returns:
        Evaluation metrics
    """
    responses = test_results.get("responses", [])
    success_count = len([r for r in responses if "error" not in r])

    # Simple evaluation metrics
    metrics = {
        "accuracy": success_count / len(responses) if responses else 0,
        "success_rate": test_results.get("success_rate", 0),
        "avg_response_time": test_results.get("avg_response_time", 0),
        "avg_tokens": test_results.get("avg_tokens", 0),
        "total_responses": len(responses),
        "template_length": len(prompt.template),
        "variable_count": len(prompt.variables),
    }

    logger.info(f"Evaluated prompt: accuracy={metrics['accuracy']:.3f}")
    return metrics


@step
def llm_judge_evaluate_step(
    prompt: Prompt,
    test_results: Dict[str, Any],
    judge_model: str = "gpt-4",
) -> Annotated[Dict[str, Any], "judge_evaluation"]:
    """Use LLM as judge to evaluate prompt responses.

    Args:
        prompt: The prompt that was tested
        test_results: Results from testing
        judge_model: Model to use as judge

    Returns:
        Judge evaluation results
    """
    # Mock implementation - replace with actual LLM judge calls
    responses = test_results.get("responses", [])
    judge_scores = []

    for response in responses:
        if "error" not in response:
            # Mock judge scoring
            judge_score = {
                "relevance": 0.8,
                "accuracy": 0.7,
                "helpfulness": 0.9,
                "overall": 0.8,
            }
            judge_scores.append(judge_score)

    # Calculate averages
    if judge_scores:
        avg_scores = {
            "relevance": sum(s["relevance"] for s in judge_scores)
            / len(judge_scores),
            "accuracy": sum(s["accuracy"] for s in judge_scores)
            / len(judge_scores),
            "helpfulness": sum(s["helpfulness"] for s in judge_scores)
            / len(judge_scores),
            "overall": sum(s["overall"] for s in judge_scores)
            / len(judge_scores),
        }
    else:
        avg_scores = {
            "relevance": 0,
            "accuracy": 0,
            "helpfulness": 0,
            "overall": 0,
        }

    evaluation = {
        "judge_model": judge_model,
        "individual_scores": judge_scores,
        "average_scores": avg_scores,
        "evaluated_responses": len(judge_scores),
    }

    logger.info(f"LLM judge evaluation: overall={avg_scores['overall']:.3f}")
    return evaluation


@step
def select_best_prompt_step(
    prompts: List[Prompt],
    evaluations: List[Dict[str, Any]],
    metric: str = "accuracy",
) -> Annotated[Prompt, "best_prompt"]:
    """Select the best prompt based on evaluation metrics.

    Args:
        prompts: List of prompts that were evaluated
        evaluations: List of evaluation results
        metric: Metric to use for selection

    Returns:
        The best performing prompt
    """
    if len(prompts) != len(evaluations):
        raise ValueError("Number of prompts and evaluations must match")

    best_idx = 0
    best_score = evaluations[0].get(metric, 0)

    for i, eval_result in enumerate(evaluations):
        score = eval_result.get(metric, 0)
        if score > best_score:
            best_score = score
            best_idx = i

    best_prompt = prompts[best_idx]
    logger.info(f"Selected best prompt with {metric}={best_score:.3f}")

    return best_prompt
