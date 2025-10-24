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

"""Customer Churn Prediction — Training and Deployment Example.

Usage:
  python run.py --train         # Train the churn prediction model
  python run.py --predict      # Run inference on sample customer data
  python run.py --predict --features '{"account_length": 50, ...}'  # Custom prediction
"""

import argparse
import json

from pipelines import churn_inference_pipeline, churn_training_pipeline


def main() -> None:
    """Main entry point for the churn prediction example."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--train",
        action="store_true",
        help="Train the churn prediction model.",
    )
    ap.add_argument(
        "--predict",
        action="store_true",
        help="Run inference on customer data.",
    )
    ap.add_argument(
        "--features",
        type=str,
        help="JSON string of customer features for prediction.",
    )
    ap.add_argument(
        "--samples",
        type=int,
        default=1000,
        help="Number of training samples to generate (default: 1000).",
    )

    args = ap.parse_args()

    if args.train:
        print(
            f">> Training churn prediction model with {args.samples} samples..."
        )
        run = churn_training_pipeline(num_samples=args.samples)
        print(
            ">> Training complete! Model tagged as 'production' and ready for serving."
        )

    elif args.predict:
        # Use provided features or default sample customer
        if args.features:
            try:
                customer_features = json.loads(args.features)
            except json.JSONDecodeError as e:
                print(f"Error parsing features JSON: {e}")
                return
        else:
            # Default sample customer with moderate churn risk
            customer_features = {
                "account_length": 45,
                "customer_service_calls": 3,
                "monthly_charges": 65.0,
                "total_charges": 2925.0,
                "has_internet_service": 1,
                "has_phone_service": 1,
                "contract_length": 1,  # month-to-month (higher churn risk)
                "payment_method_electronic": 1,
            }
            print(f">> Using sample customer features: {customer_features}")

        print(">> Running churn prediction...")
        from zenml.client import Client

        # Run the pipeline and get the result from the last step
        run = churn_inference_pipeline(customer_features=customer_features)
        client = Client()
        pipeline_run = client.get_pipeline_run(run.id)
        result = pipeline_run.steps["predict_churn"].output.load()

        print("\n=== Churn Prediction Result ===")
        print(f"Churn Probability: {result['churn_probability']:.3f}")
        print(
            f"Churn Prediction: {'Will Churn' if result['churn_prediction'] else 'Will Stay'}"
        )
        print(f"Model Version: {result.get('model_version', 'Unknown')}")
        print(f"Status: {result.get('model_status', 'Unknown')}")

        if result.get("error"):
            print(f"Error: {result['error']}")

    else:
        example_features = {
            "account_length": 45,
            "customer_service_calls": 3,
            "monthly_charges": 65.0,
            "total_charges": 2925.0,
            "has_internet_service": 1,
            "has_phone_service": 1,
            "contract_length": 1,
            "payment_method_electronic": 1,
        }

        print(f"""Customer Churn Prediction Example

Usage:
  python run.py --train                    # Train the model
  python run.py --predict                  # Predict with sample data
  python run.py --predict --features '{{...}}'  # Predict with custom data

Workflow:
1. Train model:    python run.py --train
2. Test locally:   python run.py --predict
3. Deploy service: zenml pipeline deploy pipelines.churn_inference_pipeline.churn_inference_pipeline
4. Open web UI:    Navigate to http://localhost:8000 for interactive predictions
5. Test API:       curl -X POST <endpoint>/invoke -d '{{"parameters": {{"customer_features": {{...}}}}}}'

Example customer features:
{json.dumps(example_features, indent=2)}""")


if __name__ == "__main__":
    main()
