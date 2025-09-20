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

"""Evaluation steps for comparing agent performance."""

import time
from typing import Annotated, Any, Dict, List, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)
from utils import call_llm_generic_response, load_production_classifier
from visualizations import create_comparison_plots

from zenml import log_metadata, step
from zenml.logger import get_logger
from zenml.types import HTMLString

logger = get_logger(__name__)


@step
def evaluate_agent_performance(
    test_texts: List[str], test_labels: List[str]
) -> Tuple[
    Annotated[Dict[str, Any], "evaluation_results"],
    Annotated[HTMLString, "confusion_matrices_html"],
]:
    """Evaluate both LLM-only and with Intent Classifier agent performance.

    Args:
        test_texts: List of test text samples.
        test_labels: List of corresponding ground truth labels.

    Returns:
        Tuple of evaluation results dictionary and HTML visualization string.
    """
    logger.info(f"Evaluating agent performance on {len(test_texts)} examples")

    # Evaluate LLM-only mode
    logger.info("Evaluating LLM-only mode...")
    llm_predictions, llm_latencies = _evaluate_llm_mode(test_texts)

    # Evaluate With Intent Classifier mode (try to load production classifier)
    classifier = load_production_classifier()
    if classifier is not None:
        logger.info("Evaluating With Intent Classifier mode...")
        classifier_predictions, classifier_latencies = (
            _evaluate_with_classifier_mode(test_texts, classifier)
        )
    else:
        logger.warning(
            "No classifier available - skipping classifier evaluation"
        )
        classifier_predictions, classifier_latencies = [], []

    # Calculate metrics
    results: Dict[str, Any] = {
        "test_size": len(test_texts),
        "llm_only": _calculate_metrics(
            test_labels, llm_predictions, llm_latencies
        ),
    }

    llm_metrics = results["llm_only"]
    assert isinstance(llm_metrics, dict)

    classifier_metrics: Dict[str, Any] = {}
    if classifier_predictions:
        results["with_classifier"] = _calculate_metrics(
            test_labels, classifier_predictions, classifier_latencies
        )
        classifier_metrics = results["with_classifier"]
        assert isinstance(classifier_metrics, dict)
        results["comparison"] = _compare_modes(llm_metrics, classifier_metrics)

    # Generate visualizations
    confusion_matrix_html = None
    if classifier_predictions:
        confusion_matrix_html = create_comparison_plots(
            test_labels, llm_predictions, classifier_predictions
        )

    # Log comprehensive metadata
    log_metadata(
        metadata={
            "evaluation_summary": {
                "test_samples": len(test_texts),
                "modes_evaluated": "LLM + With Classifier"
                if classifier_predictions
                else "LLM only",
                "llm_accuracy": llm_metrics["accuracy"],
                "classifier_accuracy": classifier_metrics.get("accuracy")
                if classifier_metrics
                else None,
            },
            "performance_comparison": results.get("comparison", {}),
            "latency_analysis": {
                "llm_avg_latency": llm_metrics["avg_latency_ms"],
                "classifier_avg_latency": classifier_metrics.get(
                    "avg_latency_ms"
                )
                if classifier_metrics
                else None,
                "speedup_factor": results["comparison"]["speedup_factor"]
                if "comparison" in results
                else None,
            },
        }
    )

    # Return both results and HTML visualization as separate artifacts
    html_output = HTMLString(
        confusion_matrix_html
        if confusion_matrix_html
        else "No classifier evaluation performed - only LLM mode was evaluated"
    )

    return results, html_output


def _evaluate_llm_mode(test_texts: List[str]) -> Tuple[List[str], List[float]]:
    """Evaluate LLM-only mode performance (generic responses, no intent classification).

    Args:
        test_texts: List of test text samples.

    Returns:
        Tuple of (predictions, latencies) for LLM-only mode.
    """
    predictions = []
    latencies = []

    for text in test_texts:
        start_time = time.time()
        result = call_llm_generic_response(
            text
        )  # Use generic response instead of intent classification
        end_time = time.time()

        predictions.append(result["intent"])  # Will always be "general"
        latencies.append(
            (end_time - start_time) * 1000
        )  # Convert to milliseconds

    return predictions, latencies


