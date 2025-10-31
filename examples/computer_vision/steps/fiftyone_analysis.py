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

"""FiftyOne analysis steps for model evaluation and dataset insights."""

from typing import Annotated, Any, Dict

import fiftyone as fo
from fiftyone import ViewField as F
from ultralytics import YOLO

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


def run_inference_on_fiftyone_dataset(
    fiftyone_dataset_name: str,
    trained_model: YOLO,
    confidence_threshold: float = 0.25,
) -> str:
    """Run inference on FiftyOne dataset and add predictions as new field.

    This step demonstrates the key FiftyOne workflow:
    1. Load an existing FiftyOne dataset
    2. Run model inference on all samples
    3. Add predictions as a new field alongside ground truth
    4. Enable comparison and analysis in FiftyOne App

    Args:
        fiftyone_dataset_name: Name of the FiftyOne dataset to analyze
        trained_model: The trained YOLO model
        confidence_threshold: Minimum confidence for predictions

    Returns:
        Updated FiftyOne dataset name with predictions added
    """
    logger.info(f"Loading FiftyOne dataset: {fiftyone_dataset_name}")

    # Load the existing FiftyOne dataset
    try:
        dataset = fo.load_dataset(fiftyone_dataset_name)
    except ValueError:
        logger.error(f"Dataset {fiftyone_dataset_name} not found")
        raise

    logger.info(f"Dataset loaded with {len(dataset)} samples")
    logger.info(f"Ground truth field: {dataset.default_classes}")

    # Add predictions field to store model outputs
    predictions_field = "predictions"
    logger.info(
        f"Running inference and adding predictions to '{predictions_field}' field"
    )

    # Run inference on each sample
    prediction_count = 0
    for sample in dataset.iter_samples(progress=True):
        image_path = sample.filepath

        # Run YOLO inference
        results = trained_model(
            image_path, conf=confidence_threshold, verbose=False
        )

        # Convert YOLO results to FiftyOne detections
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get bounding box coordinates (normalized)
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    # Normalize coordinates (YOLO uses absolute, FiftyOne needs relative)
                    img_height, img_width = result.orig_shape
                    x1_norm = x1 / img_width
                    y1_norm = y1 / img_height
                    x2_norm = x2 / img_width
                    y2_norm = y2 / img_height

                    # Convert to FiftyOne format (x, y, width, height)
                    width = x2_norm - x1_norm
                    height = y2_norm - y1_norm

                    # Get confidence and class
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = trained_model.names[class_id]

                    detection = fo.Detection(
                        label=class_name,
                        bounding_box=[x1_norm, y1_norm, width, height],
                        confidence=confidence,
                    )
                    detections.append(detection)

        # Add predictions to the sample
        sample[predictions_field] = fo.Detections(detections=detections)
        sample.save()
        prediction_count += len(detections)

    logger.info(
        f"Added {prediction_count} predictions across {len(dataset)} samples"
    )

    # Save the updated dataset
    dataset.save()

    return fiftyone_dataset_name


