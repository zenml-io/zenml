#!/usr/bin/env python3
"""
External Prompt Example Runner

This script demonstrates using ExternalArtifact to run pipelines with different prompts.
"""

from datetime import datetime

import click
from pipelines.basic_pipeline import basic_prompt_pipeline_with_external

from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.client import Client
from zenml.logger import get_logger
from zenml.types import Prompt

logger = get_logger(__name__)


def create_custom_prompt(template_type: str) -> Prompt:
    """Create different prompt templates based on type."""

    if template_type == "formal":
        return Prompt(
            template="""Please provide a comprehensive analysis of the following question: {question}

Your response should include:
1. A clear and direct answer
2. Supporting evidence and reasoning
3. Potential implications or considerations
4. Confidence level in your assessment

Question: {question}

Analysis:""",
            variables={
                "question": "What are the advantages of microservices architecture?"
            },
            task="question_answering",
            domain="technical",
            prompt_strategy="structured",
            description="Formal analytical prompt with structured output",
            version="2.0.0-formal",
            tags=["formal", "analysis", "structured"],
            model_config_params={"temperature": 0.2, "max_tokens": 600},
            created_at=datetime.now(),
        )

    elif template_type == "creative":
        return Prompt(
            template="""Hey there! Let's have a fun conversation about: {question}

Think of this as a friendly chat where you can:
🎯 Share your thoughts openly
💡 Use examples and analogies  
🚀 Be creative with your explanations
✨ Make it engaging and interesting

What's on your mind: {question}

Let's dive in:""",
            variables={
                "question": "What are the advantages of microservices architecture?"
            },
            task="conversation",
            domain="general",
            prompt_strategy="conversational",
            description="Creative conversational prompt with emojis and casual tone",
            version="2.0.0-creative",
            tags=["creative", "conversational", "engaging"],
            model_config_params={"temperature": 0.8, "max_tokens": 400},
            created_at=datetime.now(),
        )

    else:  # concise
        return Prompt(
            template="Q: {question}\nA: ",
            variables={
                "question": "What are the advantages of microservices architecture?"
            },
            task="question_answering",
            domain="general",
            prompt_strategy="direct",
            description="Minimal direct prompt for concise responses",
            version="2.0.0-concise",
            tags=["concise", "minimal", "direct"],
            model_config_params={"temperature": 0.1, "max_tokens": 150},
            created_at=datetime.now(),
        )


@click.command()
@click.option(
    "--prompt-type",
    type=click.Choice(["formal", "creative", "concise"]),
    default="formal",
    help="Type of external prompt to use",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
def main(prompt_type: str = "formal", no_cache: bool = False):
    """Run pipeline with external prompt artifact."""

    # Check ZenML setup
    client = Client()
    logger.info(f"Running on stack: {client.active_stack.name}")

    # Create external prompt
    custom_prompt = create_custom_prompt(prompt_type)
    external_prompt = ExternalArtifact(value=custom_prompt)

    logger.info(f"Created {prompt_type} external prompt:")
    logger.info(f"Template: {custom_prompt.template[:100]}...")
    logger.info(f"Version: {custom_prompt.version}")

    # Configure pipeline
    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    # Run pipeline with external prompt
    basic_prompt_pipeline_with_external.with_options(**pipeline_args)(
        external_prompt=external_prompt
    )

    logger.info(f"Pipeline completed with {prompt_type} prompt!")
    logger.info("Compare this run with others in the ZenML dashboard")


if __name__ == "__main__":
    main()