def _evaluate_with_classifier_mode(
    test_texts: List[str], classifier: Any
) -> Tuple[List[str], List[float]]:
    """Evaluate With Intent Classifier mode performance.

    Args:
        test_texts: List of test text samples.
        classifier: The trained classifier model.

    Returns:
        Tuple of (predictions, latencies) for classifier mode.
    """
    # Use batch prediction for efficiency
    start_time = time.time()
    predictions = classifier.predict(test_texts).tolist()
    end_time = time.time()

    # Calculate per-sample latency (total time divided by number of samples)
    total_latency_ms = (end_time - start_time) * 1000
    avg_latency_per_sample = total_latency_ms / len(test_texts)
    latencies = [avg_latency_per_sample] * len(test_texts)

    return predictions, latencies


def _calculate_metrics(
    labels: List[str], predictions: List[str], latencies: List[float]
) -> Dict[str, Any]:
    """Calculate performance metrics.

    Args:
        labels: List of ground truth labels.
        predictions: List of predicted labels.
        latencies: List of prediction latencies in milliseconds.

    Returns:
        Dictionary containing accuracy, F1 score, and latency metrics.
    """
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1_score": f1_score(labels, predictions, average="weighted"),
        "avg_latency_ms": np.mean(latencies),
        "p95_latency_ms": np.percentile(latencies, 95),
        "total_predictions": len(predictions),
        "classification_report": classification_report(
            labels, predictions, output_dict=True
        ),
    }


def _compare_modes(
    llm_results: Dict[str, Any], classifier_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare LLM-only and With Intent Classifier mode performance.

    Args:
        llm_results: Performance metrics for LLM-only mode.
        classifier_results: Performance metrics for classifier mode.

    Returns:
        Dictionary containing improvement metrics and winner information.
    """
    return {
        "accuracy_improvement": round(
            classifier_results["accuracy"] - llm_results["accuracy"], 3
        ),
        "f1_improvement": round(
            classifier_results["f1_score"] - llm_results["f1_score"], 3
        ),
        "latency_improvement": round(
            (
                llm_results["avg_latency_ms"]
                - classifier_results["avg_latency_ms"]
            )
            / llm_results["avg_latency_ms"],
            3,
        ),
        "speedup_factor": round(
            llm_results["avg_latency_ms"]
            / classifier_results["avg_latency_ms"],
            2,
        ),
    }


@step
def generate_test_dataset() -> Tuple[
    Annotated[List[str], "test_texts"], Annotated[List[str], "test_labels"]
]:
    """Generate a test dataset for evaluation (different from training).

    Returns:
        Tuple of (test_texts, test_labels) for evaluating agent performance.
    """
    # Create additional test examples not in the training set
    test_data = [
        # Card lost variations
        ("i can't locate my credit card", "card_lost"),
        ("my debit card is nowhere to be found", "card_lost"),
        ("someone stole my card from my purse", "card_lost"),
        # Payment variations
        ("how can i pay my monthly bill", "payments"),
        ("i want to make my payment online", "payments"),
        ("what's the deadline for my payment", "payments"),
        # Balance variations
        ("could you check how much i have available", "account_balance"),
        ("i need to see my current account status", "account_balance"),
        # Dispute variations
        ("there's an error in my statement", "dispute"),
        ("i was charged twice for the same thing", "dispute"),
        # Credit limit variations
        ("can my spending limit be raised", "credit_limit"),
        ("i'd like to request more credit", "credit_limit"),
        # General variations
        ("good afternoon", "general"),
        ("what can you do for me", "general"),
        ("i need help with my banking", "general"),
    ]

    texts, labels = zip(*test_data)
    logger.info(f"Generated test dataset with {len(texts)} examples")

    return list(texts), list(labels)
