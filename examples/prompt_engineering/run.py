#!/usr/bin/env python
"""Script to run prompt engineering pipelines."""

import argparse
import os
import sys

from pipelines import (
    few_shot_prompt_pipeline,
    prompt_comparison_pipeline,
    prompt_development_pipeline,
    prompt_experimentation_pipeline,
)

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def check_api_keys():
    """Check if required API keys are set."""
    keys_found = []
    keys_missing = []

    if os.getenv("OPENAI_API_KEY"):
        keys_found.append("OpenAI")
    else:
        keys_missing.append("OPENAI_API_KEY")

    if os.getenv("ANTHROPIC_API_KEY"):
        keys_found.append("Anthropic")
    else:
        keys_missing.append("ANTHROPIC_API_KEY (optional)")

    if keys_found:
        logger.info(f"API keys found for: {', '.join(keys_found)}")

    if "OPENAI_API_KEY" in keys_missing:
        logger.error("OPENAI_API_KEY is required but not set!")
        logger.info("Please set it with: export OPENAI_API_KEY='your-key'")
        return False

    return True


def run_basic_pipeline(args):
    """Run the basic prompt development pipeline."""
    logger.info("Running basic prompt development pipeline...")

    template = (
        args.template
        or "You are a helpful assistant. Answer this question concisely: {question}"
    )

    pipeline_instance = prompt_development_pipeline(
        template=template,
        prompt_type=args.prompt_type,
        task=args.task,
        model=args.model,
    )

    prompt, results, evaluation = pipeline_instance

    logger.info(f"Pipeline completed!")
    logger.info(f"Prompt ID: {prompt.prompt_id}")
    logger.info(f"Success rate: {evaluation['success_rate']:.2%}")

    return prompt, results, evaluation


def run_comparison_pipeline(args):
    """Run the prompt comparison pipeline."""
    logger.info("Running prompt comparison pipeline...")

    base_template = (
        args.base_template or "Answer the following question: {question}"
    )

    variant_templates = args.variant_templates or [
        "You are an expert. Please answer this question: {question}",
        "Think step by step and answer the following question: {question}",
        "As a knowledgeable assistant, provide a detailed answer to: {question}",
    ]

    pipeline_instance = prompt_comparison_pipeline(
        base_template=base_template,
        variant_templates=variant_templates,
        model=args.model,
        dataset_name=args.dataset,
    )

    best_prompt, comparison = pipeline_instance

    logger.info(f"Pipeline completed!")
    logger.info(f"Best prompt ID: {best_prompt.prompt_id}")
    logger.info(f"Rankings:")
    for rank in comparison["rankings"]:
        logger.info(
            f"  Rank {rank['rank']}: {rank['prompt_id'][:8]}... (success rate: {rank['success_rate']:.2%})"
        )

    return best_prompt, comparison


def run_experimentation_pipeline(args):
    """Run the advanced experimentation pipeline with LLM judge."""
    logger.info("Running experimentation pipeline with LLM judge...")

    prompt_configs = args.prompt_configs or [
        {
            "template": "Answer the question: {question}",
            "prompt_type": "user",
            "task": "question_answering",
        },
        {
            "template": "You are an AI assistant with expertise in science and technology. Answer: {question}",
            "prompt_type": "system",
            "task": "question_answering",
            "instructions": "Provide accurate, detailed responses.",
        },
        {
            "template": "Question: {question}\n\nLet me think about this step by step:\n1.",
            "prompt_type": "user",
            "task": "question_answering",
            "instructions": "Use chain of thought reasoning.",
        },
    ]

    pipeline_instance = prompt_experimentation_pipeline(
        prompt_configs=prompt_configs,
        judge_model=args.judge_model,
        test_model=args.model,
    )

    best_prompt, comparison, evaluations = pipeline_instance

    logger.info(f"Pipeline completed!")
    logger.info(f"Best prompt ID: {best_prompt.prompt_id}")

    # Show LLM judge scores
    for i, eval_result in enumerate(evaluations):
        if eval_result["average_scores"]:
            logger.info(f"\nPrompt {i + 1} LLM Judge Scores:")
            for metric, score in eval_result["average_scores"].items():
                logger.info(f"  {metric}: {score:.2f}/5.0")

    return best_prompt, comparison, evaluations


