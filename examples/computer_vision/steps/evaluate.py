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

"""Model evaluation step using YOLO validation."""

from pathlib import Path
from typing import Annotated, Dict, Tuple

from materializers import UltralyticsYOLOMaterializer
from ultralytics import YOLO

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def evaluate_model(
    trained_model: YOLO,
    dataset_path: Path,
) -> Annotated[Dict[str, float], "metrics"]:
    """Evaluate the trained YOLO model on the validation dataset.

    This step runs validation on the trained model to get performance metrics
    like mAP (mean Average Precision), precision, and recall.

    Args:
        trained_model: The trained YOLO model
        dataset_path: Path to the dataset directory with YOLO format

    Returns:
        Dictionary containing validation metrics (mAP50, mAP50-95, precision, recall)
    """
    logger.info("Running model validation...")

    # Find the data.yaml file
    data_yaml = dataset_path / "dataset.yaml"

    if not data_yaml.exists():
        logger.warning(f"Dataset config not found at {data_yaml}")
        return {
            "error": "Dataset config not found",
            "mAP50": 0.0,
            "mAP50-95": 0.0,
        }

    # Run validation
    try:
        results = trained_model.val(data=str(data_yaml))

        # Extract metrics
        metrics = {
            "mAP50": float(results.box.map50),  # mAP at IoU=0.50
            "mAP50-95": float(results.box.map),  # mAP at IoU=0.50:0.95
            "precision": float(results.box.mp),  # mean precision
            "recall": float(results.box.mr),  # mean recall
        }

        logger.info("Validation Results:")
        logger.info(f"  mAP@50: {metrics['mAP50']:.3f}")
        logger.info(f"  mAP@50-95: {metrics['mAP50-95']:.3f}")
        logger.info(f"  Precision: {metrics['precision']:.3f}")
        logger.info(f"  Recall: {metrics['recall']:.3f}")

        return metrics

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "error": str(e),
            "mAP50": 0.0,
            "mAP50-95": 0.0,
        }

