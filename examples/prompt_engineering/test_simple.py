#!/usr/bin/env python
"""Test script for simple pipeline."""

import os

from simple_pipeline import simple_prompt_pipeline

from zenml.logger import get_logger

logger = get_logger(__name__)


def check_azure_keys():
    """Check if Azure OpenAI keys are set."""
    required_keys = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
    missing_keys = []

    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)

    if missing_keys:
        logger.error(f"Missing required environment variables: {missing_keys}")
        return False

    logger.info("Azure OpenAI configuration found")
    return True


def main():
    """Run the simple pipeline test."""
    if not check_azure_keys():
        logger.error("Please set Azure OpenAI environment variables")
        return

    logger.info("Running simple prompt pipeline...")

    # Run the pipeline
    pipeline_run = simple_prompt_pipeline(
        template="You are an expert assistant. Provide a clear, concise answer to: {question}",
        model="gpt-4.1-mini",
    )

    # Access results
    prompt = (
        pipeline_run.steps["create_simple_prompt_step"]
        .outputs["prompt"][0]
        .load()
    )
    results = (
        pipeline_run.steps["test_with_azure_openai_step"]
        .outputs["results"][0]
        .load()
    )
    evaluation = (
        pipeline_run.steps["evaluate_results_step"]
        .outputs["evaluation"][0]
        .load()
    )

    # Display results
    logger.info("Pipeline completed successfully!")
    logger.info(f"Prompt ID: {prompt.prompt_id}")
    logger.info(f"Success rate: {evaluation['success_rate']:.2%}")
    logger.info(
        f"Average output length: {evaluation['avg_output_length']:.1f} characters"
    )

    # Show some example outputs
    logger.info("\nSample outputs:")
    for i, result in enumerate(results[:2]):  # Show first 2 results
        if result["success"]:
            logger.info(f"\nQ: {result['inputs']['question']}")
            logger.info(f"A: {result['output'][:100]}...")


if __name__ == "__main__":
    main()
