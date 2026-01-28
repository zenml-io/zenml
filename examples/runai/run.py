#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Run the Run:AI example pipelines.

Usage:
  python run.py --train      # Train model using Run:AI step operator (GPU)
  python run.py --predict    # Run inference locally
  python run.py --deploy     # Deploy inference pipeline on Run:AI
  python run.py --undeploy   # Remove deployed inference service
"""

import argparse


def main() -> None:
    """Main entry point for the Run:AI example."""
    ap = argparse.ArgumentParser(
        description="Run:AI Integration Example - Training and Deployment"
    )
    ap.add_argument(
        "--train",
        action="store_true",
        help="Train model using Run:AI step operator (GPU offloading).",
    )
    ap.add_argument(
        "--predict",
        action="store_true",
        help="Run inference pipeline locally.",
    )
    ap.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy inference pipeline on Run:AI as an HTTP service.",
    )
    ap.add_argument(
        "--undeploy",
        action="store_true",
        help="Remove deployed inference service from Run:AI.",
    )
    ap.add_argument(
        "--deployment-name",
        type=str,
        default="runai-inference",
        help="Name for the deployment (default: runai-inference).",
    )

    args = ap.parse_args()

    if args.train:
        from pipelines import gpu_training_pipeline

        print(">> Running GPU training pipeline with Run:AI step operator...")
        print("   - data_loader: Runs on Kubernetes (CPU)")
        print("   - gpu_trainer: Offloaded to Run:AI (GPU)")
        gpu_training_pipeline()
        print(">> Training complete!")

    elif args.predict:
        from pipelines import inference_pipeline

        sample_features = [0.5, -0.3, 1.2, 0.8, -0.5, 0.1, 0.9, -0.2]
        print(f">> Running inference with features: {sample_features}")
        inference_pipeline(features=sample_features)
        print(">> Inference complete!")

    elif args.deploy:
        from pipelines import inference_pipeline

        print(f">> Deploying '{args.deployment_name}' on Run:AI...")

        # Deploy the pipeline using the .deploy() method
        # This creates a snapshot and provisions the deployment
        deployment = inference_pipeline.deploy(
            deployment_name=args.deployment_name,
        )

        print(f"\n{'=' * 50}")
        print("Deployment successful!")
        print(f"  Name: {deployment.name}")
        print(f"  Status: {deployment.status}")
        if deployment.url:
            print(f"  URL: {deployment.url}")
            print(f"\nInvoke via CLI:")
            print(
                f"  zenml deployment invoke {deployment.name} "
                f"--features='[0.5, -0.3, 1.2, 0.8]'"
            )
            print(f"\nOr via HTTP:")
            print(f"  curl -X POST {deployment.url}/invoke \\")
            print('    -H "Content-Type: application/json" \\')
            print(
                '    -d \'{"parameters": {"features": [0.5, -0.3, 1.2, 0.8]}}\''
            )
        print(f"{'=' * 50}")

    elif args.undeploy:
        from zenml.client import Client

        client = Client()

        print(f">> Removing deployment '{args.deployment_name}'...")

        try:
            client.delete_deployment(
                name_id_or_prefix=args.deployment_name,
            )
            print(
                f">> Deployment '{args.deployment_name}' removed successfully!"
            )
        except KeyError:
            print(f"ERROR: Deployment '{args.deployment_name}' not found.")
        except Exception as e:
            print(f"ERROR: Failed to remove deployment: {e}")

    else:
        print("""Run:AI Integration Example

This example demonstrates two Run:AI integration patterns:

1. STEP OPERATOR (Training) - Selective GPU offloading
   Only GPU-intensive steps run on Run:AI, CPU steps run on Kubernetes.

   python run.py --train

2. DEPLOYER (Inference) - Deploy as HTTP service on Run:AI
   Deploy inference pipelines with fractional GPU and autoscaling.

   # Deploy using Python SDK
   python run.py --deploy --deployment-name my-service

   # Or deploy using CLI
   zenml pipeline deploy pipelines.inference_pipeline --name my-service

   # Invoke the deployment
   zenml deployment invoke my-service --features='[0.5, -0.3, 1.2]'

   # Remove deployment
   python run.py --undeploy --deployment-name my-service
   # Or: zenml deployment delete my-service

Prerequisites:
- Run:AI cluster access with credentials
- ZenML stack with Run:AI components configured

Stack Setup:
  # Step operator (for training)
  zenml step-operator register runai --flavor=runai \\
      --client_id=xxx --client_secret=xxx \\
      --runai_base_url=https://myorg.run.ai \\
      --project_name=my-project

  # Deployer (for inference)
  zenml deployer register runai --flavor=runai \\
      --client_id=xxx --client_secret=xxx \\
      --runai_base_url=https://myorg.run.ai \\
      --project_name=my-project

  # Create stack with both components
  zenml stack register runai-stack \\
      -o kubernetes -s runai -d runai \\
      -a gcs -c gcr -i local --set

Deployment Management:
  zenml deployment list                    # List all deployments
  zenml deployment describe my-service     # View deployment details
  zenml deployment logs my-service         # View deployment logs
  zenml deployment deprovision my-service  # Stop but keep record
  zenml deployment provision my-service    # Re-start deployment
  zenml deployment delete my-service       # Remove completely
""")


if __name__ == "__main__":
    main()
