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

from typing import Annotated, Any, Dict

from steps import (
    complete_fiftyone_analysis,
    evaluate_model,
    load_coco_dataset,
    train_yolo_model,
)

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.logger import get_logger

logger = get_logger(__name__)

docker_settings = DockerSettings(
    requirements="requirements.txt",
)


@pipeline(
    enable_cache=False,
    settings={
        "docker": docker_settings,
    },
)
def object_detection_training_pipeline(
    max_samples: int = 50,
    epochs: int = 1,
    model_name: str = "yolov8n.pt",
    confidence_threshold: float = 0.25,
    enable_fiftyone_analysis: bool = True,
) -> Annotated[Dict[str, Any], "training_results"]:
    """Complete computer vision pipeline with optional FiftyOne annotation workflow.

    This pipeline provides flexible computer vision training with ZenML:
    1. Loads COCO dataset using FiftyOne
    2. Exports annotations to YOLO format
    3. Trains YOLOv8 model on the dataset
    4. Evaluates model performance
    5. OPTIONAL: Complete FiftyOne annotation workflow (if enabled):
       - Runs inference on original FiftyOne dataset
       - Imports predictions back into FiftyOne
       - Analyzes predictions vs ground truth
       - Creates FiftyOne App session for interactive exploration

    Args:
        max_samples: Number of images to use from COCO validation set
        epochs: Number of training epochs
        model_name: YOLO model architecture to use (e.g., 'yolov8n.pt')
        confidence_threshold: Minimum confidence for predictions
        enable_fiftyone_analysis: Whether to run the complete FiftyOne workflow

    Returns:
        Dictionary containing trained model and optional analysis results
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

    # === OPTIONAL: FiftyOne Annotation Workflow Loop ===

    # Step 4: Complete FiftyOne analysis (if enabled)
    if enable_fiftyone_analysis:
        fiftyone_results = complete_fiftyone_analysis(
            fiftyone_dataset_name=fiftyone_dataset_name,
            trained_model=trained_model,
            confidence_threshold=confidence_threshold,
        )

        # Return comprehensive results with FiftyOne analysis
        return {
            "trained_model": trained_model,
            "training_metrics": metrics,
            "fiftyone_results": fiftyone_results,
            "workflow_type": "complete_with_fiftyone_analysis",
        }
    else:
        # Return basic training results without FiftyOne analysis
        return {
            "trained_model": trained_model,
            "training_metrics": metrics,
            "dataset_name": fiftyone_dataset_name,
            "workflow_type": "basic_training_only",
        }
