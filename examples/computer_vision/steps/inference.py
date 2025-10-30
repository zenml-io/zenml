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

"""Inference step for object detection."""

import os
from pathlib import Path
from typing import Any, Dict, List

from materializers import UltralyticsYOLOMaterializer
from ultralytics import YOLO

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def run_detection(
    image_path: str,
    confidence_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Run object detection on a single image.

    This step performs inference using the pre-loaded YOLO model from the
    deployment hook. It accepts an image path (local file or URL) and returns
    detection results including bounding boxes, labels, and confidence scores.

    The model is loaded once at deployment startup (via on_init hook) and
    reused for all inference requests, making this very fast.

    Args:
        image_path: Path to the image file (local path or URL)
        confidence_threshold: Minimum confidence score for detections

    Returns:
        Dictionary containing:
            - detections: List of detected objects with bboxes, labels, scores
            - num_detections: Total number of objects detected
            - annotated_image_path: Path to image with drawn bounding boxes
            - image_size: Original image dimensions
    """
    logger.info(f"Running detection on image: {image_path}")

    # Get the pre-loaded model from the deployment hook
    # This is passed via the pipeline context
    from zenml.client import Client

    # Load the latest production model artifact
    # The UltralyticsYOLOMaterializer handles loading the YOLO model
    try:
        client = Client()
        model_artifacts = client.list_artifact_versions(
            name="yolo-model",
            tag="production",
            sort_by="created",
            size=1,
        )

        if not model_artifacts.items:
            raise ValueError(
                "No production model found. Train a model first with: python run.py --train"
            )

        model_artifact = model_artifacts.items[0]
        model: YOLO = model_artifact.load()
        logger.info(f"Loaded YOLO model from artifact: {model_artifact.version}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return {
            "error": str(e),
            "detections": [],
            "num_detections": 0,
        }

    # Check if image exists or is a URL
    if not os.path.exists(image_path) and not image_path.startswith(
        ("http://", "https://")
    ):
        error_msg = f"Image not found: {image_path}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "detections": [],
            "num_detections": 0,
        }

    # Run inference
    logger.info("Running YOLO inference...")
    results = model(image_path, conf=confidence_threshold)

    # Parse results
    detections: List[Dict[str, Any]] = []

    for result in results:
        # Get image dimensions
        image_height, image_width = result.orig_shape

        # Extract detection information
        boxes = result.boxes
        for box in boxes:
            # Get bounding box coordinates (xyxy format)
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # Get confidence and class
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = model.names[class_id]

            detections.append(
                {
                    "bbox": [x1, y1, x2, y2],
                    "label": class_name,
                    "confidence": confidence,
                    "class_id": class_id,
                }
            )

        # Save annotated image
        annotated_image_path = Path("predictions") / "annotated_image.jpg"
        annotated_image_path.parent.mkdir(parents=True, exist_ok=True)

        # Plot results on image
        annotated_img = result.plot()

        # Save using cv2
        import cv2
        import base64

        cv2.imwrite(str(annotated_image_path), annotated_img)

        logger.info(
            f"Annotated image saved to: {annotated_image_path.absolute()}"
        )

        # Convert images to base64 for web display
        # Get the original image
        original_img = result.orig_img
        
        # Encode original image to base64
        _, original_buffer = cv2.imencode('.jpg', original_img)
        original_base64 = base64.b64encode(original_buffer).decode('utf-8')
        
        # Encode annotated image to base64
        _, annotated_buffer = cv2.imencode('.jpg', annotated_img)
        annotated_base64 = base64.b64encode(annotated_buffer).decode('utf-8')

        return {
            "detections": detections,
            "num_detections": len(detections),
            "annotated_image_path": str(annotated_image_path.absolute()),
            "image_size": {"width": image_width, "height": image_height},
            "model_version": model_artifact.version,
            "original_image_base64": original_base64,
            "annotated_image_base64": annotated_base64,
        }

    # If no results
    return {
        "detections": [],
        "num_detections": 0,
        "error": "No detections found",
    }

