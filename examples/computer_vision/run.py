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

"""Computer Vision with ZenML - Object Detection Example.

This example demonstrates how to build an end-to-end computer vision pipeline
using ZenML, Ultralytics YOLO, and FiftyOne. It includes:
- Training pipeline: Load COCO dataset and train a YOLO model
- Inference pipeline: Deploy as an HTTP service for real-time predictions

Usage:
    # Train a model on COCO subset
    python run.py --train

    # Run inference on a local image
    python run.py --predict --image path/to/image.jpg

    # Run inference on a URL
    python run.py --predict --image https://ultralytics.com/images/bus.jpg

    # Deploy as HTTP service
    zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline

    # Test deployed service
    curl -X POST http://localhost:8000/invoke \\
        -H "Content-Type: application/json" \\
        -d '{"parameters": {"image_path": "https://ultralytics.com/images/bus.jpg"}}'
"""

import argparse

from pipelines import (
    object_detection_inference_pipeline,
    object_detection_training_pipeline,
)

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Main entry point for the computer vision example."""
    parser = argparse.ArgumentParser(
        description="Computer Vision Object Detection with ZenML"
    )

    parser.add_argument(
        "--train",
        action="store_true",
        help="Train a YOLO model on COCO dataset subset",
    )

    parser.add_argument(
        "--predict",
        action="store_true",
        help="Run inference on an image",
    )

    parser.add_argument(
        "--image",
        type=str,
        default="https://ultralytics.com/images/bus.jpg",
        help="Path or URL to image for prediction",
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=50,
        help="Number of COCO samples to use for training (default: 50)",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
        help="Number of training epochs (default: 1 for quick demo, use 10+ for production)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="YOLO model to use (default: yolov8n.pt)",
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help="Confidence threshold for detections (default: 0.25)",
    )

    parser.add_argument(
        "--disable-fiftyone-analysis",
        action="store_true",
        help="Disable the complete FiftyOne annotation workflow (faster training)",
    )

    args = parser.parse_args()

    if args.train:
        logger.info(
            f"Training {args.model} on {args.samples} COCO samples for {args.epochs} epochs..."
        )

        # Run training pipeline
        enable_fiftyone_analysis = not args.disable_fiftyone_analysis
        object_detection_training_pipeline(
            max_samples=args.samples,
            epochs=args.epochs,
            model_name=args.model,
            confidence_threshold=args.confidence,
            enable_fiftyone_analysis=enable_fiftyone_analysis,
        )

        # Get latest model version for logging
        client = Client()
        try:
            latest_model = client.get_artifact_version(
                name_id_or_prefix="yolo-model"
            )
            model_version = latest_model.version
        except Exception:
            model_version = "unknown"

        logger.info(
            f"\n✅ Training complete! Model version: {model_version} (tagged as 'production')"
        )

        if enable_fiftyone_analysis:
            logger.info(
                "\n📊 FiftyOne dashboard ready. Launch with: python launch_fiftyone.py"
            )

        logger.info("\n📝 Next steps:")
        logger.info(
            "  • Test: python run.py --predict --image path/to/image.jpg"
        )
        logger.info(
            "  • Deploy: zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline"
        )

    elif args.predict:
        logger.info(f"Running inference on {args.image}...")

        # Run inference pipeline - returns the detection results directly
        results = object_detection_inference_pipeline(
            image_path=args.image,
            confidence_threshold=args.confidence,
        )

        if isinstance(results, dict) and "error" in results:
            logger.error(f"Error: {results['error']}")
            return

        logger.info(
            f"\n🎯 Detected {results.get('num_detections', 0)} objects:"
        )
        for i, detection in enumerate(results.get("detections", []), 1):
            logger.info(
                f"  {i}. {detection['label']} ({detection['confidence']:.1%})"
            )

        if results.get("annotated_image_path"):
            logger.info(f"\n📸 Saved to: {results['annotated_image_path']}")

    else:
        print("""
🎯 Computer Vision Object Detection with ZenML

USAGE:
  python run.py --train --samples 50 --epochs 3
  python run.py --predict --image path/to/image.jpg
  zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline

OPTIONS:
  --train                         Train YOLO model on COCO dataset
  --predict                       Run inference on an image
  --image PATH                    Image path or URL (default: ultralytics bus.jpg)
  --samples N                     COCO samples for training (default: 50)
  --epochs N                      Training epochs (default: 1)
  --model NAME                    YOLO model (default: yolov8n.pt)
  --confidence FLOAT              Detection threshold (default: 0.25)
  --disable-fiftyone-analysis     Skip FiftyOne for faster training

See README.md for more details.
""")


if __name__ == "__main__":
    main()
