#!/usr/bin/env python3
"""ZenML Quickstart — From Agent-Only to Agent+Classifier.

Usage:
  python run.py --train    # Train classifier and tag as production
"""

import argparse

from pipelines.evaluation_pipeline import agent_evaluation_pipeline
from pipelines.intent_training_pipeline import intent_training_pipeline


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


if __name__ == "__main__":
    main()
