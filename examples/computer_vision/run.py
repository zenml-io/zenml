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

    args = parser.parse_args()

    if args.train:
        logger.info("=" * 60)
        logger.info("Training YOLO Object Detection Model")
        logger.info("=" * 60)
        logger.info(f"Dataset: COCO validation subset ({args.samples} samples)")
        logger.info(f"Model: {args.model}")
        logger.info(f"Epochs: {args.epochs}")
        logger.info("=" * 60)

        # Run training pipeline
        run = object_detection_training_pipeline(
            max_samples=args.samples,
            epochs=args.epochs,
            model_name=args.model,
        )

        logger.info("\n" + "=" * 60)
        logger.info("✅ Training Complete!")
        logger.info("=" * 60)

        # Get the trained model artifact
        client = Client()
        pipeline_run = client.get_pipeline_run(run.id)

        # Get the model artifact from the training step
        # outputs returns a list of ArtifactVersionResponses, get the first one
        model_outputs = pipeline_run.steps["train_yolo_model"].outputs[
            "yolo-model"
        ]
        model_output = model_outputs[0] if isinstance(model_outputs, list) else model_outputs
        
        logger.info(f"Model artifact ID: {model_output.id}")
        logger.info(f"Model artifact version: {model_output.version}")
        logger.info(
            f"Model tags: {[tag.name for tag in model_output.tags]}"
        )

        logger.info("\n📝 Next Steps:")
        logger.info("1. Test inference locally:")
        logger.info("   python run.py --predict --image path/to/image.jpg")
        logger.info("\n2. Deploy as HTTP service:")
        logger.info(
            "   zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline"
        )
        logger.info("\n3. Open web UI:")
        logger.info("   http://localhost:8000")
        logger.info("\n💡 Model is automatically tagged as 'production' and ready for deployment!")

    elif args.predict:
        logger.info("=" * 60)
        logger.info("Running Object Detection Inference")
        logger.info("=" * 60)
        logger.info(f"Image: {args.image}")
        logger.info(f"Confidence threshold: {args.confidence}")
        logger.info("=" * 60)

        # Run inference pipeline
        run = object_detection_inference_pipeline(
            image_path=args.image,
            confidence_threshold=args.confidence,
        )

        # Get results
        client = Client()
        pipeline_run = client.get_pipeline_run(run.id)
        results = pipeline_run.steps["run_detection"].output.load()

        logger.info("\n" + "=" * 60)
        logger.info("🎯 Detection Results")
        logger.info("=" * 60)

        if "error" in results:
            logger.error(f"Error: {results['error']}")
            return

        logger.info(f"Objects detected: {results['num_detections']}")

        if results.get("image_size"):
            logger.info(
                f"Image size: {results['image_size']['width']} x {results['image_size']['height']}"
            )

        if results.get("model_version"):
            logger.info(f"Model version: {results['model_version']}")

        if results.get("annotated_image_path"):
            logger.info(
                f"Annotated image saved to: {results['annotated_image_path']}"
            )

        logger.info("\n📦 Detected Objects:")
        for i, detection in enumerate(results.get("detections", []), 1):
            logger.info(
                f"  {i}. {detection['label']} "
                f"(confidence: {detection['confidence']:.2%})"
            )
            bbox = detection["bbox"]
            logger.info(
                f"     BBox: [{bbox[0]:.0f}, {bbox[1]:.0f}, "
                f"{bbox[2]:.0f}, {bbox[3]:.0f}]"
            )

    else:
        # Show usage information
        print(
            """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         🎯 Computer Vision Object Detection with ZenML 🎯            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

This example demonstrates end-to-end computer vision pipelines with ZenML,
including training, inference, and deployment as an HTTP service.

📚 USAGE:

  1️⃣  Train a model:
     python run.py --train --samples 50 --epochs 3

  2️⃣  Tag the model for deployment:
     zenml artifact update <artifact-id> --name yolo-model

  3️⃣  Run batch inference:
     python run.py --predict --image path/to/image.jpg

  4️⃣  Deploy as HTTP service:
     zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline

  5️⃣  Use the web interface:
     Open http://localhost:8000 in your browser

  6️⃣  Test the API:
     curl -X POST http://localhost:8000/invoke \\
       -H "Content-Type: application/json" \\
       -d '{"parameters": {"image_path": "https://ultralytics.com/images/bus.jpg"}}'

🔧 OPTIONS:

  --train                Train a YOLO model on COCO dataset
  --predict              Run inference on an image
  --image PATH/URL       Image path or URL (for prediction)
  --samples N            Number of COCO samples for training (default: 50)
  --epochs N             Training epochs (default: 3)
  --model NAME           YOLO model (default: yolov8n.pt)
  --confidence FLOAT     Detection confidence threshold (default: 0.25)

📖 For more information, see README.md
"""
        )


if __name__ == "__main__":
    main()

