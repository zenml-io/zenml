"""Simple example demonstrating prompt versioning, comparison, and dashboard visualization.

This example shows the three core features users want:
1. Prompts as first-class objects with versions
2. Easy A/B comparison of different prompts
3. Dashboard visualization of prompt versions in runs
"""

from typing import Any, Dict, List

from zenml import pipeline, step
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


@step
def create_prompt_versions() -> List[Prompt]:
    """Create different versions of prompts for comparison."""
    prompts = [
        Prompt(
            template="You are a helpful assistant. Answer this question concisely: {question}",
            version="1.0.0",
            prompt_type="system",
        ),
        Prompt(
            template="Please provide a detailed and comprehensive answer to: {question}",
            version="2.0.0",
            prompt_type="user",
        ),
        Prompt(
            template="Question: {question}\n\nProvide a balanced answer with examples.",
            version="3.0.0",
            prompt_type="user",
        ),
    ]

    logger.info(f"Created {len(prompts)} prompt versions for comparison")
    return prompts


@step
def test_prompt_with_llm(
    prompt: Prompt,
    test_questions: List[str],
) -> Dict[str, Any]:
    """Test a single prompt with sample questions.

    In a real scenario, this would call an actual LLM API.
    """
    results = []

    for question in test_questions:
        # Format the prompt
        formatted = prompt.format(question=question)

        # In real usage, you would call your LLM here
        # response = llm.generate(formatted)

        # For demo purposes, simulate a response
        response = (
            f"[Mock response for v{prompt.version}] Answer to: {question}"
        )

        results.append(
            {
                "question": question,
                "prompt_version": prompt.version,
                "formatted_prompt": formatted,
                "response": response,
                "response_length": len(response),
            }
        )

    # Calculate simple metrics
    avg_length = sum(r["response_length"] for r in results) / len(results)

    return {
        "prompt_version": prompt.version,
        "prompt_type": prompt.prompt_type,
        "results": results,
        "metrics": {
            "avg_response_length": avg_length,
            "total_questions": len(test_questions),
        },
    }


@step
def compare_prompt_results(
    all_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare results from different prompt versions."""
    comparison = {
        "versions_tested": [r["prompt_version"] for r in all_results],
        "metrics_comparison": {},
        "winner": None,
    }

    # Compare average response lengths
    lengths = {
        r["prompt_version"]: r["metrics"]["avg_response_length"]
        for r in all_results
    }
    comparison["metrics_comparison"]["avg_response_length"] = lengths

    # Determine winner (for demo - shortest responses)
    winner_version = min(lengths.items(), key=lambda x: x[1])[0]
    comparison["winner"] = winner_version

    logger.info(f"Comparison complete. Winner: v{winner_version}")
    return comparison


@pipeline
def simple_prompt_comparison_pipeline():
    """Simple pipeline demonstrating prompt comparison.

    This pipeline:
    1. Creates multiple prompt versions
    2. Tests each version with the same questions
    3. Compares results to pick a winner

    The dashboard will show:
    - Each prompt as a versioned artifact
    - Results from each test
    - Comparison summary
    """
    # Test questions
    test_questions = [
        "What is machine learning?",
        "How does a neural network work?",
        "What is the difference between AI and ML?",
    ]

    # Create prompt versions
    prompts = create_prompt_versions()

    # Test each prompt
    all_results = []
    for i, prompt in enumerate(prompts):
        results = test_prompt_with_llm(
            prompt=prompt,
            test_questions=test_questions,
        )
        all_results.append(results)

    # Compare results
    comparison = compare_prompt_results(all_results=all_results)

    return prompts, all_results, comparison


# Alternative: Using the comparison utility
@pipeline
def prompt_ab_test_pipeline():
    """Pipeline using the built-in comparison utility."""
    from zenml.prompts import compare_prompts

    # Create two prompts to compare
    prompt_a = Prompt(
        template="Answer concisely: {question}",
        version="1.0.0",
    )

    prompt_b = Prompt(
        template="Provide a detailed answer: {question}",
        version="2.0.0",
    )

    # Test cases
    test_cases = [
        {"question": "What is Python?"},
        {"question": "Explain decorators"},
    ]

    # Mock LLM function
    def mock_llm(prompt: str) -> str:
        return f"Response to: {prompt[:30]}..."

    # Mock metric functions
    def length_metric(responses, test_cases):
        return sum(len(r) for r in responses if r) / len(responses)

    def success_metric(responses, test_cases):
        return sum(1 for r in responses if r is not None) / len(responses)

    # Compare
    comparison_result = compare_prompts(
        prompt_a=prompt_a,
        prompt_b=prompt_b,
        test_cases=test_cases,
        llm_function=mock_llm,
        metric_functions={
            "avg_length": length_metric,
            "success_rate": success_metric,
        },
    )

    return prompt_a, prompt_b, comparison_result


if __name__ == "__main__":
    # Run the simple comparison pipeline
    simple_prompt_comparison_pipeline()

    # Or run the A/B test pipeline
    # prompt_ab_test_pipeline()