def analyze_predictions_with_fiftyone(
    fiftyone_dataset_name: str,
) -> Dict[str, Any]:
    """Analyze model predictions vs ground truth using FiftyOne.

    This step showcases FiftyOne's analysis capabilities:
    1. Compare predictions vs ground truth
    2. Generate evaluation metrics
    3. Identify problematic samples
    4. Create visualizations and insights

    Args:
        fiftyone_dataset_name: Name of dataset with predictions added

    Returns:
        Analysis results and insights about model performance
    """
    logger.info(f"Analyzing predictions in dataset: {fiftyone_dataset_name}")

    # Load dataset with predictions
    dataset = fo.load_dataset(fiftyone_dataset_name)

    # Get ground truth and prediction fields
    gt_field = "ground_truth"  # COCO datasets use this by default
    pred_field = "predictions"

    logger.info(f"Comparing {gt_field} vs {pred_field}")

    # Evaluate predictions against ground truth at IoU 0.5
    results_50 = dataset.evaluate_detections(
        pred_field,
        gt_field=gt_field,
        eval_key="eval_50",
        iou=0.5,
        compute_mAP=True,
    )

    # Evaluate at IoU 0.75 for mAP_75
    results_75 = dataset.evaluate_detections(
        pred_field,
        gt_field=gt_field,
        eval_key="eval_75",
        iou=0.75,
        compute_mAP=True,
    )

    # Extract key metrics
    analysis = {
        "mAP_50": results_50.mAP(),
        "mAP_75": results_75.mAP(),
        "num_samples": len(dataset),
        "num_ground_truth": len(
            dataset.values(f"{gt_field}.detections", unwind=True)
        ),
        "num_predictions": len(
            dataset.values(f"{pred_field}.detections", unwind=True)
        ),
    }

    # Get overall precision and recall (from IoU 0.5 evaluation)
    try:
        analysis["precision"] = results_50.precision()
        analysis["recall"] = results_50.recall()
    except Exception as e:
        logger.warning(f"Could not get precision/recall: {e}")
        analysis["precision"] = None
        analysis["recall"] = None

    # Get per-class metrics
    class_metrics = {}
    try:
        for class_name in dataset.distinct(f"{gt_field}.detections.label"):
            class_view = dataset.filter_labels(
                gt_field, F("label") == class_name
            )
            if len(class_view) > 0:
                try:
                    class_results = class_view.evaluate_detections(
                        pred_field,
                        gt_field=gt_field,
                        eval_key=f"eval_50_{class_name}",
                        iou=0.5,
                        compute_mAP=True,
                    )
                    class_metrics[class_name] = {
                        "mAP": class_results.mAP(),
                        "precision": class_results.precision(),
                        "recall": class_results.recall(),
                    }
                except Exception as e:
                    logger.warning(
                        f"Could not evaluate class {class_name}: {e}"
                    )
                    class_metrics[class_name] = {
                        "mAP": None,
                        "precision": None,
                        "recall": None,
                    }
    except Exception as e:
        logger.warning(f"Could not compute per-class metrics: {e}")

    analysis["per_class_metrics"] = class_metrics

    # Calculate confidence statistics manually
    try:
        confidences = dataset.values(
            f"{pred_field}.detections.confidence", unwind=True
        )
        if confidences:
            import statistics

            analysis["confidence_stats"] = {
                "avg_confidence": statistics.mean(confidences),
                "max_confidence": max(confidences),
                "min_confidence": min(confidences),
                "num_detections": len(confidences),
            }
        else:
            analysis["confidence_stats"] = {"num_detections": 0}
    except Exception as e:
        logger.warning(f"Could not compute confidence stats: {e}")
        analysis["confidence_stats"] = {"num_detections": 0}

    # Find samples with false positives and false negatives
    # The eval attribute is attached to prediction labels, not as a top-level field
    try:
        fp_view = dataset.filter_labels(pred_field, F("eval_50") == "fp")
        analysis["samples_with_most_fps"] = len(fp_view)

        fn_view = dataset.filter_labels(pred_field, F("eval_50") == "fn")
        analysis["samples_with_most_fns"] = len(fn_view)
    except Exception as e:
        logger.warning(f"Could not compute FP/FN analysis: {e}")
        analysis["samples_with_most_fps"] = 0
        analysis["samples_with_most_fns"] = 0

    logger.info("Analysis complete!")
    mAP_50 = analysis.get("mAP_50")
    mAP_75 = analysis.get("mAP_75")

    mAP_50_str = f"{mAP_50:.3f}" if mAP_50 is not None else "N/A"
    mAP_75_str = f"{mAP_75:.3f}" if mAP_75 is not None else "N/A"

    logger.info(f"mAP@0.5: {mAP_50_str}")
    logger.info(f"mAP@0.75: {mAP_75_str}")
    logger.info("Per-class performance:")

    for class_name, metrics in class_metrics.items():
        mAP_val = metrics.get("mAP")
        precision_val = metrics.get("precision")
        recall_val = metrics.get("recall")

        mAP_val_str = f"{mAP_val:.3f}" if mAP_val is not None else "N/A"
        precision_str = (
            f"{precision_val:.3f}" if precision_val is not None else "N/A"
        )
        recall_str = f"{recall_val:.3f}" if recall_val is not None else "N/A"

        logger.info(
            f"  {class_name}: mAP={mAP_val_str}, P={precision_str}, R={recall_str}"
        )

    return analysis


