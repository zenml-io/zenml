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

import re
import shutil
import uuid
import webbrowser
from datetime import datetime, timezone
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

    def _sanitize(self, value: str, max_len: int = 63) -> str:
        """Sanitize a string for safe use as a FiftyOne field name.

        Field names should be concise and contain only letters, digits, or underscores.
        This method:
          - replaces any invalid characters with underscores
          - collapses repeated underscores into a single underscore
          - strips leading/trailing underscores
          - truncates to a maximum length
          - falls back to 'field' if the result would be empty

        Args:
            value: Input string to sanitize
            max_len: Maximum allowed length of the result

        Returns:
            A sanitized string suitable for use as a field name
        """
        try:
            s = "" if value is None else str(value)
            # Replace non-alphanumeric/underscore characters with underscores
            s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
            # Collapse consecutive underscores
            s = re.sub(r"_+", "_", s)
            # Strip leading/trailing underscores
            s = s.strip("_")

            # Ensure non-empty fallback
            if not s:
                s = "field"

            # Truncate to the allowed maximum length
            if max_len > 0 and len(s) > max_len:
                s = s[:max_len]

            return s
        except Exception as e:
            # Defensive fallback to avoid hard failures on unexpected inputs
            logger.warning(f"Sanitization failed for value '{value}': {e}")
            return "field"

    def _default_version_suffix(self) -> str:
        """Generate a default version suffix suitable for field names.

        Combines a UTC timestamp and an 8-character UUID fragment to minimize
        collisions while keeping the result reasonably short:
        Example: '20250310T134501Z_1a2b3c4d'

        Returns:
            A version suffix string
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        short_uuid = uuid.uuid4().hex[:8]
        return f"{ts}_{short_uuid}"

    def list_prediction_fields(
        self, dataset_name: str, base_field: str = "predictions"
    ) -> List[str]:
        """List all prediction fields on a dataset.

        A prediction field is defined as either the exact base_field or any field
        starting with base_field followed by an underscore (e.g., 'predictions_...').

        Args:
            dataset_name: Name of the FiftyOne dataset
            base_field: Base field name to match

        Returns:
            Sorted list of prediction field names
        """
        try:
            dataset = self.get_dataset(dataset_name)
            schema = dataset.get_field_schema()
            if not isinstance(schema, dict):
                return []

            fields: List[str] = []
            prefix = f"{base_field}_"
            for fname in schema.keys():
                if fname == base_field or fname.startswith(prefix):
                    fields.append(fname)

            fields = sorted(set(fields))
            return fields
        except Exception as e:
            logger.error(
                f"Failed to list prediction fields for dataset '{dataset_name}': {e}"
            )
            return []

    def get_latest_prediction_field(
        self, dataset_name: str, base_field: str = "predictions"
    ) -> Optional[str]:
        """Resolve the latest prediction field for a dataset.

        Resolution order:
          1) dataset.info['latest_predictions_field'] if present and exists in schema
          2) base_field if it exists in schema
          3) None if no prediction fields are found

        Args:
            dataset_name: Name of the FiftyOne dataset
            base_field: Base field name to consider

        Returns:
            The name of the latest prediction field, or None if unavailable
        """
        try:
            dataset = self.get_dataset(dataset_name)
            schema = dataset.get_field_schema()
            info_latest = dataset.info.get("latest_predictions_field")

            if isinstance(info_latest, str):
                if info_latest in schema:
                    return info_latest
                else:
                    logger.warning(
                        f"latest_predictions_field '{info_latest}' not found in schema "
                        f"for dataset '{dataset_name}'"
                    )

            if base_field in schema:
                return base_field

            # As a best-effort fallback, try to detect any matching fields
            candidates = self.list_prediction_fields(
                dataset_name=dataset_name, base_field=base_field
            )
            if candidates:
                # Return the last lexicographically as a heuristic; caller can override
                return candidates[-1]

            return None
        except Exception as e:
            logger.error(
                f"Failed to determine latest prediction field for dataset '{dataset_name}': {e}"
            )
            return None

    def set_latest_prediction_field(
        self, dataset_name: str, field_name: str
    ) -> None:
        """Set the latest prediction field pointer in dataset.info.

        Note: This method updates dataset.info and persists the dataset.

        Args:
            dataset_name: Name of the dataset
            field_name: Field name to mark as latest
        """
        dataset = self.get_dataset(dataset_name)
        try:
            schema = dataset.get_field_schema()
            if field_name not in schema:
                logger.warning(
                    f"Setting latest_predictions_field to '{field_name}', "
                    f"but it does not exist in dataset '{dataset_name}' schema"
                )
            dataset.info["latest_predictions_field"] = field_name
            dataset.save()
        except Exception as e:
            logger.error(
                f"Failed to set latest prediction field for dataset '{dataset_name}': {e}"
            )
            raise

    def append_prediction_version_info(
        self, dataset_name: str, entry: Dict[str, Any]
    ) -> None:
        """Append a prediction version entry to dataset.info.

        This creates dataset.info['prediction_versions'] if it does not exist,
        appends the provided entry, and saves the dataset.

        Args:
            dataset_name: Name of the dataset
            entry: Metadata entry to append
        """
        dataset = self.get_dataset(dataset_name)
        try:
            if not isinstance(entry, dict):
                raise ValueError("entry must be a dictionary")

            versions = dataset.info.get("prediction_versions", [])
            if not isinstance(versions, list):
                versions = []

            versions.append(entry)
            dataset.info["prediction_versions"] = versions
            dataset.save()
        except Exception as e:
            logger.error(
                f"Failed to append prediction version info for dataset '{dataset_name}': {e}"
            )
            raise

    def get_prediction_versions_info(
        self, dataset_name: str
    ) -> List[Dict[str, Any]]:
        """Get the list of prediction version entries from dataset.info.

        Args:
            dataset_name: Name of the dataset

        Returns:
            A list of prediction version metadata entries (possibly empty)
        """
        try:
            dataset = self.get_dataset(dataset_name)
            versions = dataset.info.get("prediction_versions", [])
            if not isinstance(versions, list):
                return []
            # Ensure we only return dict entries
            return [v for v in versions if isinstance(v, dict)]
        except Exception as e:
            logger.error(
                f"Failed to get prediction versions info for dataset '{dataset_name}': {e}"
            )
            return []

    def describe_prediction_versions(
        self, dataset_name: str
    ) -> List[Dict[str, Any]]:
        """Describe prediction versions with latest marker and sorted order.

        Sorting strategy:
          - If 'created_at' timestamps (ISO 8601) are present, sort by created_at ascending
            and then reverse to return newest first.
          - Otherwise, sort by 'field' to provide a deterministic order.

        Args:
            dataset_name: Name of the dataset

        Returns:
            A list of version entries with 'is_latest' boolean added. The dataset is
            not modified by this method.
        """
        try:
            dataset = self.get_dataset(dataset_name)
            latest = dataset.info.get("latest_predictions_field")
            raw_versions = dataset.info.get("prediction_versions", [])

            versions: List[Dict[str, Any]] = []
            if isinstance(raw_versions, list):
                for v in raw_versions:
                    if isinstance(v, dict):
                        entry = dict(v)
                        entry["is_latest"] = (
                            isinstance(latest, str)
                            and entry.get("field") == latest
                        )
                        versions.append(entry)

            # Try to sort by created_at (ISO strings sort lexicographically)
            def sort_key(e: Dict[str, Any]) -> Tuple[int, str]:
                created = e.get("created_at")
                if isinstance(created, str) and created:
                    # '0' ensures entries with created_at come first in ascending order
                    return (0, created)
                # '1' places entries without created_at after those with it
                return (1, str(e.get("field", "")))

            versions.sort(key=sort_key)
            # Newest first if created_at is ISO ascending
            versions = versions[::-1]
            return versions
        except Exception as e:
            logger.error(
                f"Failed to describe prediction versions for dataset '{dataset_name}': {e}"
            )
            return []

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

            # Resolve latest predictions field, if any
            latest_field = self.get_latest_prediction_field(dataset_name)
            if latest_field:
                logger.info(
                    f"Computing dataset stats using predictions field '{latest_field}'"
                )
                labeled_view = dataset.match(
                    F(f"{latest_field}.detections").length() > 0
                )
                labeled_count = len(labeled_view)
                unlabeled_count = total_samples - labeled_count
            else:
                # No prediction field means all are unlabeled
                logger.info(
                    "No predictions field found; treating all samples as unlabeled for stats"
                )
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

    def get_labeled_data(
        self,
        dataset_name: str,
        predictions_field: Optional[str] = None,
        **kwargs,
    ) -> fo.DatasetView:
        """Get labeled samples from a dataset.

        Args:
            dataset_name: Name of the dataset
            predictions_field: Optional predictions field to use; if None, auto-resolve latest
            **kwargs: Additional arguments

        Returns:
            View of labeled samples
        """
        dataset = self.get_dataset(dataset_name)

        # Resolve which predictions field to use
        field = predictions_field or self.get_latest_prediction_field(
            dataset_name
        )
        if field:
            logger.info(
                f"Selecting labeled data using predictions field '{field}'"
            )
            labeled_view = dataset.match(F(f"{field}.detections").length() > 0)
        else:
            # If no predictions, return empty view
            logger.info(
                "No predictions field found; returning empty labeled view"
            )
            labeled_view = dataset.limit(0)

        logger.info(
            f"Found {len(labeled_view)} labeled samples in '{dataset_name}'"
        )
        return labeled_view

    def get_unlabeled_data(
        self,
        dataset_name: str,
        predictions_field: Optional[str] = None,
        **kwargs,
    ) -> fo.DatasetView:
        """Get unlabeled samples from a dataset.

        Args:
            dataset_name: Name of the dataset
            predictions_field: Optional predictions field to use; if None, auto-resolve latest
            **kwargs: Additional arguments

        Returns:
            View of unlabeled samples
        """
        dataset = self.get_dataset(dataset_name)

        # Resolve which predictions field to use
        field = predictions_field or self.get_latest_prediction_field(
            dataset_name
        )
        if field:
            logger.info(
                f"Selecting unlabeled data using predictions field '{field}'"
            )
            unlabeled_view = dataset.match(
                F(f"{field}.detections").length() == 0
            )
        else:
            # If no predictions field, all samples are unlabeled
            logger.info(
                "No predictions field found; treating all samples as unlabeled"
            )
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
        version_suffix: Optional[str] = None,
        record_metadata: bool = True,
        zenml_metadata: Optional[Dict[str, Any]] = None,
        also_update_latest_alias: bool = True,
    ) -> str:
        """Run model inference on dataset and add predictions.

        This method supports versioned prediction fields and metadata lineage tracking.
        Past predictions are retained by creating a unique versioned field for each run,
        with an optional mirror to a stable alias for compatibility.

        Args:
            dataset_name: Name of the FiftyOne dataset
            model: Trained YOLO model
            confidence_threshold: Minimum confidence threshold
            predictions_field: Base field name to store predictions (alias, if mirroring)
            version_suffix: Optional custom suffix for versioned field name
            record_metadata: Whether to store lineage metadata in dataset.info
            zenml_metadata: Optional ZenML lineage info to persist
            also_update_latest_alias: Whether to mirror to the stable predictions_field alias

        Returns:
            Name of the updated dataset
        """
        dataset = self.get_dataset(dataset_name)
        logger.info(
            f"Running inference on {len(dataset)} samples with confidence >= {confidence_threshold}"
        )

        # Determine unique versioned field name without deleting existing predictions
        schema = dataset.get_field_schema()
        # Sanitize provided suffix or generate a default timestamp+uuid suffix
        suffix = (
            self._sanitize(version_suffix)
            if version_suffix
            else self._default_version_suffix()
        )
        versioned_field = f"{predictions_field}_{suffix}"

        # Ensure uniqueness by checking schema and regenerating if needed
        attempts = 0
        while versioned_field in schema.keys():
            attempts += 1
            # Regenerate only the suffix to avoid bloating the base name
            suffix = self._default_version_suffix()
            versioned_field = f"{predictions_field}_{suffix}"
            if attempts >= 10:
                # Extremely unlikely; proceed anyway with the last generated value
                logger.warning(
                    f"Collision detected repeatedly when generating versioned field name for '{predictions_field}'. "
                    f"Proceeding with '{versioned_field}'."
                )
                break

        logger.info(
            f"Writing predictions to versioned field '{versioned_field}'"
        )
        if also_update_latest_alias:
            logger.info(
                f"Also mirroring predictions to alias '{predictions_field}'"
            )

        # Run inference on each sample (YOLO logic unchanged)
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
                det_obj = fo.Detections(detections=detections)
                sample[versioned_field] = det_obj
                if also_update_latest_alias:
                    # Mirror to stable alias for backward compatibility
                    sample[predictions_field] = det_obj

                # Add ZenML dashboard URL to sample for easy access in UI
                if zenml_metadata and "zenml_dashboard_url" in zenml_metadata:
                    sample[f"{versioned_field}_zenml_url"] = zenml_metadata[
                        "zenml_dashboard_url"
                    ]
                    if also_update_latest_alias:
                        sample[f"{predictions_field}_zenml_url"] = (
                            zenml_metadata["zenml_dashboard_url"]
                        )

                sample.save()

            except Exception as e:
                logger.warning(f"Failed to process sample {sample.id}: {e}")
                continue

        logger.info(
            f"✅ Added predictions to {len(dataset)} samples in field '{versioned_field}'"
            + (
                f" (mirrored to '{predictions_field}')"
                if also_update_latest_alias
                else ""
            )
        )

        # Record metadata and update latest pointer
        try:
            # Extract classes from model if available; otherwise fall back to COCO
            classes: List[str]
            try:
                names = getattr(model, "names", None)
                classes = (
                    list(names.values())
                    if isinstance(names, dict)
                    else COCO_CLASSES
                )
            except Exception:
                classes = COCO_CLASSES

            # Extract model name/version gracefully
            model_name = getattr(model, "model", None)
            if model_name is None:
                model_name = (
                    getattr(model, "name", None) or model.__class__.__name__
                )
            model_version = getattr(model, "version", None) or "unknown"

            if record_metadata:
                entry: Dict[str, Any] = {
                    "field": versioned_field,
                    "created_at": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "base_field": predictions_field,
                    "params": {
                        "confidence_threshold": confidence_threshold,
                    },
                    "model": {
                        "name": str(model_name),
                        "version": str(model_version),
                        "classes": classes,
                    },
                    "zenml": zenml_metadata or {},
                }
                self.append_prediction_version_info(dataset_name, entry)

            # Update the 'latest' pointer to the versioned field
            self.set_latest_prediction_field(dataset_name, versioned_field)
        except Exception as e:
            logger.warning(
                f"Failed to record prediction metadata or update latest field for dataset '{dataset_name}': {e}"
            )

        return dataset_name

    def evaluate_predictions(
        self,
        dataset_name: str,
        predictions_field: Optional[str] = None,
        gt_field: str = "ground_truth",
    ) -> Dict[str, Any]:
        """Evaluate predictions against ground truth.

        Args:
            dataset_name: Name of the dataset
            predictions_field: Optional field containing predictions; if None, auto-resolve latest
            gt_field: Field containing ground truth

        Returns:
            Dictionary containing evaluation metrics
        """
        dataset = self.get_dataset(dataset_name)
        # Resolve which predictions field to use: prefer provided, else latest known, else fallback alias
        resolved_field = (
            predictions_field
            or self.get_latest_prediction_field(dataset_name)
            or "predictions"
        )
        if predictions_field is None:
            logger.info(
                f"Evaluating using predictions field '{resolved_field}' (auto-resolved)"
            )
        else:
            logger.info(
                f"Evaluating using predictions field '{resolved_field}' (provided)"
            )

        # Generate unique evaluation keys based on predictions field to avoid conflicts
        eval_key_50 = f"eval_{resolved_field}_50"
        eval_key_75 = f"eval_{resolved_field}_75"

        # Run separate evaluations at different IoU thresholds
        results_50 = dataset.evaluate_detections(
            resolved_field,
            gt_field=gt_field,
            eval_key=eval_key_50,
            iou=0.5,
            compute_mAP=True,
        )

        results_75 = dataset.evaluate_detections(
            resolved_field,
            gt_field=gt_field,
            eval_key=eval_key_75,
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
            "eval_keys": [eval_key_50, eval_key_75],
            "predictions_field_used": resolved_field,
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
