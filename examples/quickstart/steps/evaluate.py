"""Evaluation steps for comparing agent performance."""

import base64
import io
import time
from typing import Annotated, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from utils import call_llm_generic_response
from visualizations import render_evaluation_template

from zenml import log_metadata, step
from zenml.client import Client
from zenml.logger import get_logger
from zenml.types import HTMLString

logger = get_logger(__name__)


@step
def evaluate_agent_performance(
    test_texts: List[str], test_labels: List[str]
) -> Tuple[
    Annotated[Dict, "evaluation_results"],
    Annotated[HTMLString, "confusion_matrices_html"],
]:
    """Evaluate both LLM-only and With Intent Classifier agent performance."""
    logger.info(f"Evaluating agent performance on {len(test_texts)} examples")

    # Evaluate LLM-only mode
    logger.info("Evaluating LLM-only mode...")
    llm_predictions, llm_latencies = _evaluate_llm_mode(
        test_texts, test_labels
    )

    # Evaluate With Intent Classifier mode (try to load production classifier)
    classifier = _load_production_classifier()
    if classifier is not None:
        logger.info("Evaluating With Intent Classifier mode...")
        classifier_predictions, classifier_latencies = (
            _evaluate_with_classifier_mode(test_texts, test_labels, classifier)
        )
    else:
        logger.warning(
            "No classifier available - skipping classifier evaluation"
        )
        classifier_predictions, classifier_latencies = [], []

    # Calculate metrics
    results = {
        "test_size": len(test_texts),
        "llm_only": _calculate_metrics(
            test_labels, llm_predictions, llm_latencies
        ),
    }

    if classifier_predictions:
        results["with_classifier"] = _calculate_metrics(
            test_labels, classifier_predictions, classifier_latencies
        )
        results["comparison"] = _compare_modes(
            results["llm_only"], results["with_classifier"]
        )

    # Generate visualizations
    confusion_matrix_html = None
    if classifier_predictions:
        confusion_matrix_html = _create_comparison_plots(
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
                "llm_accuracy": results["llm_only"]["accuracy"],
                "classifier_accuracy": results["with_classifier"]["accuracy"]
                if "with_classifier" in results
                else None,
            },
            "performance_comparison": results.get("comparison", {}),
            "latency_analysis": {
                "llm_avg_latency": results["llm_only"]["avg_latency_ms"],
                "classifier_avg_latency": results["with_classifier"][
                    "avg_latency_ms"
                ]
                if "with_classifier" in results
                else None,
                "speedup_factor": results["comparison"]["latency_improvement"]
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


def _load_production_classifier():
    """Load the production-tagged classifier from the artifact store."""
    try:
        client = Client()
        # Find the intent-classifier artifact with production tag
        artifacts = client.list_artifact_versions(
            name="intent-classifier", tags=["production"]
        )
        if not artifacts.items:
            logger.warning("No production-tagged classifier found")
            return None

        # Get the latest production artifact
        latest_artifact = artifacts.items[
            0
        ]  # Already sorted by created time desc
        classifier = latest_artifact.load()
        logger.info(f"Loaded production classifier: {latest_artifact.id}")
        return classifier

    except Exception as e:
        logger.error(f"Failed to load production classifier: {e}")
        return None


def _evaluate_llm_mode(
    test_texts: List[str],
    test_labels: List[str],  # noqa: ARG001
) -> Tuple[List[str], List[float]]:
    """Evaluate LLM-only mode performance (generic responses, no intent classification)."""
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
    test_texts: List[str],
    test_labels: List[str],
    classifier,  # noqa: ARG001
) -> Tuple[List[str], List[float]]:
    """Evaluate With Intent Classifier mode performance."""
    predictions = []
    latencies = []

    for text in test_texts:
        start_time = time.time()
        # Classifier prediction (fast)
        predicted_intent = classifier.predict([text])[0]
        end_time = time.time()

        predictions.append(predicted_intent)
        latencies.append(
            (end_time - start_time) * 1000
        )  # Convert to milliseconds

    return predictions, latencies


def _calculate_metrics(
    labels: List[str], predictions: List[str], latencies: List[float]
) -> Dict:
    """Calculate performance metrics."""
    return {
        "accuracy": round(accuracy_score(labels, predictions), 3),
        "f1_score": round(
            f1_score(labels, predictions, average="weighted"), 3
        ),
        "avg_latency_ms": round(np.mean(latencies), 2),
        "p95_latency_ms": round(np.percentile(latencies, 95), 2),
        "total_predictions": len(predictions),
        "classification_report": classification_report(
            labels, predictions, output_dict=True
        ),
    }


