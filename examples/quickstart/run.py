#!/usr/bin/env python3
"""ZenML Quickstart — From Agent-Only to Agent+Classifier.

Usage:
  python run.py --train    # Train classifier and tag as production
"""

import argparse

from pipelines.intent_training_pipeline import intent_training_pipeline


def main() -> None:
    """Main entry point for the quickstart CLI."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--train", action="store_true", help="Run the training pipeline."
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
    else:
        print("Usage: python run.py --train")
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


if __name__ == "__main__":
    main()
