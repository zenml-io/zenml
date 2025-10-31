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

import base64
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import cv2

from zenml import get_step_context, step
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
        image_path: Path to the image file (local path, URL, or base64 data URI)
        confidence_threshold: Minimum confidence score for detections

    Returns:
        Dictionary containing:
            - detections: List of detected objects with bboxes, labels, scores
            - num_detections: Total number of objects detected
            - annotated_image_path: Path to image with drawn bounding boxes
            - image_size: Original image dimensions
    """
    logger.info(f"Running detection on image: {image_path}")

    try:
        # Get the pre-loaded model from pipeline state (warm path)
        step_context = get_step_context()
        model = step_context.pipeline_state

        if model is None:
            # Fallback: load model from artifact store (cold path)
            logger.info(
                "Model not found in pipeline state, loading from artifact store..."
            )
            from zenml.client import Client

            client = Client()
            model_artifact = client.get_artifact_version(
                name_id_or_prefix="yolo-model"
            )
            model = model_artifact.load()
            logger.info(
                f"Loaded YOLO model from artifact (cold path): {model_artifact.version}"
            )
            model_version = model_artifact.version
        else:
            logger.info(
                "Using pre-warmed model from pipeline state (fast path)"
            )
            # For warm models, try to get version info
            try:
                from zenml.client import Client

                client = Client()
                latest_artifact = client.get_artifact_version(
                    name_id_or_prefix="yolo-model"
                )
                model_version = latest_artifact.version
            except Exception:
                model_version = "unknown"

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return {
            "error": str(e),
            "detections": [],
            "num_detections": 0,
        }

    # Handle different image input types
    temp_image_path = None
    try:
        if image_path.startswith("data:image"):
            # Handle base64 encoded image
            logger.info("Processing base64 encoded image")

            # Extract base64 data from data URI
            _, encoded = image_path.split(",", 1)
            image_data = base64.b64decode(encoded)

            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".jpg", delete=False
            ) as temp_file:
                temp_file.write(image_data)
                temp_image_path = temp_file.name

            input_path = temp_image_path

        elif image_path.startswith(("http://", "https://")):
            # Handle URL
            logger.info(f"Processing image from URL: {image_path}")
            input_path = image_path

        elif os.path.exists(image_path):
            # Handle local file path
            logger.info(f"Processing local image: {image_path}")
            input_path = image_path

        else:
            error_msg = f"Image not found or invalid format: {image_path}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "detections": [],
                "num_detections": 0,
            }

        # Run inference
        logger.info("Running YOLO inference...")
        results = model(input_path, conf=confidence_threshold)

    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "detections": [],
            "num_detections": 0,
        }

    finally:
        # Clean up temporary file if created
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except OSError:
                logger.warning(
                    f"Failed to delete temporary file: {temp_image_path}"
                )

    # Parse results
    detections: List[Dict[str, Any]] = []

    if not results:
        return {
            "error": "No inference results returned",
            "detections": [],
            "num_detections": 0,
        }

    # Process the first result (YOLO inference typically returns one result per image)
    result = results[0]

    # Get image dimensions
    image_height, image_width = result.orig_shape

    # Extract detection information
    boxes = result.boxes
    if boxes is not None and len(boxes) > 0:
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

    # Save annotated image (this will show bounding boxes even if no detections)
    annotated_image_path = Path("predictions") / "annotated_image.jpg"
    annotated_image_path.parent.mkdir(parents=True, exist_ok=True)

    # Plot results on image (YOLO's plot() shows boxes if any detected)
    annotated_img = result.plot()

    # Save using cv2
    cv2.imwrite(str(annotated_image_path), annotated_img)

    logger.info(f"Annotated image saved to: {annotated_image_path.absolute()}")

    # Convert images to base64 for web display
    # Get the original image
    original_img = result.orig_img

    # Encode original image to base64
    _, original_buffer = cv2.imencode(".jpg", original_img)
    original_base64 = base64.b64encode(original_buffer).decode("utf-8")

    # Encode annotated image to base64
    _, annotated_buffer = cv2.imencode(".jpg", annotated_img)
    annotated_base64 = base64.b64encode(annotated_buffer).decode("utf-8")

    return {
        "detections": detections,
        "num_detections": len(detections),
        "annotated_image_path": str(annotated_image_path.absolute()),
        "image_size": {"width": image_width, "height": image_height},
        "model_version": model_version,
        "original_image_base64": original_base64,
        "annotated_image_base64": annotated_base64,
    }
