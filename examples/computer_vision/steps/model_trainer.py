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

"""Model training step using Ultralytics YOLO."""

from pathlib import Path
from typing import Annotated

from materializers import UltralyticsYOLOMaterializer
from ultralytics import YOLO

from zenml import ArtifactConfig, add_tags, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(output_materializers=UltralyticsYOLOMaterializer)
def train_yolo_model(
    dataset_path: Path,
    model_name: str = "yolov8n.pt",
    epochs: int = 1,
    image_size: int = 640,
) -> Annotated[
    YOLO, ArtifactConfig(name="yolo-model", tags=["computer-vision"])
]:
    """Train a YOLO model on the provided dataset.

    This step uses Ultralytics YOLO to train (or fine-tune) an object detection
    model. For demonstration purposes, we use YOLOv8n (nano) which is the smallest
    and fastest YOLO model. Default is just 1 epoch for quick testing - increase
    for better accuracy in production.

    The trained model is automatically materialized using the custom
    UltralyticsYOLOMaterializer, which stores the model weights and allows
    the model to be loaded in any subsequent step or pipeline.

    Args:
        dataset_path: Path to the dataset directory with YOLO format
        model_name: YOLO model to use. Options from smallest to largest:
            - 'yolov8n.pt' (nano, ~3.2M params) - default, fastest
            - 'yolov8s.pt' (small, ~11.2M params)
            - 'yolov8m.pt' (medium, ~25.9M params)
            - 'yolov8l.pt' (large, ~43.7M params)
            - 'yolov8x.pt' (extra large, ~68.2M params)
        epochs: Number of training epochs (default: 1 for quick demo)
        image_size: Input image size for training

    Returns:
        trained_model: The trained YOLO model object (automatically materialized)
    """
    logger.info(f"Initializing YOLO model: {model_name}")

    # Load pre-trained YOLO model
    # This will download the model if not already cached
    model = YOLO(model_name)

    logger.info(f"Starting training for {epochs} epochs...")
    logger.info(f"Dataset path: {dataset_path}")

    # Find the data.yaml file in the dataset directory
    data_yaml = dataset_path / "dataset.yaml"

    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Could not find dataset.yaml at {data_yaml}. "
            "Make sure the dataset was exported correctly."
        )

    # Train the model
    # Ultralytics handles all the training details and returns the results
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=image_size,
        project="runs/detect",
        name="coco_training",
        exist_ok=True,
        verbose=True,
    )

    logger.info("Training completed!")

    # After training, the model object is already updated with the best weights
    # YOLO automatically loads the best weights into the model object
    # No need to manually load from a path!
    logger.info(f"Model trained successfully")
    logger.info(f"Best weights saved at: {model.trainer.best}")

    # Tag the trained model artifact as 'production' for deployment
    add_tags(
        tags=["production"], artifact_name="yolo-model", infer_artifact=True
    )
    logger.info("Tagged model artifact as 'production'")

    # The model object already has the best weights loaded
    # The UltralyticsYOLOMaterializer will handle saving the weights to artifact store
    return model
