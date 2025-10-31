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

from annotators import FiftyOneAnnotator
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
    # Initialize FiftyOne annotator
    annotator = FiftyOneAnnotator()

    # Run inference and add predictions using the annotator
    return annotator.run_inference_and_add_predictions(
        dataset_name=fiftyone_dataset_name,
        model=trained_model,
        confidence_threshold=confidence_threshold,
    )


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
    # Initialize FiftyOne annotator
    annotator = FiftyOneAnnotator()

    # Use annotator to evaluate predictions
    return annotator.evaluate_predictions(dataset_name=fiftyone_dataset_name)


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
    # Initialize FiftyOne annotator
    annotator = FiftyOneAnnotator()

    # Get dataset stats using annotator
    labeled_count, unlabeled_count = annotator.get_dataset_stats(
        fiftyone_dataset_name
    )
    total_samples = labeled_count + unlabeled_count

    logger.info(f"Dataset '{fiftyone_dataset_name}' ready for analysis:")
    logger.info(f"  • Total samples: {total_samples}")
    logger.info(f"  • Samples with predictions: {labeled_count}")
    logger.info(f"  • Samples without predictions: {unlabeled_count}")

    # Show analysis summary
    if analysis_results:
        mAP_50 = analysis_results.get("mAP_50")
        mAP_75 = analysis_results.get("mAP_75")

        if mAP_50 is not None:
            logger.info(f"  • mAP@0.5: {mAP_50:.3f}")
        if mAP_75 is not None:
            logger.info(f"  • mAP@0.75: {mAP_75:.3f}")

    logger.info("\n🎯 FiftyOne Dashboard Access:")
    logger.info(
        f"  Launch command: python launch_fiftyone.py {fiftyone_dataset_name}"
    )
    logger.info("  Default URL: http://localhost:5151")
    logger.info(
        "  Custom port: python launch_fiftyone.py {dataset_name} --port 8080"
    )

    return f"FiftyOne dashboard ready for '{fiftyone_dataset_name}'"


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
