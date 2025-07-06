"""Steps for prompt engineering pipelines."""

import json
from typing import Annotated, Any, Dict, List, Optional

from zenml import step
from zenml.logger import get_logger
from zenml.prompts import Prompt
from zenml.prompts.prompt_comparison import compare_prompts
from zenml.prompts.prompt_utils import create_prompt_variant

logger = get_logger(__name__)


@step
def create_prompt_step(
    template: str,
    prompt_type: str = "user",
    task: Optional[str] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
    instructions: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
) -> Annotated[Prompt, "created_prompt"]:
    """Create a new prompt artifact.

    Args:
        template: The prompt template string
        prompt_type: Type of prompt (system, user, assistant)
        task: Task the prompt is designed for
        examples: Example inputs/outputs for few-shot prompting
        instructions: Specific instructions for the prompt
        variables: Default variable values

    Returns:
        Created Prompt artifact
    """
    prompt = Prompt(
        template=template,
        prompt_type=prompt_type,
        task=task,
        examples=examples,
        instructions=instructions,
        variables=variables,
        version="1.0.0",
    )

    logger.info(f"Created prompt with ID: {prompt.prompt_id}")
    logger.info(f"Template variables: {prompt.get_variable_names()}")

    return prompt


@step
def create_variant_step(
    base_prompt: Prompt, variant_name: str, **changes: Any
) -> Annotated[Prompt, "prompt_variant"]:
    """Create a variant of an existing prompt.

    Args:
        base_prompt: The base prompt to create variant from
        variant_name: Name for the variant
        **changes: Fields to change in the variant

    Returns:
        New prompt variant
    """
    variant = create_prompt_variant(
        base_prompt=base_prompt, variant_name=variant_name, **changes
    )

    logger.info(
        f"Created variant '{variant_name}' from prompt {base_prompt.prompt_id}"
    )

    return variant


