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

"""FiftyOne annotator implementation for computer vision workflows."""

import shutil
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fiftyone as fo
import fiftyone.zoo as foz
from fiftyone import ViewField as F
from pydantic import BaseModel, Field
from ultralytics import YOLO

from zenml.logger import get_logger

logger = get_logger(__name__)

# COCO 2017 class names in the correct order (80 classes)
COCO_CLASSES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


class FiftyOneAnnotatorConfig(BaseModel):
    """Configuration for FiftyOne annotator.

    This is a simplified version that follows the ZenML annotator pattern
    but doesn't inherit from the full stack component system.
    """

    default_port: int = Field(
        5151, description="Default port for FiftyOne App"
    )
    auto_launch: bool = Field(
        False, description="Automatically launch browser when starting app"
    )


class FiftyOneAnnotator:
    """FiftyOne annotator for computer vision workflows.

    This class encapsulates FiftyOne functionality following the ZenML annotator pattern,
    making it easy to refactor into a full ZenML integration later. It handles:
    - Dataset loading and management
    - Model inference and prediction import
    - Performance analysis and evaluation
    - Interactive dashboard launching
    """

    def __init__(self, config: Optional[FiftyOneAnnotatorConfig] = None):
        """Initialize the FiftyOne annotator.

        Args:
            config: Configuration for the annotator
        """
        self.config = config or FiftyOneAnnotatorConfig()

    def get_url(self, port: Optional[int] = None) -> str:
        """Get the URL of the FiftyOne annotation interface.

        Args:
            port: Port to use, defaults to config port

        Returns:
            The URL of the annotation interface
        """
        port = port or self.config.default_port
        return f"http://localhost:{port}"

    def get_url_for_dataset(
        self, dataset_name: str, port: Optional[int] = None
    ) -> str:
        """Get the URL for a specific dataset in FiftyOne App.

        Args:
            dataset_name: Name of the dataset
            port: Port to use, defaults to config port

        Returns:
            The URL for the dataset
        """
        base_url = self.get_url(port)
        return f"{base_url}?dataset={dataset_name}"

    def get_datasets(self) -> List[fo.Dataset]:
        """Get all available FiftyOne datasets.

        Returns:
            List of FiftyOne datasets
        """
        dataset_names = fo.list_datasets()
        datasets = []
        for name in dataset_names:
            try:
                datasets.append(fo.load_dataset(name))
            except Exception as e:
                logger.warning(f"Failed to load dataset {name}: {e}")
        return datasets

    def get_dataset_names(self) -> List[str]:
        """Get names of all available FiftyOne datasets.

        Returns:
            List of dataset names
        """
        return fo.list_datasets()

    def get_dataset_stats(self, dataset_name: str) -> Tuple[int, int]:
        """Get statistics for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Tuple of (labeled_samples, unlabeled_samples)
        """
        try:
            dataset = fo.load_dataset(dataset_name)
            total_samples = len(dataset)

            # Check if predictions field exists
            has_predictions = (
                "predictions" in dataset.get_field_schema().keys()
            )

            if has_predictions:
                # Count samples with predictions
                labeled_view = dataset.match(
                    F("predictions.detections").length() > 0
                )
                labeled_count = len(labeled_view)
                unlabeled_count = total_samples - labeled_count
            else:
                # No predictions field means all are unlabeled
                labeled_count = 0
                unlabeled_count = total_samples

            return labeled_count, unlabeled_count

        except Exception as e:
            logger.error(
                f"Failed to get stats for dataset {dataset_name}: {e}"
            )
            return 0, 0

    def launch(
        self,
        dataset_name: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs,
    ) -> fo.Session:
        """Launch the FiftyOne annotation interface.

        Args:
            dataset_name: Optional dataset to load
            port: Port to use
            **kwargs: Additional arguments for fo.launch_app()

        Returns:
            FiftyOne session object
        """
        port = port or self.config.default_port

        if dataset_name:
            dataset = self.get_dataset(dataset_name=dataset_name)
            logger.info(
                f"Launching FiftyOne App for dataset '{dataset_name}' on port {port}"
            )
        else:
            dataset = None
            logger.info(f"Launching FiftyOne App on port {port}")

        # Launch the app
        session = fo.launch_app(dataset, port=port, **kwargs)

        if self.config.auto_launch:
            webbrowser.open(self.get_url(port))

        logger.info(f"FiftyOne App available at: {self.get_url(port)}")
        return session

    def add_dataset(
        self,
        dataset_source: str = "coco-2017",
        split: str = "validation",
        max_samples: int = 50,
        dataset_name: Optional[str] = None,
        **kwargs,
    ) -> fo.Dataset:
        """Add/register a dataset for annotation.

        Args:
            dataset_source: Source dataset (e.g., 'coco-2017')
            split: Dataset split to load
            max_samples: Maximum number of samples
            dataset_name: Custom name for the dataset
            **kwargs: Additional arguments for dataset loading

        Returns:
            The loaded FiftyOne dataset
        """
        if not dataset_name:
            dataset_name = f"{dataset_source}-{split}-{max_samples}samples"

        logger.info(
            f"Loading {dataset_source} {split} dataset with max {max_samples} samples..."
        )

        # Load dataset from FiftyOne zoo
        dataset = foz.load_zoo_dataset(
            dataset_source,
            split=split,
            max_samples=max_samples,
            dataset_name=dataset_name,
            shuffle=True,
            persistent=True,
            **kwargs,
        )

        logger.info(f"Loaded {len(dataset)} samples from {dataset_source}")
        return dataset

    def get_dataset(self, dataset_name: str, **kwargs) -> fo.Dataset:
        """Get a dataset by name.

        Args:
            dataset_name: Name of the dataset
            **kwargs: Additional arguments

        Returns:
            The FiftyOne dataset
        """
        try:
            return fo.load_dataset(dataset_name)
        except ValueError as e:
            logger.error(f"Dataset '{dataset_name}' not found: {e}")
            available = self.get_dataset_names()
            logger.info(f"Available datasets: {available}")
            raise

    def delete_dataset(self, dataset_name: str, **kwargs) -> None:
        """Delete a dataset.

        Args:
            dataset_name: Name of the dataset to delete
            **kwargs: Additional arguments
        """
        try:
            dataset = fo.load_dataset(dataset_name)
            dataset.delete()
            logger.info(f"Deleted dataset '{dataset_name}'")
        except Exception as e:
            logger.error(f"Failed to delete dataset '{dataset_name}': {e}")
            raise

    def get_labeled_data(self, dataset_name: str, **kwargs) -> fo.DatasetView:
        """Get labeled samples from a dataset.

        Args:
            dataset_name: Name of the dataset
            **kwargs: Additional arguments

        Returns:
            View of labeled samples
        """
        dataset = self.get_dataset(dataset_name)

        # Check if predictions exist
        if "predictions" in dataset.get_field_schema().keys():
            labeled_view = dataset.match(
                F("predictions.detections").length() > 0
            )
        else:
            # If no predictions, return empty view
            labeled_view = dataset.limit(0)

        logger.info(
            f"Found {len(labeled_view)} labeled samples in '{dataset_name}'"
        )
        return labeled_view

    def get_unlabeled_data(
        self, dataset_name: str, **kwargs
    ) -> fo.DatasetView:
        """Get unlabeled samples from a dataset.

        Args:
            dataset_name: Name of the dataset
            **kwargs: Additional arguments

        Returns:
            View of unlabeled samples
        """
        dataset = self.get_dataset(dataset_name)

        # Check if predictions exist
        if "predictions" in dataset.get_field_schema().keys():
            unlabeled_view = dataset.match(
                F("predictions.detections").length() == 0
            )
        else:
            # If no predictions field, all samples are unlabeled
            unlabeled_view = dataset

        logger.info(
            f"Found {len(unlabeled_view)} unlabeled samples in '{dataset_name}'"
        )
        return unlabeled_view

    def export_to_yolo_format(
        self,
        dataset_name: str,
        export_dir: Union[str, Path],
        classes: Optional[List[str]] = None,
    ) -> Path:
        """Export dataset to YOLO format for training.

        Args:
            dataset_name: Name of the dataset to export
            export_dir: Directory to export to
            classes: List of class names to use (defaults to COCO classes)

        Returns:
            Path to the exported dataset directory
        """
        dataset = self.get_dataset(dataset_name)
        export_dir = Path(export_dir)
        classes = classes or COCO_CLASSES

        logger.info(
            f"Exporting dataset '{dataset_name}' to {export_dir} in YOLO format..."
        )

        # Clean up existing directory
        if export_dir.exists():
            logger.info("Removing existing export directory...")
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Export with correct class mapping
        for split in ["train", "val"]:
            dataset.export(
                export_dir=str(export_dir),
                dataset_type=fo.types.YOLOv5Dataset,
                split=split,
                classes=classes,
            )

        logger.info(f"Dataset exported successfully to {export_dir}")
        return export_dir

    def run_inference_and_add_predictions(
        self,
        dataset_name: str,
        model: YOLO,
        confidence_threshold: float = 0.25,
        predictions_field: str = "predictions",
    ) -> str:
        """Run model inference on dataset and add predictions.

        Args:
            dataset_name: Name of the FiftyOne dataset
            model: Trained YOLO model
            confidence_threshold: Minimum confidence threshold
            predictions_field: Name of the field to store predictions

        Returns:
            Name of the updated dataset
        """
        dataset = self.get_dataset(dataset_name)
        logger.info(
            f"Running inference on {len(dataset)} samples with confidence >= {confidence_threshold}"
        )

        # Clear existing predictions
        if predictions_field in dataset.get_field_schema().keys():
            logger.info(f"Clearing existing '{predictions_field}' field...")
            dataset.delete_sample_field(predictions_field)

        # Run inference on each sample
        for sample in dataset:
            try:
                # Run YOLO inference
                results = model(
                    sample.filepath, conf=confidence_threshold, verbose=False
                )
                result = results[0]  # First result

                # Convert YOLO results to FiftyOne format
                detections = []
                if result.boxes is not None:
                    boxes = result.boxes
                    for box in boxes:
                        # Get normalized coordinates (FiftyOne expects [0, 1] range)
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        img_h, img_w = result.orig_shape

                        # Convert to relative coordinates and width/height format
                        rel_x = x1 / img_w
                        rel_y = y1 / img_h
                        rel_w = (x2 - x1) / img_w
                        rel_h = (y2 - y1) / img_h

                        # Get class info
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = model.names[class_id]

                        detection = fo.Detection(
                            label=class_name,
                            bounding_box=[rel_x, rel_y, rel_w, rel_h],
                            confidence=confidence,
                        )
                        detections.append(detection)

                # Add detections to sample
                sample[predictions_field] = fo.Detections(
                    detections=detections
                )
                sample.save()

            except Exception as e:
                logger.warning(f"Failed to process sample {sample.id}: {e}")
                continue

        logger.info(
            f"✅ Added predictions to {len(dataset)} samples in field '{predictions_field}'"
        )
        return dataset_name

    def evaluate_predictions(
        self,
        dataset_name: str,
        predictions_field: str = "predictions",
        gt_field: str = "ground_truth",
    ) -> Dict[str, Any]:
        """Evaluate predictions against ground truth.

        Args:
            dataset_name: Name of the dataset
            predictions_field: Field containing predictions
            gt_field: Field containing ground truth

        Returns:
            Dictionary containing evaluation metrics
        """
        dataset = self.get_dataset(dataset_name)
        logger.info(
            f"Evaluating predictions in '{predictions_field}' against '{gt_field}'"
        )

        # Run separate evaluations at different IoU thresholds
        results_50 = dataset.evaluate_detections(
            predictions_field,
            gt_field=gt_field,
            eval_key="eval_50",
            iou=0.5,
            compute_mAP=True,
        )

        results_75 = dataset.evaluate_detections(
            predictions_field,
            gt_field=gt_field,
            eval_key="eval_75",
            iou=0.75,
            compute_mAP=True,
        )

        # Extract metrics
        metrics = results_50.metrics()
        mAP_50 = metrics.get("mAP")

        metrics_75 = results_75.metrics()
        mAP_75 = metrics_75.get("mAP")

        # Get per-class metrics
        class_metrics = {}
        if hasattr(results_50, "report"):
            try:
                report_data = results_50.report()
                if isinstance(report_data, dict):
                    class_metrics = report_data
            except Exception:
                logger.warning("Could not extract detailed per-class metrics")

        evaluation_results = {
            "mAP_50": mAP_50,
            "mAP_75": mAP_75,
            "class_metrics": class_metrics,
            "total_samples": len(dataset),
            "eval_keys": ["eval_50", "eval_75"],
        }

        # Log results
        mAP_50_str = f"{mAP_50:.3f}" if mAP_50 is not None else "N/A"
        mAP_75_str = f"{mAP_75:.3f}" if mAP_75 is not None else "N/A"

        logger.info(f"mAP@0.5: {mAP_50_str}")
        logger.info(f"mAP@0.75: {mAP_75_str}")
        logger.info("Per-class performance:")

        for class_name, metrics in class_metrics.items():
            mAP_val = metrics.get("mAP")
            precision_val = metrics.get("precision")
            recall_val = metrics.get("recall")

            mAP_str = f"{mAP_val:.3f}" if mAP_val is not None else "N/A"
            precision_str = (
                f"{precision_val:.3f}" if precision_val is not None else "N/A"
            )
            recall_str = (
                f"{recall_val:.3f}" if recall_val is not None else "N/A"
            )

            logger.info(
                f"  {class_name}: mAP={mAP_str}, P={precision_str}, R={recall_str}"
            )

        return evaluation_results
