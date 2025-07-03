"""Example pipeline demonstrating prompt evaluation using LLM-as-Judge methodology.

This pipeline shows how to use ZenML's LLM-as-Judge evaluation steps to
systematically assess prompt quality and compare different prompt versions.
"""

from typing import Dict, List, Any
from zenml import pipeline, step
from zenml.steps.prompt_evaluation import (
    llm_judge_evaluate_prompt,
    compare_prompt_versions
)


@step
def prepare_test_cases() -> List[Dict[str, Any]]:
    """Prepare test cases for prompt evaluation."""
    return [
        {
            "variables": {
                "question": "What is machine learning?",
                "context": "The user is a beginner with no technical background"
            },
            "expected_output": "A clear, beginner-friendly explanation of machine learning"
        },
        {
            "variables": {
                "question": "How do neural networks work?", 
                "context": "The user has some programming experience but is new to ML"
            },
            "expected_output": "Technical explanation with code examples"
        },
        {
            "variables": {
                "question": "What are the ethical implications of AI?",
                "context": "The user is interested in the societal impact of AI"
            },
            "expected_output": "Balanced discussion of AI ethics and societal impacts"
        }
    ]


@step
def define_evaluation_criteria() -> List[str]:
    """Define criteria for prompt evaluation."""
    return [
        "relevance",      # How relevant is the response to the question
        "accuracy",       # Technical accuracy of the information
        "clarity",        # How clear and understandable the response is
        "completeness",   # How complete the response is
        "helpfulness",    # How helpful the response is to the user
        "safety"          # Whether the response is safe and appropriate
    ]


@step
def evaluate_single_prompt(
    prompt_artifact_id: str,
    test_cases: List[Dict[str, Any]],
    criteria: List[str]
) -> Dict[str, Any]:
    """Evaluate a single prompt artifact."""
    return llm_judge_evaluate_prompt(
        prompt_artifact_id=prompt_artifact_id,
        test_cases=test_cases,
        evaluation_criteria=criteria,
        judge_model="gpt-4",
        temperature=0.1
    )


@step
def compare_two_prompts(
    prompt_v1_id: str,
    prompt_v2_id: str,
    test_cases: List[Dict[str, Any]],
    criteria: List[str]
) -> Dict[str, Any]:
    """Compare two prompt versions."""
    return compare_prompt_versions(
        prompt_v1_id=prompt_v1_id,
        prompt_v2_id=prompt_v2_id,
        test_cases=test_cases,
        evaluation_criteria=criteria,
        judge_model="gpt-4"
    )


@step
def generate_evaluation_report(
    evaluation_results: List[Dict[str, Any]],
    comparison_results: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a comprehensive evaluation report."""
    
    report = {
        "evaluation_summary": {
            "total_prompts_evaluated": len(evaluation_results),
            "average_overall_score": sum(r["overall_score"] for r in evaluation_results) / len(evaluation_results),
            "evaluations": evaluation_results
        }
    }
    
    if comparison_results:
        report["comparison_summary"] = {
            "total_comparisons": len(comparison_results),
            "comparisons": comparison_results
        }
        
        # Identify best performing prompts
        winners = {}
        for comp in comparison_results:
            winner = comp["winner"]
            if winner != "tie":
                winner_id = comp[f"prompt_{winner}_id"]
                if winner_id not in winners:
                    winners[winner_id] = 0
                winners[winner_id] += 1
        
        if winners:
            best_prompt = max(winners.keys(), key=lambda k: winners[k])
            report["recommendations"] = {
                "best_performing_prompt": best_prompt,
                "win_count": winners[best_prompt]
            }
    
    return report


@pipeline
def prompt_evaluation_pipeline(
    prompt_ids: List[str],
    comparison_pairs: List[tuple] = None
) -> Dict[str, Any]:
    """Pipeline for comprehensive prompt evaluation.
    
    Args:
        prompt_ids: List of prompt artifact IDs to evaluate
        comparison_pairs: Optional list of (prompt_id1, prompt_id2) tuples for comparison
        
    Returns:
        Comprehensive evaluation report
    """
    
    # Prepare evaluation data
    test_cases = prepare_test_cases()
    criteria = define_evaluation_criteria()
    
    # Evaluate individual prompts
    evaluation_results = []
    for prompt_id in prompt_ids:
        result = evaluate_single_prompt(
            prompt_artifact_id=prompt_id,
            test_cases=test_cases,
            criteria=criteria
        )
        evaluation_results.append(result)
    
    # Perform comparisons if specified
    comparison_results = []
    if comparison_pairs:
        for prompt1_id, prompt2_id in comparison_pairs:
            comparison = compare_two_prompts(
                prompt_v1_id=prompt1_id,
                prompt_v2_id=prompt2_id,
                test_cases=test_cases,
                criteria=criteria
            )
            comparison_results.append(comparison)
    
    # Generate final report
    report = generate_evaluation_report(
        evaluation_results=evaluation_results,
        comparison_results=comparison_results if comparison_results else None
    )
    
    return report


if __name__ == "__main__":
    # Example usage
    from zenml.client import Client
    
    client = Client()
    
    # Get some prompt artifacts from your project
    # Replace with actual prompt artifact IDs
    prompt_artifacts = client.list_artifacts(
        artifact_name="my_prompt_template", 
        artifact_type="prompt"
    )
    
    if len(prompt_artifacts.items) >= 2:
        prompt_ids = [artifact.id for artifact in prompt_artifacts.items[:3]]
        comparison_pairs = [(prompt_ids[0], prompt_ids[1])]
        
        # Run the evaluation pipeline
        evaluation_report = prompt_evaluation_pipeline(
            prompt_ids=prompt_ids,
            comparison_pairs=comparison_pairs
        )
        
        print("Evaluation Report:")
        print(f"Average Score: {evaluation_report['evaluation_summary']['average_overall_score']:.2f}")
        
        if "recommendations" in evaluation_report:
            best_prompt = evaluation_report["recommendations"]["best_performing_prompt"]
            print(f"Best Performing Prompt: {best_prompt}")
    else:
        print("Need at least 2 prompt artifacts to run this example")
        print("Create some prompt artifacts first using ZenML's artifact system")