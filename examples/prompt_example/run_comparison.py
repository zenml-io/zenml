#!/usr/bin/env python3
"""
Prompt Comparison Example Runner

This script demonstrates A/B testing and comparison of different prompt variants.
"""

import click
from pipelines.comparison_pipeline import prompt_comparison_pipeline

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--variants",
    type=int,
    default=3,
    help="Number of prompt variants to compare (1-5).",
)
def main(no_cache: bool = False, variants: int = 3):
    """Run the prompt comparison pipeline."""

    if variants < 1 or variants > 5:
        logger.error("Number of variants must be between 1 and 5")
        return

    # Check ZenML setup
    client = Client()
    logger.info(f"Running on stack: {client.active_stack.name}")

    # Configure pipeline
    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    # Run pipeline
    prompt_comparison_pipeline.with_options(**pipeline_args)(
        num_variants=variants
    )

    logger.info(
        f"Prompt comparison pipeline completed with {variants} variants!"
    )
    logger.info("Check the ZenML dashboard to compare prompt performance")
    logger.info("Use ZenML Pro experiment comparison for detailed analysis")


if __name__ == "__main__":
    main()