def create_fiftyone_dashboard_session(
    fiftyone_dataset_name: str,
    analysis_results: Dict[str, Any],
) -> str:
    """Create a FiftyOne App session for interactive analysis.

    This step demonstrates how to create persistent FiftyOne sessions
    for dataset exploration and model analysis.

    Args:
        fiftyone_dataset_name: Dataset to visualize
        analysis_results: Analysis results for context

    Returns:
        Session information and access details
    """
    logger.info(f"Creating FiftyOne App session for: {fiftyone_dataset_name}")

    # Load dataset
    dataset = fo.load_dataset(fiftyone_dataset_name)

    # Create interesting views for analysis
    views = {}

    # View 1: Samples with predictions
    pred_view = dataset.exists("predictions")
    views["with_predictions"] = f"Samples with predictions ({len(pred_view)})"

    # View 2: High confidence predictions
    high_conf_view = dataset.filter_labels(
        "predictions", F("confidence") > 0.8
    )
    views["high_confidence"] = (
        f"High confidence predictions ({len(high_conf_view)})"
    )

    # View 3: Low confidence predictions (potential issues)
    low_conf_view = dataset.filter_labels("predictions", F("confidence") < 0.3)
    views["low_confidence"] = (
        f"Low confidence predictions ({len(low_conf_view)})"
    )

    # View 4: False positives and false negatives
    try:
        fp_view = dataset.filter_labels("predictions", F("eval_50") == "fp")
        views["false_positives"] = f"False positives ({len(fp_view)})"

        fn_view = dataset.filter_labels("predictions", F("eval_50") == "fn")
        views["false_negatives"] = f"False negatives ({len(fn_view)})"
    except Exception as e:
        logger.warning(f"Could not create FP/FN views: {e}")

    session_info = {
        "dataset_name": fiftyone_dataset_name,
        "total_samples": len(dataset),
        "available_views": views,
        "analysis_summary": {
            "mAP_50": analysis_results.get("mAP_50", "N/A"),
            "mAP_75": analysis_results.get("mAP_75", "N/A"),
            "num_predictions": analysis_results.get("num_predictions", 0),
        },
        "instructions": [
            "1. Start FiftyOne App: `fiftyone app launch`",
            f"2. Load dataset: `fo.load_dataset('{fiftyone_dataset_name}')`",
            "3. Explore ground truth vs predictions side-by-side",
            "4. Use the views above to focus on specific samples",
            "5. Click on samples to see detailed annotations",
        ],
    }

    logger.info("FiftyOne App session ready!")
    logger.info(f"Dataset: {fiftyone_dataset_name}")
    logger.info(f"Available views: {list(views.keys())}")
    logger.info("Start with: fiftyone app launch")

    return str(session_info)


@step
def complete_fiftyone_analysis(
    fiftyone_dataset_name: str,
    trained_model: YOLO,
    confidence_threshold: float = 0.25,
) -> Annotated[Dict[str, Any], "fiftyone_analysis_results"]:
    """Complete FiftyOne analysis workflow: inference + analysis + dashboard setup.

    This combined step performs the entire FiftyOne annotation workflow loop:
    1. Runs inference on the FiftyOne dataset
    2. Analyzes predictions vs ground truth
    3. Sets up interactive dashboard session

    Args:
        fiftyone_dataset_name: Name of the FiftyOne dataset to analyze
        trained_model: The trained YOLO model
        confidence_threshold: Minimum confidence for predictions

    Returns:
        Combined results from inference, analysis, and session setup
    """
    logger.info("Starting complete FiftyOne analysis workflow...")

    # Step 1: Run inference and add predictions
    updated_dataset_name = run_inference_on_fiftyone_dataset(
        fiftyone_dataset_name=fiftyone_dataset_name,
        trained_model=trained_model,
        confidence_threshold=confidence_threshold,
    )

    # Step 2: Analyze predictions vs ground truth
    analysis_results = analyze_predictions_with_fiftyone(
        fiftyone_dataset_name=updated_dataset_name,
    )

    # Step 3: Create dashboard session
    session_info = create_fiftyone_dashboard_session(
        fiftyone_dataset_name=updated_dataset_name,
        analysis_results=analysis_results,
    )

    # Combine all results with dashboard access instructions
    complete_results = {
        "dataset_name": updated_dataset_name,
        "analysis_results": analysis_results,
        "session_info": session_info,
        "dashboard_instructions": {
            "step_1": "fiftyone app launch",
            "step_2": f"fo.load_dataset('{updated_dataset_name}')",
            "step_3": "Explore predictions vs ground truth in the browser",
            "dataset_url": f"http://localhost:5151/datasets/{updated_dataset_name}",
            "quick_commands": [
                "import fiftyone as fo",
                f"dataset = fo.load_dataset('{updated_dataset_name}')",
                "session = fo.launch_app(dataset)",
                "# View dataset in browser at http://localhost:5151",
            ],
        },
    }

    logger.info("Complete FiftyOne analysis workflow finished!")
    logger.info("🎯 Next Steps - Access your FiftyOne Dashboard:")
    logger.info("1. Launch FiftyOne App: fiftyone app launch")
    logger.info(
        f"2. Load your dataset: fo.load_dataset('{updated_dataset_name}')"
    )
    logger.info("3. Open browser to: http://localhost:5151")
    logger.info("4. Compare predictions vs ground truth visually!")

    return complete_results
