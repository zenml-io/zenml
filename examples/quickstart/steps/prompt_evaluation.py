"""LLM-as-Judge evaluation steps for prompt quality assessment.

This module provides ZenML steps for evaluating prompt quality using the
LLM-as-Judge methodology. It enables automated evaluation of prompt templates
based on multiple criteria such as relevance, accuracy, clarity, and safety.

Example usage:
    from zenml.steps.prompt_evaluation import llm_judge_evaluate_prompt

    # Define test cases
    test_cases = [
        {
            "variables": {"question": "What is ML?", "context": "beginner level"},
            "expected_output": "Machine learning explanation..."
        }
    ]

    # Evaluate prompt
    evaluation = llm_judge_evaluate_prompt(
        prompt_artifact_id="prompt-123",
        test_cases=test_cases,
        evaluation_criteria=["relevance", "clarity", "accuracy"]
    )
"""

from typing import Any, Dict, List

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def llm_judge_evaluate_prompt(
    prompt_artifact_id: str,
    test_cases: List[Dict[str, Any]],
    evaluation_criteria: List[str] = None,
    judge_model: str = "gpt-4",
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Evaluate a prompt using LLM-as-Judge methodology.

    Args:
        prompt_artifact_id: ID of the prompt artifact to evaluate
        test_cases: List of test cases with input variables and expected outputs
        evaluation_criteria: Criteria to evaluate (relevance, accuracy, clarity, etc.)
        judge_model: LLM model to use as judge
        temperature: Temperature for judge model

    Returns:
        Dictionary containing evaluation results and metrics
    """
    logger.info(
        f"Starting LLM-as-Judge evaluation for prompt {prompt_artifact_id}"
    )

    # Default evaluation criteria
    if evaluation_criteria is None:
        evaluation_criteria = [
            "relevance",
            "accuracy",
            "clarity",
            "helpfulness",
            "safety",
        ]

    client = Client()

    try:
        # Get the prompt artifact
        prompt_artifact = client.get_artifact(prompt_artifact_id)
        prompt_content = prompt_artifact.run_metadata.get("template", "")

        if not prompt_content:
            raise ValueError(
                f"No prompt template found in artifact {prompt_artifact_id}"
            )

        # Run evaluation for each test case
        evaluation_results = []
        total_scores = {criterion: 0.0 for criterion in evaluation_criteria}

        for i, test_case in enumerate(test_cases):
            logger.info(f"Evaluating test case {i + 1}/{len(test_cases)}")

            # Generate response using the prompt
            filled_prompt = _fill_prompt_template(
                prompt_content, test_case.get("variables", {})
            )

            # Get judge evaluation
            case_scores = _judge_response(
                prompt=filled_prompt,
                response=test_case.get("expected_output", ""),
                criteria=evaluation_criteria,
                judge_model=judge_model,
                temperature=temperature,
            )

            evaluation_results.append(
                {
                    "test_case_id": i,
                    "prompt": filled_prompt,
                    "expected_output": test_case.get("expected_output", ""),
                    "scores": case_scores,
                    "overall_score": sum(case_scores.values())
                    / len(case_scores),
                }
            )

            # Accumulate scores
            for criterion, score in case_scores.items():
                total_scores[criterion] += score

        # Calculate overall metrics
        num_cases = len(test_cases)
        average_scores = {
            criterion: total / num_cases
            for criterion, total in total_scores.items()
        }
        overall_score = sum(average_scores.values()) / len(average_scores)

        # Determine quality level
        quality_level = _get_quality_level(overall_score)

        evaluation_summary = {
            "prompt_artifact_id": prompt_artifact_id,
            "judge_model": judge_model,
            "test_cases_count": num_cases,
            "evaluation_criteria": evaluation_criteria,
            "average_scores": average_scores,
            "overall_score": overall_score,
            "quality_level": quality_level,
            "individual_results": evaluation_results,
            "recommendations": _generate_recommendations(
                average_scores, evaluation_results
            ),
        }

        logger.info(
            f"Evaluation complete. Overall score: {overall_score:.2f} ({quality_level})"
        )
        return evaluation_summary

    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        raise


@step
def compare_prompt_versions(
    prompt_v1_id: str,
    prompt_v2_id: str,
    test_cases: List[Dict[str, Any]],
    evaluation_criteria: List[str] = None,
    judge_model: str = "gpt-4",
) -> Dict[str, Any]:
    """
    Compare two prompt versions using LLM-as-Judge.

    Args:
        prompt_v1_id: First prompt artifact ID
        prompt_v2_id: Second prompt artifact ID
        test_cases: Test cases for comparison
        evaluation_criteria: Evaluation criteria
        judge_model: Judge model to use

    Returns:
        Comparison results with winner determination
    """
    logger.info(f"Comparing prompts {prompt_v1_id} vs {prompt_v2_id}")

    # Evaluate both versions
    eval_v1 = llm_judge_evaluate_prompt(
        prompt_v1_id, test_cases, evaluation_criteria, judge_model
    )
    eval_v2 = llm_judge_evaluate_prompt(
        prompt_v2_id, test_cases, evaluation_criteria, judge_model
    )

    # Determine winner
    v1_score = eval_v1["overall_score"]
    v2_score = eval_v2["overall_score"]

    if v1_score > v2_score:
        winner = "v1"
        improvement = ((v1_score - v2_score) / v2_score) * 100
    elif v2_score > v1_score:
        winner = "v2"
        improvement = ((v2_score - v1_score) / v1_score) * 100
    else:
        winner = "tie"
        improvement = 0.0

    comparison_result = {
        "prompt_v1_id": prompt_v1_id,
        "prompt_v2_id": prompt_v2_id,
        "v1_evaluation": eval_v1,
        "v2_evaluation": eval_v2,
        "winner": winner,
        "improvement_percentage": improvement,
        "score_difference": abs(v1_score - v2_score),
        "detailed_comparison": _create_detailed_comparison(eval_v1, eval_v2),
    }

    logger.info(
        f"Comparison complete. Winner: {winner} with {improvement:.1f}% improvement"
    )
    return comparison_result


def _fill_prompt_template(template: str, variables: Dict[str, str]) -> str:
    """Fill prompt template with variables."""
    filled = template
    for key, value in variables.items():
        filled = filled.replace(f"{{{key}}}", str(value))
    return filled


def _judge_response(
    prompt: str,
    response: str,
    criteria: List[str],
    judge_model: str,
    temperature: float,
) -> Dict[str, float]:
    """Use LLM to judge response quality based on criteria."""

    # Create judge prompt
    judge_prompt = f"""You are an expert evaluator for AI-generated content. 
    
Please evaluate the following response based on these criteria: {", ".join(criteria)}

Original Prompt: {prompt}

Response to Evaluate: {response}

For each criterion, provide a score from 0-10 where:
- 0-2: Poor
- 3-4: Below Average  
- 5-6: Average
- 7-8: Good
- 9-10: Excellent

Respond with ONLY a JSON object containing scores for each criterion:
{{"relevance": X.X, "accuracy": X.X, "clarity": X.X, "helpfulness": X.X, "safety": X.X}}"""

    # TODO: Replace with actual LLM API integration
    # Example integration with OpenAI or other LLM providers:
    #
    # from openai import OpenAI
    # client = OpenAI()
    # response = client.chat.completions.create(
    #     model=judge_model,
    #     messages=[{"role": "user", "content": judge_prompt}],
    #     temperature=temperature
    # )
    #
    # try:
    #     scores = json.loads(response.choices[0].message.content)
    #     return scores
    # except json.JSONDecodeError:
    #     logger.warning("Failed to parse LLM judge response as JSON")
    #     return {criterion: 5.0 for criterion in criteria}  # fallback scores

    # Mock scores for development - replace with actual implementation
    import random

    random.seed(hash(prompt + response))  # Consistent scores for same input
    mock_scores = {}
    for criterion in criteria:
        mock_scores[criterion] = random.uniform(6.0, 9.5)

    return mock_scores


def _get_quality_level(score: float) -> str:
    """Determine quality level from score."""
    if score >= 8.5:
        return "Excellent"
    elif score >= 7.0:
        return "Good"
    elif score >= 5.5:
        return "Average"
    elif score >= 3.5:
        return "Below Average"
    else:
        return "Poor"


def _generate_recommendations(
    scores: Dict[str, float], results: List[Dict]
) -> List[str]:
    """Generate improvement recommendations based on evaluation."""
    recommendations = []

    # Identify weakest criteria
    sorted_scores = sorted(scores.items(), key=lambda x: x[1])
    weakest_criterion = sorted_scores[0]

    if weakest_criterion[1] < 6.0:
        recommendations.append(
            f"Focus on improving {weakest_criterion[0]} (current score: {weakest_criterion[1]:.1f})"
        )

    # Check for consistency issues
    score_variance = max(scores.values()) - min(scores.values())
    if score_variance > 2.0:
        recommendations.append(
            "Consider balancing the prompt to address inconsistent performance across criteria"
        )

    # Overall score recommendations
    avg_score = sum(scores.values()) / len(scores)
    if avg_score < 7.0:
        recommendations.append(
            "Overall prompt quality could be improved with more specific instructions"
        )

    return recommendations


def _create_detailed_comparison(
    eval_v1: Dict, eval_v2: Dict
) -> Dict[str, Any]:
    """Create detailed comparison between two evaluations."""
    comparison = {}

    v1_scores = eval_v1["average_scores"]
    v2_scores = eval_v2["average_scores"]

    for criterion in v1_scores.keys():
        score_diff = v2_scores[criterion] - v1_scores[criterion]
        comparison[criterion] = {
            "v1_score": v1_scores[criterion],
            "v2_score": v2_scores[criterion],
            "difference": score_diff,
            "winner": "v2"
            if score_diff > 0
            else "v1"
            if score_diff < 0
            else "tie",
        }

    return comparison
