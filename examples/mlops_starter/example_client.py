#!/usr/bin/env python3
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
#

"""Example client for the breast cancer classifier serving endpoint.

This script demonstrates how to send requests to the deployed inference pipeline
and interpret the results for real-world use cases.
"""

import requests
from sklearn.datasets import load_breast_cancer

# Example endpoint URL (replace with your actual deployment URL)
ENDPOINT_URL = "http://localhost:8001"  # Update this!


def send_prediction_request(endpoint_url: str, features_data: list):
    """Send a prediction request to the serving endpoint.

    Args:
        endpoint_url: The base URL of the deployed endpoint
        features_data: List of feature vectors (each with 30 features)

    Returns:
        Response from the endpoint
    """
    payload = {
        "input_data": features_data,
        "random_state": 42,
        "target": "target",
    }

    response = requests.post(
        f"{endpoint_url}/invoke",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    return response


def main():
    """Example usage of the breast cancer classifier endpoint."""
    print("🔬 Breast Cancer Classifier - Example Client")
    print("=" * 50)

    # Get sample data from sklearn
    data = load_breast_cancer()
    sample_features = data.data[:3].tolist()  # First 3 samples
    actual_labels = data.target[:3]  # Actual labels for comparison

    print(f"📊 Sending {len(sample_features)} samples for prediction...")
    print(f"🎯 Actual labels: {actual_labels}")
    print()

    try:
        response = send_prediction_request(ENDPOINT_URL, sample_features)

        if response.status_code == 200:
            result = response.json()
            print("✅ Prediction successful!")
            print(f"⏱️  Response time: {result.get('execution_time', 'N/A')}s")

            # Extract predictions
            if "outputs" in result and "predictions" in result["outputs"]:
                predictions = result["outputs"]["predictions"]
                print(f"🔮 Predictions: {predictions}")

                # Compare with actual labels
                print("\n📋 Results comparison:")
                for i, (pred, actual) in enumerate(
                    zip(predictions, actual_labels)
                ):
                    pred_label = "Malignant" if pred == 1 else "Benign"
                    actual_label = "Malignant" if actual == 1 else "Benign"
                    match = "✅" if pred == actual else "❌"
                    print(
                        f"  Sample {i + 1}: Predicted={pred_label}, Actual={actual_label} {match}"
                    )

            print(f"\n🔍 Full response: {result}")

        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Error: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {ENDPOINT_URL}")
        print("Make sure the serving endpoint is running!")
        print("Deploy with: python deploy_serving.py")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