def _compare_modes(llm_results: Dict, classifier_results: Dict) -> Dict:
    """Compare LLM-only and With Intent Classifier mode performance."""
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
            1,
        ),
    }


def _create_comparison_plots(
    labels: List[str], llm_preds: List[str], classifier_preds: List[str]
) -> str:
    """Create modern, interactive-style confusion matrices with ZenML branding."""
    # Get unique labels for consistent ordering
    unique_labels = sorted(list(set(labels)))

    # Create confusion matrices
    llm_cm = confusion_matrix(labels, llm_preds, labels=unique_labels)
    classifier_cm = confusion_matrix(
        labels, classifier_preds, labels=unique_labels
    )

    # Calculate performance metrics for display
    llm_accuracy = accuracy_score(labels, llm_preds)
    classifier_accuracy = accuracy_score(labels, classifier_preds)
    llm_f1 = f1_score(labels, llm_preds, average="weighted")
    classifier_f1 = f1_score(labels, classifier_preds, average="weighted")

    # Determine which is better
    accuracy_winner = (
        "With Classifier"
        if classifier_accuracy > llm_accuracy
        else "LLM-only"
        if llm_accuracy > classifier_accuracy
        else "Tie"
    )
    f1_winner = (
        "With Classifier"
        if classifier_f1 > llm_f1
        else "LLM-only"
        if llm_f1 > classifier_f1
        else "Tie"
    )

    # ZenML color palette (defined but used in color scheme below)
    # zenml_colors = ["#f8faff", "#e1e7ff", "#c7d2fe", "#a5b4fc", "#8b5cf6", "#7c3aed", "#6d28d9"]

    # Set modern style
    plt.style.use("default")

    # Create figure with better layout and modern styling
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#ffffff")

    # Modern LLM confusion matrix with ZenML colors
    sns.heatmap(
        llm_cm,
        annot=True,
        fmt="d",
        cmap=sns.light_palette("#8b5cf6", as_cmap=True),
        xticklabels=unique_labels,
        yticklabels=unique_labels,
        ax=ax1,
        cbar_kws={"shrink": 0.8},
        square=True,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"size": 12, "weight": "bold"},
    )
    ax1.set_title(
        "LLM-Only Mode",
        fontsize=16,
        fontweight="bold",
        color="#374151",
        pad=20,
    )
    ax1.set_xlabel(
        "Predicted Intent", fontsize=12, fontweight="600", color="#6b7280"
    )
    ax1.set_ylabel(
        "True Intent", fontsize=12, fontweight="600", color="#6b7280"
    )
    ax1.tick_params(axis="both", which="major", labelsize=10)

    # Modern With Intent Classifier confusion matrix with complementary ZenML colors
    sns.heatmap(
        classifier_cm,
        annot=True,
        fmt="d",
        cmap=sns.light_palette("#10b981", as_cmap=True),  # ZenML green accent
        xticklabels=unique_labels,
        yticklabels=unique_labels,
        ax=ax2,
        cbar_kws={"shrink": 0.8},
        square=True,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"size": 12, "weight": "bold"},
    )
    ax2.set_title(
        "With Intent Classifier",
        fontsize=16,
        fontweight="bold",
        color="#374151",
        pad=20,
    )
    ax2.set_xlabel(
        "Predicted Intent", fontsize=12, fontweight="600", color="#6b7280"
    )
    ax2.set_ylabel(
        "True Intent", fontsize=12, fontweight="600", color="#6b7280"
    )
    ax2.tick_params(axis="both", which="major", labelsize=10)

    # Improve overall layout
    plt.tight_layout(pad=3.0)

    # Convert plot to high-quality base64 image
    img_buffer = io.BytesIO()
    plt.savefig(
        img_buffer,
        format="png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
        pad_inches=0.2,
    )
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()

    # Use the template system to render the visualization
    html_content = render_evaluation_template(
        img_base64=img_base64,
        llm_accuracy=llm_accuracy,
        classifier_accuracy=classifier_accuracy,
        llm_f1=llm_f1,
        classifier_f1=classifier_f1,
        accuracy_winner=accuracy_winner,
        f1_winner=f1_winner,
    )

    logger.info(
        "Generated modern confusion matrix visualization with ZenML styling"
    )
    return html_content


@step
def generate_test_dataset() -> Tuple[
    Annotated[List[str], "test_texts"], Annotated[List[str], "test_labels"]
]:
    """Generate a test dataset for evaluation (different from training)."""
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
