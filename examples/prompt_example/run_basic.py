#!/usr/bin/env python3
"""
Basic Prompt Example Runner

This script demonstrates basic prompt usage in ZenML pipelines.
"""

import click
from pipelines.basic_pipeline import basic_prompt_pipeline

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
def main(no_cache: bool = False):
    """Run the basic prompt pipeline."""

    # Check ZenML setup
    client = Client()
    logger.info(f"Running on stack: {client.active_stack.name}")

    # Configure pipeline
    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    # Run pipeline
    basic_prompt_pipeline.with_options(**pipeline_args)()

    logger.info("Basic prompt pipeline completed!")
    logger.info(
        "Check the ZenML dashboard to view prompt artifacts and visualizations"
    )


if __name__ == "__main__":
    main()
