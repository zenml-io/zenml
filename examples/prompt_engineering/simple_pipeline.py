"""Simple working prompt engineering pipeline."""

from typing import Annotated, Any, Dict, List

from zenml import pipeline, step
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


@step
def create_simple_prompt_step(
    template: str,
    prompt_type: str = "user",
    version: str = "1.0.0",
) -> Annotated[Prompt, "prompt"]:
    """Create a simple prompt."""
    prompt = Prompt(
        template=template,
        prompt_type=prompt_type,
        version=version,
    )
    logger.info(f"Created prompt v{prompt.version}")
    return prompt


@step
def create_test_data_step() -> Annotated[List[Dict[str, Any]], "test_cases"]:
    """Create simple test data."""
    test_cases = [
        {"question": "What is machine learning?"},
        {"question": "What is ZenML?"},
        {"question": "How does AI work?"},
        {"question": "What is Python?"},
        {"question": "What is data science?"},
    ]
    logger.info(f"Created {len(test_cases)} test cases")
    return test_cases


@step
def test_with_azure_openai_step(
    prompt: Prompt,
    test_cases: List[Dict[str, Any]],
    model: str = "gpt-4.1-mini",
) -> Annotated[List[Dict[str, Any]], "results"]:
    """Test prompt with Azure OpenAI."""
    import os

    from openai import AzureOpenAI

    # Configure Azure OpenAI client
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
        azure_endpoint=os.getenv(
            "AZURE_OPENAI_ENDPOINT",
            "https://zenml-prompt-abs.openai.azure.com/",
        ),
    )

    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    results = []

    for i, test_case in enumerate(test_cases):
        try:
            # Format the prompt
            formatted_prompt = prompt.format(**test_case)

            # Call Azure OpenAI
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": prompt.prompt_type,
                        "content": formatted_prompt,
                    }
                ],
                temperature=0.7,
                max_tokens=300,
            )
            output = response.choices[0].message.content

            result = {
                "test_case_id": i,
                "inputs": test_case,
                "formatted_prompt": formatted_prompt,
                "output": output,
                "model": model,
                "success": True,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error in test case {i}: {str(e)}")
            result = {
                "test_case_id": i,
                "inputs": test_case,
                "formatted_prompt": formatted_prompt
                if "formatted_prompt" in locals()
                else None,
                "output": None,
                "model": model,
                "success": False,
                "error": str(e),
            }

        results.append(result)
        logger.info(f"Completed test case {i + 1}/{len(test_cases)}")

    return results


@step
def evaluate_results_step(
    results: List[Dict[str, Any]],
) -> Annotated[Dict[str, Any], "evaluation"]:
    """Evaluate the test results."""
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    success_rate = successful_tests / total_tests if total_tests > 0 else 0

    # Calculate average output length
    output_lengths = [
        len(r["output"]) for r in results if r["success"] and r["output"]
    ]
    avg_output_length = (
        sum(output_lengths) / len(output_lengths) if output_lengths else 0
    )

    evaluation = {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": success_rate,
        "avg_output_length": avg_output_length,
        "failed_tests": [r for r in results if not r["success"]],
    }

    logger.info(f"Evaluation complete: {success_rate:.2%} success rate")
    return evaluation


@pipeline
def simple_prompt_pipeline(
    template: str = "You are a helpful assistant. Answer this question: {question}",
    model: str = "gpt-4.1-mini",
):
    """Simple working prompt pipeline."""
    # Create prompt
    prompt = create_simple_prompt_step(template=template)

    # Create test data
    test_cases = create_test_data_step()

    # Test with LLM
    results = test_with_azure_openai_step(
        prompt=prompt,
        test_cases=test_cases,
        model=model,
    )

    # Evaluate
    evaluation = evaluate_results_step(results=results)

    return prompt, results, evaluation
