"""Simplified pipeline definitions for prompt engineering."""

from typing import List, Tuple

from steps import (
    create_prompt_step,
    evaluate_prompt_step,
    llm_judge_evaluate_step,
    load_test_dataset_step,
    select_best_prompt_step,
    test_prompt_with_llm_step,
)

from zenml import pipeline
from zenml.prompts import Prompt


@pipeline(enable_cache=False)
def prompt_development_pipeline(
    template: str = "Answer the question: {question}",
    prompt_type: str = "user",
    model: str = "gpt-3.5-turbo",
) -> Tuple[Prompt, dict, dict]:
    """Basic pipeline for prompt development and testing.

    This pipeline demonstrates the fundamental workflow of creating,
    testing, and evaluating prompts with LLMs.

    Args:
        template: The prompt template string
        prompt_type: Type of prompt (system, user, assistant)
        model: LLM model to use for testing

    Returns:
        Tuple of (prompt, test_results, evaluation_metrics)
    """
    # Create a prompt artifact
    prompt = create_prompt_step(
        template=template,
        prompt_type=prompt_type,
    )

    # Load test dataset
    test_cases = load_test_dataset_step(dataset_name="default")

    # Test the prompt with real LLM calls
    test_results = test_prompt_with_llm_step(
        prompt=prompt,
        test_cases=test_cases,
        model=model,
        temperature=0.7,
        max_tokens=300,
    )

    # Evaluate the results
    evaluation = evaluate_prompt_step(prompt=prompt, test_results=test_results)

    return prompt, test_results, evaluation


@pipeline(enable_cache=False)
def prompt_comparison_pipeline(
    base_template: str = "Answer the question: {question}",
    variant_templates: List[str] = None,
    model: str = "gpt-3.5-turbo",
) -> Prompt:
    """Pipeline for comparing prompt variants and selecting the best.

    Args:
        base_template: The base prompt template
        variant_templates: List of variant templates to compare
        model: LLM model to use for testing

    Returns:
        The best performing prompt
    """
    if variant_templates is None:
        variant_templates = [
            "You are an expert. Please answer this question: {question}",
            "Think step by step and answer the following question: {question}",
            "Provide a detailed answer to this question: {question}",
        ]

    # Create all prompt variants
    all_templates = [base_template] + variant_templates
    prompts = []

    for template in all_templates:
        prompt = create_prompt_step(template=template)
        prompts.append(prompt)

    # Load test dataset
    test_cases = load_test_dataset_step(dataset_name="default")

    # Test all prompts
    evaluations = []
    for prompt in prompts:
        test_results = test_prompt_with_llm_step(
            prompt=prompt,
            test_cases=test_cases,
            model=model,
        )

        evaluation = evaluate_prompt_step(
            prompt=prompt,
            test_results=test_results,
        )
        evaluations.append(evaluation)

    # Select the best prompt
    best_prompt = select_best_prompt_step(
        prompts=prompts,
        evaluations=evaluations,
        metric="accuracy",
    )

    return best_prompt


@pipeline(enable_cache=False)
def llm_judge_pipeline(
    template: str = "Answer the question: {question}",
    judge_model: str = "gpt-4",
    test_model: str = "gpt-3.5-turbo",
) -> dict:
    """Pipeline using LLM as judge for evaluation.

    Args:
        template: The prompt template to evaluate
        judge_model: Model to use as judge
        test_model: Model to test the prompt with

    Returns:
        Judge evaluation results
    """
    # Create prompt
    prompt = create_prompt_step(template=template)

    # Load test dataset
    test_cases = load_test_dataset_step(dataset_name="default")

    # Test with LLM
    test_results = test_prompt_with_llm_step(
        prompt=prompt,
        test_cases=test_cases,
        model=test_model,
    )

    # Evaluate with LLM judge
    judge_evaluation = llm_judge_evaluate_step(
        prompt=prompt,
        test_results=test_results,
        judge_model=judge_model,
    )

    return judge_evaluation


@pipeline(enable_cache=False)
def prompt_optimization_pipeline(
    base_template: str = "Answer the question: {question}",
    optimization_rounds: int = 3,
    model: str = "gpt-3.5-turbo",
) -> Prompt:
    """Pipeline for iterative prompt optimization.

    Args:
        base_template: Starting template
        optimization_rounds: Number of optimization rounds
        model: LLM model to use

    Returns:
        Optimized prompt
    """
    # Start with base prompt
    current_prompt = create_prompt_step(template=base_template)

    # Load test dataset
    test_cases = load_test_dataset_step(dataset_name="default")

    # Initial evaluation
    test_results = test_prompt_with_llm_step(
        prompt=current_prompt,
        test_cases=test_cases,
        model=model,
    )

    evaluate_prompt_step(
        prompt=current_prompt,
        test_results=test_results,
    )

    # For now, return the current prompt
    # In a real implementation, you would:
    # 1. Generate variations based on performance
    # 2. Test variations
    # 3. Select best performing variation
    # 4. Repeat for optimization_rounds

    return current_prompt
