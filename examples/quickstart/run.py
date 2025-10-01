# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ZenML Quickstart — From Agent-Only to Agent+Classifier.

Usage:
  python run.py --agent      # Run agent in batch mode (before deployment)
  python run.py --train      # Train classifier and tag as production
  python run.py --evaluate   # Compare agent performance
"""

import argparse

from pipelines.evaluation_pipeline import agent_evaluation_pipeline
from pipelines.intent_training_pipeline import intent_training_pipeline
from pipelines.support_agent import support_agent


def main() -> None:
    """Main entry point for the quickstart CLI."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--agent",
        action="store_true",
        help="Run the agent pipeline in batch mode (before deployment).",
    )
    ap.add_argument(
        "--train", action="store_true", help="Run the training pipeline."
    )
    ap.add_argument(
        "--evaluate",
        action="store_true",
        help="Run the evaluation pipeline to compare agent modes.",
    )
    ap.add_argument(
        "--text",
        type=str,
        default="my card is lost and i need a replacement",
        help="Custom text input for the agent (use with --agent).",
    )
    args = ap.parse_args()

    if args.agent:
        print(
            f">> Running support_agent pipeline in batch mode with text: '{args.text}'"
        )
        support_agent(text=args.text)
    elif args.train:
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
        print("  python run.py --agent      # Run agent in batch mode")
        print(
            "  python run.py --agent --text 'Custom query'  # Run with custom text"
        )
        print("  python run.py --train      # Train classifier")
        print("  python run.py --evaluate   # Evaluate agent performance")
        print("\nQuickstart flow:")
        print("0. Setup deployer stack:")
        print("   zenml deployer register docker -f docker")
        print(
            "   zenml stack register docker-deployer -o default -a default -D docker --set"
        )
        print("1. Test agent locally: python run.py --agent")
        print(
            "2. Deploy agent: zenml pipeline deploy pipelines.support_agent.support_agent -n support_agent -c configs/agent.yaml"
        )
        print("3. Train classifier: python run.py --train")
        print(
            "4. Update agent: zenml pipeline deploy pipelines.support_agent.support_agent -n support_agent -c configs/agent.yaml -u"
        )
        print("5. Evaluate performance: python run.py --evaluate")


if __name__ == "__main__":
    main()