def run_few_shot_pipeline(args):
    """Run the few-shot prompting pipeline."""
    logger.info("Running few-shot prompt pipeline...")

    base_template = (
        args.base_template
        or """Answer the question based on the examples provided.

{examples}

Question: {question}
Answer:"""
    )

    # Different example sets to test
    examples_list = [
        # 1 example
        [{"question": "What is 2+2?", "answer": "4"}],
        # 3 examples
        [
            {"question": "What is 2+2?", "answer": "4"},
            {"question": "What is the capital of France?", "answer": "Paris"},
            {"question": "What color is the sky?", "answer": "Blue"},
        ],
        # 5 examples with more complex ones
        [
            {"question": "What is 2+2?", "answer": "4"},
            {"question": "What is the capital of France?", "answer": "Paris"},
            {"question": "What color is the sky?", "answer": "Blue"},
            {
                "question": "What is photosynthesis?",
                "answer": "The process by which plants convert light energy into chemical energy",
            },
            {
                "question": "Who wrote Romeo and Juliet?",
                "answer": "William Shakespeare",
            },
        ],
    ]

    pipeline_instance = few_shot_prompt_pipeline(
        base_template=base_template,
        examples_list=examples_list,
        model=args.model,
    )

    best_prompt, comparison = pipeline_instance

    logger.info(f"Pipeline completed!")
    logger.info(f"Best prompt configuration: {best_prompt.version}")
    logger.info("\nComparison results:")
    for rank in comparison["rankings"]:
        logger.info(
            f"  {rank['template_preview'][:50]}... - Success rate: {rank['success_rate']:.2%}"
        )

    return best_prompt, comparison


def view_results(args):
    """View results from previous pipeline runs."""
    client = Client()

    # List recent pipeline runs
    if args.pipeline_name:
        runs = client.list_pipeline_runs(
            pipeline_name=args.pipeline_name, size=args.num_runs
        )
    else:
        runs = client.list_pipeline_runs(size=args.num_runs)

    if not runs:
        logger.info("No pipeline runs found.")
        return

    logger.info(f"\nRecent pipeline runs:")
    for i, run in enumerate(runs):
        logger.info(f"\n{i + 1}. Pipeline: {run.pipeline.name}")
        logger.info(f"   Status: {run.status}")
        logger.info(f"   Created: {run.created}")

        # Show artifacts if requested
        if args.show_artifacts:
            artifacts = run.artifacts
            if artifacts:
                logger.info("   Artifacts:")
                for name, artifact in artifacts.items():
                    logger.info(f"     - {name}: {artifact.type}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run ZenML prompt engineering pipelines"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Basic pipeline
    basic_parser = subparsers.add_parser(
        "basic", help="Run basic prompt development pipeline"
    )
    basic_parser.add_argument(
        "--template", type=str, help="Prompt template to test"
    )
    basic_parser.add_argument(
        "--prompt-type",
        type=str,
        default="user",
        choices=["system", "user", "assistant"],
    )
    basic_parser.add_argument(
        "--task", type=str, help="Task type (e.g., qa, summarization)"
    )
    basic_parser.add_argument(
        "--model", type=str, default="gpt-3.5-turbo", help="Model to use"
    )

    # Comparison pipeline
    comparison_parser = subparsers.add_parser(
        "comparison", help="Run prompt comparison pipeline"
    )
    comparison_parser.add_argument(
        "--base-template", type=str, help="Base prompt template"
    )
    comparison_parser.add_argument(
        "--variant-templates",
        type=str,
        nargs="+",
        help="Variant templates to test",
    )
    comparison_parser.add_argument(
        "--model", type=str, default="gpt-3.5-turbo", help="Model to use"
    )
    comparison_parser.add_argument(
        "--dataset",
        type=str,
        default="default",
        choices=["default", "qa_hard", "summarization"],
    )

    # Experimentation pipeline
    exp_parser = subparsers.add_parser(
        "experiment", help="Run experimentation pipeline with LLM judge"
    )
    exp_parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        help="Model to test prompts with",
    )
    exp_parser.add_argument(
        "--judge-model",
        type=str,
        default="gpt-4",
        help="Model to use as judge",
    )
    exp_parser.add_argument(
        "--prompt-configs",
        type=str,
        help="JSON file with prompt configurations",
    )

    # Few-shot pipeline
    few_shot_parser = subparsers.add_parser(
        "few-shot", help="Run few-shot prompting pipeline"
    )
    few_shot_parser.add_argument(
        "--base-template",
        type=str,
        help="Base template for few-shot prompting",
    )
    few_shot_parser.add_argument(
        "--model", type=str, default="gpt-3.5-turbo", help="Model to use"
    )

    # View results
    view_parser = subparsers.add_parser(
        "view", help="View results from previous runs"
    )
    view_parser.add_argument(
        "--pipeline-name", type=str, help="Filter by pipeline name"
    )
    view_parser.add_argument(
        "--num-runs", type=int, default=5, help="Number of runs to show"
    )
    view_parser.add_argument(
        "--show-artifacts", action="store_true", help="Show artifact details"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Check API keys for pipeline runs
    if args.command != "view" and not check_api_keys():
        sys.exit(1)

    # Run the appropriate command
    if args.command == "basic":
        run_basic_pipeline(args)
    elif args.command == "comparison":
        run_comparison_pipeline(args)
    elif args.command == "experiment":
        run_experimentation_pipeline(args)
    elif args.command == "few-shot":
        run_few_shot_pipeline(args)
    elif args.command == "view":
        view_results(args)


if __name__ == "__main__":
    main()
