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

"""Data loading step using FiftyOne for COCO dataset."""

import shutil
from pathlib import Path
from typing import Annotated, Tuple

import fiftyone as fo
import fiftyone.zoo as foz

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def load_coco_dataset(
    max_samples: int = 50,
    split: str = "validation",
) -> Tuple[
    Annotated[Path, "dataset_path"],
    Annotated[str, "fiftyone_dataset_name"],
]:
    """Load a subset of the COCO 2017 validation dataset using FiftyOne.

    This step downloads a small subset of the COCO dataset and prepares it
    for object detection training. FiftyOne handles the downloading and
    dataset management, making it easy to work with standard CV datasets.

    Args:
        max_samples: Maximum number of images to load from COCO validation set
        split: COCO split to load ('train', 'validation', 'test')

    Returns:
        Tuple containing:
            - dataset_path: Path to the exported dataset directory (images + labels)
            - fiftyone_dataset_name: Name of the FiftyOne dataset for later reference
    """
    logger.info(
        f"Loading COCO {split} dataset with max {max_samples} samples..."
    )

    # Generate a unique dataset name based on parameters
    dataset_name = f"coco-2017-{split}-{max_samples}samples"

    # Load COCO validation split from FiftyOne zoo
    # This downloads only the specified number of samples
    dataset = foz.load_zoo_dataset(
        "coco-2017",
        split=split,
        max_samples=max_samples,
        dataset_name=dataset_name,
        shuffle=True,
    )

    logger.info(f"Loaded {len(dataset)} samples from COCO dataset")
    logger.info(f"Dataset info: {dataset}")

    # Export dataset to YOLO format for training
    # This creates a directory structure that YOLO expects
    export_dir = Path("data") / "coco_subset"
    export_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting dataset to {export_dir} in YOLO format...")

    # Clean up existing export directory if it exists
    if (export_dir / "dataset.yaml").exists():
        logger.info("Removing existing export directory...")
        shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

    # Export to YOLO format
    # YOLO requires both 'train' and 'val' splits in dataset.yaml
    # For this demo, we'll use the same data for both splits
    dataset.export(
        export_dir=str(export_dir),
        dataset_type=fo.types.YOLOv5Dataset,
        split="train",
    )

    # Also export as validation split (YOLO requires both)
    dataset.export(
        export_dir=str(export_dir),
        dataset_type=fo.types.YOLOv5Dataset,
        split="val",
    )

    logger.info(f"Dataset exported successfully to {export_dir}")
    logger.info(f"FiftyOne dataset '{dataset_name}' saved for visualization")

    # Return the Path - ZenML's PathMaterializer will automatically:
    # 1. Copy this directory to the artifact store
    # 2. Make it available to subsequent steps in other pods
    # 3. Download it to a temp location when loaded
    return export_dir, dataset_name

