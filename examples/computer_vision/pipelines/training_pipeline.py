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

"""Training pipeline for object detection with YOLO."""

from typing import Annotated

from steps import (
    evaluate_model,
    load_coco_dataset,
    train_yolo_model,
)
from ultralytics import YOLO

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.logger import get_logger

logger = get_logger(__name__)

docker_settings = DockerSettings(
    requirements="requirements.txt",
    required_integrations=["pillow"],
)


@pipeline(
    settings={
        "docker": docker_settings,
    }
)
def object_detection_training_pipeline(
    max_samples: int = 50,
    epochs: int = 1,
    model_name: str = "yolov8n.pt",
) -> Annotated[YOLO, "trained_model"]:
    """Training pipeline for object detection using YOLO and COCO dataset.

    This pipeline demonstrates how to build a complete computer vision training
    workflow with ZenML. It:
    1. Loads a subset of the COCO dataset using FiftyOne
    2. Trains a YOLOv8 model on the dataset
    3. Creates visualizations with FiftyOne
    4. Tags the trained model for deployment

    The pipeline uses ZenML's artifact tracking to manage all intermediate
    outputs (datasets, models, metrics) with full lineage tracking.

    Args:
        max_samples: Number of images to use from COCO validation set
        epochs: Number of training epochs
        model_name: YOLO model architecture to use (e.g., 'yolov8n.pt')

    Returns:
        The trained YOLO model, ready to be used for inference or deployment.
        Tag this artifact as 'yolo-model' for deployment.
    """
    # Step 1: Load COCO dataset using FiftyOne
    # This downloads a subset of COCO and exports it in YOLO format
    dataset_path, fiftyone_dataset_name = load_coco_dataset(
        max_samples=max_samples,
    )

    # Step 2: Train YOLO model on the dataset
    # This uses Ultralytics YOLO to train an object detection model
    # The model is automatically materialized and can be loaded in any step
    trained_model = train_yolo_model(
        dataset_path=dataset_path,
        model_name=model_name,
        epochs=epochs,
    )

    # Step 3: Evaluate the trained model
    # Run validation to get metrics like mAP, precision, recall
    metrics = evaluate_model(
        trained_model=trained_model,
        dataset_path=dataset_path,
    )

    return trained_model

