#!/usr/bin/env python3
"""ZenML Quickstart — From Agent-Only to Agent+Classifier.

<<<<<<< HEAD
Usage:
  python run.py --train    # Train classifier and tag as production
"""
=======
import click
from pipelines import (
    english_translation_pipeline,
)

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@click.command(
    help="""
ZenML Starter project.

Run the ZenML starter project with basic options.

Examples:

  \b
  # Run the training pipeline
    python run.py
"""
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--model_type",
    type=click.Choice(["t5-small", "t5-large"], case_sensitive=False),
    default="t5-small",
    help="Choose the model size: t5-small or t5-large.",
)
@click.option(
    "--config_path",
    help="Choose the configuration file.",
)
def main(
    model_type: str,
    config_path: Optional[str],
    no_cache: bool = False,
):
    """Main entry point for the pipeline execution.
>>>>>>> misc/update-examples-deployed-pipelines

import argparse

from pipelines.evaluation_pipeline import agent_evaluation_pipeline
from pipelines.intent_training_pipeline import intent_training_pipeline

<<<<<<< HEAD

def main() -> None:
    """Main entry point for the quickstart CLI."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--train", action="store_true", help="Run the training pipeline."
    )
    ap.add_argument(
        "--evaluate",
        action="store_true",
        help="Run the evaluation pipeline to compare agent modes.",
    )
    args = ap.parse_args()

    if args.train:
        print(
            ">> Running intent_training_pipeline (auto-tags artifact VERSION as 'production')."
        )
        intent_training_pipeline()
        print(
            ">> Done. Check dashboard: artifact 'intent-classifier' latest version has tag 'production'."
        )
    elif args.evaluate:
        print(
            ">> Running agent_evaluation_pipeline to compare LLM vs Hybrid performance."
        )
        agent_evaluation_pipeline()
        print(
            ">> Evaluation complete. Check dashboard for detailed metrics and visualizations."
        )
    else:
        print("Usage:")
        print("  python run.py --train      # Train classifier")
        print("  python run.py --evaluate   # Evaluate agent performance")
        print("\nQuickstart flow:")
        print("0. Setup deployer stack:")
        print("   zenml deployer register docker -f docker")
        print(
            "   zenml stack register docker-deployer -o default -a default -D docker --set"
        )
        print(
            "1. Deploy agent: zenml pipeline deploy pipelines.agent_serving_pipeline.agent_serving_pipeline -n support-agent -c configs/agent.yaml"
        )
        print("2. Train classifier: python run.py --train")
        print(
            "3. Update agent: zenml pipeline deploy pipelines.agent_serving_pipeline.agent_serving_pipeline -n support-agent -c configs/agent.yaml -u"
        )
        print("4. Evaluate performance: python run.py --evaluate")
=======
    Args:
        model_type: Type of model to use
        config_path: Configuration file to use
        no_cache: If `True` cache will be disabled.
    """
    client = Client()
    run_args_train = {}

    orchf = client.active_stack.orchestrator.flavor

    sof = None
    if client.active_stack.step_operator:
        sof = client.active_stack.step_operator.flavor

    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    if not config_path:
        # Default configuration
        config_path = "configs/training_default.yaml"
        #
        if orchf == "sagemaker" or sof == "sagemaker":
            config_path = "configs/training_aws.yaml"
        elif orchf == "vertex" or sof == "vertex":
            config_path = "configs/training_gcp.yaml"
        elif orchf == "azureml" or sof == "azureml":
            config_path = "configs/training_azure.yaml"

        print(f"Using {config_path} to configure the pipeline run.")
    else:
        print(
            f"You specified {config_path}. Please be aware of the contents of this "
            f"file as some settings might be very specific to a certain orchestration "
            f"environment. Also you might need to set `skip_build` to False in case "
            f"of missing requirements in the execution environment."
        )

    pipeline_args["config_path"] = config_path
    english_translation_pipeline.with_options(**pipeline_args)(
        model_type=model_type, **run_args_train
    )
>>>>>>> misc/update-examples-deployed-pipelines


if __name__ == "__main__":
    main()
