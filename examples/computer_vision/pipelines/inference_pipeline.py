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

"""Inference pipeline for real-time object detection deployment."""

from typing import Any, Dict

from steps import run_detection

from pipelines.hooks import cleanup_model, init_model
from zenml import pipeline
from zenml.config import (
    CORSConfig,
    DeploymentSettings,
    DockerSettings,
    SecureHeadersConfig,
)
from zenml.config.resource_settings import ResourceSettings

docker_settings = DockerSettings(
    requirements="requirements.txt",
    required_integrations=["pillow"],
)

# Custom CSP to allow data URIs for base64-encoded images
CUSTOM_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "img-src 'self' data:; "  # Added 'data:' to allow base64 images
    "style-src 'self' 'unsafe-inline'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "font-src 'self';"
    "frame-src 'self'"
)

deployment_settings = DeploymentSettings(
    app_title="YOLO Object Detection Service",
    app_description="Real-time object detection using YOLOv8 with interactive web interface",
    app_version="1.0.0",
    dashboard_files_path="ui",
    cors=CORSConfig(
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,  # Cannot be True with wildcard origins
    ),
    secure_headers=SecureHeadersConfig(
        csp=CUSTOM_CSP,
    ),
)

resource_settings = ResourceSettings(
    memory="2GB",
    cpu_count=2,
    min_replicas=1,
    max_replicas=3,
    max_concurrency=10,
)


@pipeline(
    enable_cache=False,
    on_init=init_model,
    on_cleanup=cleanup_model,
    settings={
        "docker": docker_settings,
        "deployment": deployment_settings,
        "resources": resource_settings,
    },
)
def object_detection_inference_pipeline(
    image_path: str = "https://ultralytics.com/images/bus.jpg",
    confidence_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Object detection inference pipeline deployed as an HTTP service.

    This pipeline uses a pre-loaded YOLO model (loaded during deployment
    initialization via the `on_init` hook) to perform fast object detection
    on images. The model stays "warm" in memory, eliminating cold-start delays.

    The pipeline can be deployed as a real-time HTTP service that accepts
    image paths (local files or URLs) and returns detection results with
    bounding boxes, labels, and confidence scores.

    Usage:
        1. Train a model: python run.py --train
        2. Deploy this pipeline: zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline
        3. Test via web UI: Open http://localhost:8000
        4. Test via API: curl -X POST http://localhost:8000/invoke -d '{"parameters": {"image_path": "path/to/image.jpg"}}'

    Args:
        image_path: Path to the image file (local path or URL).
            Examples:
            - Local: "/path/to/image.jpg"
            - URL: "https://ultralytics.com/images/bus.jpg"
        confidence_threshold: Minimum confidence score for detections (0.0 to 1.0)

    Returns:
        Dictionary containing:
            - detections: List of detected objects with bboxes, labels, scores
            - num_detections: Total number of objects detected
            - annotated_image_path: Path to image with drawn bounding boxes
            - image_size: Original image dimensions
            - model_version: Version of the YOLO model used
    """
    detection_results: Dict[str, Any] = run_detection(
        image_path=image_path,
        confidence_threshold=confidence_threshold,
    )

    return detection_results
