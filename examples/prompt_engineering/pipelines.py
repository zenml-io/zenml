"""Pipeline definitions for prompt engineering."""

from typing import Optional, Tuple

from steps import (
    compare_prompts_step,
    create_prompt_step,
    create_variant_step,
    evaluate_prompt_step,
    llm_judge_evaluate_step,
    load_test_dataset_step,
    select_best_prompt_step,
    test_prompt_with_llm_step,
)

from zenml import Prompt, pipeline
from zenml.config import DockerSettings


@pipeline(
    enable_cache=False,  # Disable caching for fresh LLM calls
    settings={
        "docker": DockerSettings(
            required_integrations=["numpy", "pandas"],
            requirements=["openai>=1.0.0", "anthropic>=0.18.0"],
        )
    },
)
def prompt_development_pipeline(
    template: str,
    prompt_type: str = "user",
    task: Optional[str] = None,
    model: str = "gpt-3.5-turbo",
) -> Tuple[Prompt, dict, dict]:
    """Basic pipeline for prompt development and testing.

    This pipeline demonstrates the fundamental workflow of creating,
    testing, and evaluating prompts with LLMs.

    Args:
        template: The prompt template string
        prompt_type: Type of prompt (system, user, assistant)
        task: Task the prompt is designed for
        model: LLM model to use for testing

    Returns:
        Tuple of (prompt, test_results, evaluation_metrics)
    """
    # Create a prompt artifact
    prompt = create_prompt_step(
        template=template,
        prompt_type=prompt_type,
        task=task,
        instructions="Be helpful, accurate, and concise.",
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


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            required_integrations=["numpy", "pandas"],
            requirements=["openai>=1.0.0", "anthropic>=0.18.0"],
        )
    },
)
def prompt_comparison_pipeline(
    base_template: str,
    variant_templates: list,
    model: str = "gpt-3.5-turbo",
    dataset_name: str = "default",
) -> Tuple[Prompt, dict]:
    """Pipeline for comparing multiple prompt variants.

    This pipeline creates multiple prompt variants, tests them all,
    and selects the best performing one based on evaluation metrics.

    Args:
        base_template: The base prompt template
        variant_templates: List of variant templates to test
        model: LLM model to use for testing
        dataset_name: Name of test dataset to use

    Returns:
        Tuple of (best_prompt, comparison_results)
    """
    # Create base prompt
    base_prompt = create_prompt_step(
        template=base_template,
        prompt_type="user",
        task="question_answering",
        version="1.0.0",
    )

    # Create variants
    variants = []
    for i, variant_template in enumerate(variant_templates):
        variant = create_variant_step(
            base_prompt=base_prompt,
            variant_name=f"variant_{i + 1}",
            template=variant_template,
            version=f"1.{i + 1}.0",
        )
        variants.append(variant)

    # Load test dataset
    test_dataset = load_test_dataset_step(dataset_name=dataset_name)

    # Test all prompts (base + variants)
    all_prompts = [base_prompt] + variants
    all_results = []

    for prompt in all_prompts:
        results = test_prompt_with_llm_step(
            prompt=prompt,
            test_cases=test_dataset,
            model=model,
            temperature=0.7,
            max_tokens=300,
        )
        all_results.append(results)

    # Compare all prompts
    comparison = compare_prompts_step(prompts=all_prompts, results=all_results)

    # Select the best prompt
    best_prompt = select_best_prompt_step(
        comparison_results=comparison, prompts=all_prompts
    )

    return best_prompt, comparison


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            required_integrations=["numpy", "pandas"],
            requirements=["openai>=1.0.0", "anthropic>=0.18.0"],
        )
    },
)
def prompt_experimentation_pipeline(
    prompt_configs: list,
    judge_model: str = "gpt-4",
    test_model: str = "gpt-3.5-turbo",
) -> Tuple[Prompt, dict, dict]:
    """Advanced pipeline using LLM-as-Judge for evaluation.

    This pipeline demonstrates advanced prompt evaluation using
    another LLM as a judge to assess output quality.

    Args:
        prompt_configs: List of prompt configurations to test
        judge_model: Model to use for evaluation (should be powerful)
        test_model: Model to test the prompts with

    Returns:
        Tuple of (best_prompt, comparison_results, llm_evaluations)
    """
    # Create prompts from configs
    prompts = []
    for config in prompt_configs:
        prompt = create_prompt_step(**config)
        prompts.append(prompt)

    # Load test dataset
    test_dataset = load_test_dataset_step(dataset_name="qa_hard")

    # Test all prompts
    all_results = []
    all_evaluations = []

    for prompt in prompts:
        # Test with LLM
        results = test_prompt_with_llm_step(
            prompt=prompt,
            test_cases=test_dataset,
            model=test_model,
            temperature=0.7,
            max_tokens=500,
        )
        all_results.append(results)

        # Evaluate with LLM judge
        llm_eval = llm_judge_evaluate_step(
            prompt=prompt, test_results=results, judge_model=judge_model
        )
        all_evaluations.append(llm_eval)

    # Compare based on LLM evaluations
    comparison = compare_prompts_step(prompts=prompts, results=all_results)

    # Select best based on LLM judge scores
    best_prompt = select_best_prompt_step(
        comparison_results=comparison, prompts=prompts
    )

    return best_prompt, comparison, all_evaluations


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            required_integrations=["numpy", "pandas"],
            requirements=["openai>=1.0.0", "anthropic>=0.18.0"],
        )
    },
)
def few_shot_prompt_pipeline(
    base_template: str,
    examples_list: list,
    model: str = "gpt-3.5-turbo",
) -> Tuple[Prompt, dict]:
    """Pipeline for testing few-shot prompting strategies.

    This pipeline compares zero-shot vs few-shot prompting by
    testing the same template with different numbers of examples.

    Args:
        base_template: The base prompt template
        examples_list: List of example sets to test
        model: LLM model to use

    Returns:
        Tuple of (best_prompt, comparison_results)
    """
    # Create zero-shot baseline
    zero_shot = create_prompt_step(
        template=base_template,
        prompt_type="user",
        task="question_answering",
        examples=None,
    )

    # Create few-shot variants
    few_shot_prompts = []
    for i, examples in enumerate(examples_list):
        few_shot = create_prompt_step(
            template=base_template,
            prompt_type="user",
            task="question_answering",
            examples=examples,
            version=f"few_shot_{len(examples)}_examples",
        )
        few_shot_prompts.append(few_shot)

    # Test all variants
    test_dataset = load_test_dataset_step(dataset_name="default")
    all_prompts = [zero_shot] + few_shot_prompts
    all_results = []

    for prompt in all_prompts:
        results = test_prompt_with_llm_step(
            prompt=prompt,
            test_cases=test_dataset,
            model=model,
            temperature=0.5,  # Lower temperature for more consistent results
            max_tokens=300,
        )
        all_results.append(results)

    # Compare and select best
    comparison = compare_prompts_step(prompts=all_prompts, results=all_results)

    best_prompt = select_best_prompt_step(
        comparison_results=comparison, prompts=all_prompts
    )

    return best_prompt, comparison