@step
def test_prompt_with_llm_step(
    prompt: Prompt,
    test_cases: List[Dict[str, Any]],
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> Annotated[List[Dict[str, Any]], "test_results"]:
    """Test a prompt with an LLM using real API calls.

    Args:
        prompt: The prompt to test
        test_cases: List of test cases with variables
        model: Model to use (gpt-3.5-turbo, gpt-4, claude-3, etc.)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate

    Returns:
        List of test results with inputs and outputs
    """
    results = []

    # Import based on model type
    if model.startswith("gpt") or model.startswith("text-"):
        import openai

        client = openai.OpenAI()
        use_openai = True
    elif model.startswith("claude"):
        import anthropic

        client = anthropic.Anthropic()
        use_openai = False
    else:
        raise ValueError(f"Unsupported model: {model}")

    for i, test_case in enumerate(test_cases):
        try:
            # Format the prompt
            formatted_prompt = prompt.format(**test_case)

            # Call the appropriate API
            if use_openai:
                if model.startswith("gpt"):
                    # Chat completion API
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": prompt.prompt_type,
                                "content": formatted_prompt,
                            }
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    output = response.choices[0].message.content
                else:
                    # Legacy completion API
                    response = client.completions.create(
                        model=model,
                        prompt=formatted_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    output = response.choices[0].text.strip()
            else:
                # Anthropic API
                response = client.messages.create(
                    model=model,
                    messages=[{"role": "user", "content": formatted_prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                output = response.content[0].text

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
def evaluate_prompt_step(
    prompt: Prompt,
    test_results: List[Dict[str, Any]],
    evaluation_criteria: Optional[Dict[str, Any]] = None,
) -> Annotated[Dict[str, Any], "evaluation_metrics"]:
    """Evaluate prompt performance based on test results.

    Args:
        prompt: The prompt being evaluated
        test_results: Results from testing the prompt
        evaluation_criteria: Optional custom evaluation criteria

    Returns:
        Dictionary of evaluation metrics
    """
    # Calculate basic metrics
    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r["success"])
    success_rate = successful_tests / total_tests if total_tests > 0 else 0

    # Calculate average output length
    output_lengths = [
        len(r["output"]) for r in test_results if r["success"] and r["output"]
    ]
    avg_output_length = (
        sum(output_lengths) / len(output_lengths) if output_lengths else 0
    )

    metrics = {
        "prompt_id": prompt.prompt_id,
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": success_rate,
        "avg_output_length": avg_output_length,
        "failed_tests": [r for r in test_results if not r["success"]],
    }

    # Add custom evaluation if provided
    if evaluation_criteria:
        # Implement custom evaluation logic here
        # For example, checking if outputs contain certain keywords
        pass

    logger.info(f"Evaluation complete: {success_rate:.2%} success rate")

    return metrics


@step
def load_test_dataset_step(
    dataset_name: str = "default",
) -> Annotated[List[Dict[str, Any]], "test_dataset"]:
    """Load a test dataset for prompt evaluation.

    Args:
        dataset_name: Name of the dataset to load

    Returns:
        List of test cases
    """
    # Example datasets
    datasets = {
        "default": [
            {"question": "What is machine learning?"},
            {"question": "How does gradient descent work?"},
            {
                "question": "What is the difference between supervised and unsupervised learning?"
            },
            {"question": "Explain neural networks in simple terms."},
            {"question": "What is overfitting and how to prevent it?"},
        ],
        "qa_hard": [
            {
                "question": "Explain the vanishing gradient problem in deep neural networks."
            },
            {"question": "How does batch normalization improve training?"},
            {"question": "What is the lottery ticket hypothesis?"},
            {
                "question": "Compare different optimization algorithms (SGD, Adam, RMSprop)."
            },
            {"question": "Explain the transformer architecture."},
        ],
        "summarization": [
            {
                "text": "Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience. Instead of being explicitly programmed to perform a task, machine learning systems learn from data, identifying patterns and making decisions with minimal human intervention.",
                "max_length": 50,
            },
            {
                "text": "Deep learning is a subfield of machine learning that uses artificial neural networks with multiple layers (deep neural networks) to progressively extract higher-level features from raw input. It has revolutionized fields such as computer vision, natural language processing, and speech recognition by achieving state-of-the-art performance on many challenging tasks.",
                "max_length": 50,
            },
        ],
    }

    dataset = datasets.get(dataset_name, datasets["default"])
    logger.info(
        f"Loaded {len(dataset)} test cases from '{dataset_name}' dataset"
    )

    return dataset


@step
def compare_prompts_step(
    prompts: List[Prompt],
    results: List[List[Dict[str, Any]]],
    comparison_metrics: Optional[List[str]] = None,
) -> Annotated[Dict[str, Any], "prompt_comparison"]:
    """Compare multiple prompts based on their test results.

    Args:
        prompts: List of prompts to compare
        results: List of test results for each prompt
        comparison_metrics: Metrics to use for comparison

    Returns:
        Comparison results and rankings
    """
    if len(prompts) != len(results):
        raise ValueError("Number of prompts must match number of result sets")

    comparisons = []

    for i, (prompt, prompt_results) in enumerate(zip(prompts, results)):
        # Calculate metrics for this prompt
        successful = sum(1 for r in prompt_results if r["success"])
        success_rate = (
            successful / len(prompt_results) if prompt_results else 0
        )

        avg_length = (
            sum(
                len(r["output"])
                for r in prompt_results
                if r["success"] and r["output"]
            )
            / successful
            if successful > 0
            else 0
        )

        comparisons.append(
            {
                "prompt_id": prompt.prompt_id,
                "prompt_index": i,
                "template_preview": prompt.template[:100] + "..."
                if len(prompt.template) > 100
                else prompt.template,
                "success_rate": success_rate,
                "avg_output_length": avg_length,
                "total_tests": len(prompt_results),
                "successful_tests": successful,
            }
        )

    # Rank prompts by success rate
    comparisons.sort(key=lambda x: x["success_rate"], reverse=True)

    # Add rankings
    for i, comp in enumerate(comparisons):
        comp["rank"] = i + 1

    # Use the compare_prompts utility for detailed comparison
    detailed_comparisons = []
    if len(prompts) > 1:
        for i in range(len(prompts)):
            for j in range(i + 1, len(prompts)):
                comparison = compare_prompts(prompts[i], prompts[j])
                detailed_comparisons.append(
                    {
                        "prompt_1": prompts[i].prompt_id,
                        "prompt_2": prompts[j].prompt_id,
                        "similarity": comparison.overall_similarity,
                        "is_compatible": comparison.is_compatible,
                    }
                )

    result = {
        "rankings": comparisons,
        "best_prompt_id": comparisons[0]["prompt_id"] if comparisons else None,
        "detailed_comparisons": detailed_comparisons,
        "summary": {
            "total_prompts": len(prompts),
            "best_success_rate": comparisons[0]["success_rate"]
            if comparisons
            else 0,
            "worst_success_rate": comparisons[-1]["success_rate"]
            if comparisons
            else 0,
        },
    }

    logger.info(
        f"Comparison complete. Best prompt: {result['best_prompt_id']}"
    )

    return result


@step
def select_best_prompt_step(
    comparison_results: Dict[str, Any], prompts: List[Prompt]
) -> Annotated[Prompt, "best_prompt"]:
    """Select the best prompt based on comparison results.

    Args:
        comparison_results: Results from prompt comparison
        prompts: Original list of prompts

    Returns:
        The best performing prompt
    """
    best_prompt_id = comparison_results["best_prompt_id"]

    for prompt in prompts:
        if prompt.prompt_id == best_prompt_id:
            logger.info(f"Selected best prompt: {prompt.prompt_id}")
            return prompt

    # Fallback to first prompt if not found
    logger.warning("Best prompt not found, returning first prompt")
    return prompts[0]


@step
def llm_judge_evaluate_step(
    prompt: Prompt,
    test_results: List[Dict[str, Any]],
    evaluation_prompt: Optional[Prompt] = None,
    judge_model: str = "gpt-4",
) -> Annotated[Dict[str, Any], "llm_evaluation"]:
    """Use an LLM to evaluate prompt outputs (LLM-as-Judge pattern).

    Args:
        prompt: The prompt being evaluated
        test_results: Results from testing the prompt
        evaluation_prompt: Optional custom evaluation prompt
        judge_model: Model to use for evaluation

    Returns:
        LLM-based evaluation results
    """
    if not evaluation_prompt:
        # Default evaluation prompt
        evaluation_prompt = Prompt(
            template="""Evaluate the following AI response:

Question: {question}
Response: {response}

Rate the response on the following criteria (1-5 scale):
1. Accuracy: Is the information correct?
2. Relevance: Does it answer the question?
3. Clarity: Is it well-written and easy to understand?
4. Completeness: Does it cover all aspects?

Provide ratings in JSON format:
{{"accuracy": X, "relevance": X, "clarity": X, "completeness": X, "overall": X, "feedback": "..."}}""",
            prompt_type="user",
        )

    import openai

    client = openai.OpenAI()

    evaluations = []

    for result in test_results:
        if not result["success"] or not result["output"]:
            continue

        try:
            # Format evaluation prompt
            eval_formatted = evaluation_prompt.format(
                question=result["inputs"].get("question", ""),
                response=result["output"],
            )

            # Get evaluation from LLM
            response = client.chat.completions.create(
                model=judge_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert evaluator. Provide honest, detailed evaluations.",
                    },
                    {"role": "user", "content": eval_formatted},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            evaluation = json.loads(response.choices[0].message.content)
            evaluation["test_case_id"] = result["test_case_id"]
            evaluations.append(evaluation)

        except Exception as e:
            logger.error(
                f"Error evaluating test case {result['test_case_id']}: {e}"
            )

    # Calculate aggregate scores
    if evaluations:
        avg_scores = {
            "accuracy": sum(e.get("accuracy", 0) for e in evaluations)
            / len(evaluations),
            "relevance": sum(e.get("relevance", 0) for e in evaluations)
            / len(evaluations),
            "clarity": sum(e.get("clarity", 0) for e in evaluations)
            / len(evaluations),
            "completeness": sum(e.get("completeness", 0) for e in evaluations)
            / len(evaluations),
            "overall": sum(e.get("overall", 0) for e in evaluations)
            / len(evaluations),
        }
    else:
        avg_scores = {}

    return {
        "prompt_id": prompt.prompt_id,
        "evaluations": evaluations,
        "average_scores": avg_scores,
        "total_evaluated": len(evaluations),
        "judge_model": judge_model,
    }
