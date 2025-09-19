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

from utils import call_llm_for_intent, call_llm_generic_response, classifier_manager
from zenml import get_step_context, log_metadata, step
from zenml.client import Client
from zenml.logger import get_logger
from zenml.types import HTMLString

logger = get_logger(__name__)


@step
def evaluate_agent_performance(
    test_texts: List[str], test_labels: List[str]
) -> Tuple[
    Annotated[Dict, "evaluation_results"],
    Annotated[HTMLString, "confusion_matrices_html"]
]:
    """Evaluate both LLM-only and With Intent Classifier agent performance."""

    logger.info(f"Evaluating agent performance on {len(test_texts)} examples")

    # Evaluate LLM-only mode
    logger.info("Evaluating LLM-only mode...")
    llm_predictions, llm_latencies = _evaluate_llm_mode(test_texts, test_labels)

    # Evaluate With Intent Classifier mode (try to load production classifier)
    classifier = _load_production_classifier()
    if classifier is not None:
        logger.info("Evaluating With Intent Classifier mode...")
        classifier_predictions, classifier_latencies = _evaluate_with_classifier_mode(
            test_texts, test_labels, classifier
        )
    else:
        logger.warning("No classifier available - skipping classifier evaluation")
        classifier_predictions, classifier_latencies = [], []

    # Calculate metrics
    results = {
        "test_size": len(test_texts),
        "llm_only": _calculate_metrics(test_labels, llm_predictions, llm_latencies),
    }

    if classifier_predictions:
        results["with_classifier"] = _calculate_metrics(test_labels, classifier_predictions, classifier_latencies)
        results["comparison"] = _compare_modes(results["llm_only"], results["with_classifier"])

    # Generate visualizations
    confusion_matrix_html = None
    if classifier_predictions:
        confusion_matrix_html = _create_comparison_plots(test_labels, llm_predictions, classifier_predictions)

    # Log comprehensive metadata
    log_metadata(
        metadata={
            "evaluation_summary": {
                "test_samples": len(test_texts),
                "modes_evaluated": "LLM + With Classifier" if classifier_predictions else "LLM only",
                "llm_accuracy": results["llm_only"]["accuracy"],
                "classifier_accuracy": results["with_classifier"]["accuracy"] if "with_classifier" in results else None,
            },
            "performance_comparison": results.get("comparison", {}),
            "latency_analysis": {
                "llm_avg_latency": results["llm_only"]["avg_latency_ms"],
                "classifier_avg_latency": results["with_classifier"]["avg_latency_ms"] if "with_classifier" in results else None,
                "speedup_factor": results["comparison"]["latency_improvement"] if "comparison" in results else None,
            }
        }
    )

    # Return both results and HTML visualization as separate artifacts
    html_output = HTMLString(confusion_matrix_html if confusion_matrix_html else "No classifier evaluation performed - only LLM mode was evaluated")

    return results, html_output


def _load_production_classifier():
    """Load the production-tagged classifier from the artifact store."""
    try:
        client = Client()
        # Find the intent-classifier artifact with production tag
        artifacts = client.list_artifact_versions(name="intent-classifier", tags=["production"])
        if not artifacts.items:
            logger.warning("No production-tagged classifier found")
            return None

        # Get the latest production artifact
        latest_artifact = artifacts.items[0]  # Already sorted by created time desc
        classifier = latest_artifact.load()
        logger.info(f"Loaded production classifier: {latest_artifact.id}")
        return classifier

    except Exception as e:
        logger.error(f"Failed to load production classifier: {e}")
        return None


def _evaluate_llm_mode(test_texts: List[str], test_labels: List[str]) -> Tuple[List[str], List[float]]:
    """Evaluate LLM-only mode performance (generic responses, no intent classification)."""
    predictions = []
    latencies = []

    for text in test_texts:
        start_time = time.time()
        result = call_llm_generic_response(text)  # Use generic response instead of intent classification
        end_time = time.time()

        predictions.append(result["intent"])  # Will always be "general"
        latencies.append((end_time - start_time) * 1000)  # Convert to milliseconds

    return predictions, latencies


def _evaluate_with_classifier_mode(
    test_texts: List[str], test_labels: List[str], classifier
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
        latencies.append((end_time - start_time) * 1000)  # Convert to milliseconds

    return predictions, latencies


def _calculate_metrics(labels: List[str], predictions: List[str], latencies: List[float]) -> Dict:
    """Calculate performance metrics."""
    return {
        "accuracy": round(accuracy_score(labels, predictions), 3),
        "f1_score": round(f1_score(labels, predictions, average="weighted"), 3),
        "avg_latency_ms": round(np.mean(latencies), 2),
        "p95_latency_ms": round(np.percentile(latencies, 95), 2),
        "total_predictions": len(predictions),
        "classification_report": classification_report(labels, predictions, output_dict=True),
    }


def _compare_modes(llm_results: Dict, classifier_results: Dict) -> Dict:
    """Compare LLM-only and With Intent Classifier mode performance."""
    return {
        "accuracy_improvement": round(classifier_results["accuracy"] - llm_results["accuracy"], 3),
        "f1_improvement": round(classifier_results["f1_score"] - llm_results["f1_score"], 3),
        "latency_improvement": round(
            (llm_results["avg_latency_ms"] - classifier_results["avg_latency_ms"])
            / llm_results["avg_latency_ms"], 3
        ),
        "speedup_factor": round(llm_results["avg_latency_ms"] / classifier_results["avg_latency_ms"], 1),
    }


def _create_comparison_plots(labels: List[str], llm_preds: List[str], classifier_preds: List[str]) -> str:
    """Create modern, interactive-style confusion matrices with ZenML branding."""

    # Get unique labels for consistent ordering
    unique_labels = sorted(list(set(labels)))

    # Create confusion matrices
    llm_cm = confusion_matrix(labels, llm_preds, labels=unique_labels)
    classifier_cm = confusion_matrix(labels, classifier_preds, labels=unique_labels)

    # Calculate performance metrics for display
    llm_accuracy = accuracy_score(labels, llm_preds)
    classifier_accuracy = accuracy_score(labels, classifier_preds)
    llm_f1 = f1_score(labels, llm_preds, average='weighted')
    classifier_f1 = f1_score(labels, classifier_preds, average='weighted')

    # Determine which is better
    accuracy_winner = "With Classifier" if classifier_accuracy > llm_accuracy else "LLM-only" if llm_accuracy > classifier_accuracy else "Tie"
    f1_winner = "With Classifier" if classifier_f1 > llm_f1 else "LLM-only" if llm_f1 > classifier_f1 else "Tie"

    # ZenML color palette - modern purple/blue gradient
    zenml_colors = ['#f8faff', '#e1e7ff', '#c7d2fe', '#a5b4fc', '#8b5cf6', '#7c3aed', '#6d28d9']

    # Set modern style
    plt.style.use('default')

    # Create figure with better layout and modern styling
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor('#ffffff')

    # Modern LLM confusion matrix with ZenML colors
    sns.heatmap(
        llm_cm,
        annot=True,
        fmt='d',
        cmap=sns.light_palette('#8b5cf6', as_cmap=True),
        xticklabels=unique_labels,
        yticklabels=unique_labels,
        ax=ax1,
        cbar_kws={'shrink': 0.8},
        square=True,
        linewidths=0.5,
        linecolor='white',
        annot_kws={'size': 12, 'weight': 'bold'}
    )
    ax1.set_title('LLM-Only Mode', fontsize=16, fontweight='bold', color='#374151', pad=20)
    ax1.set_xlabel('Predicted Intent', fontsize=12, fontweight='600', color='#6b7280')
    ax1.set_ylabel('True Intent', fontsize=12, fontweight='600', color='#6b7280')
    ax1.tick_params(axis='both', which='major', labelsize=10)

    # Modern With Intent Classifier confusion matrix with complementary ZenML colors
    sns.heatmap(
        classifier_cm,
        annot=True,
        fmt='d',
        cmap=sns.light_palette('#10b981', as_cmap=True),  # ZenML green accent
        xticklabels=unique_labels,
        yticklabels=unique_labels,
        ax=ax2,
        cbar_kws={'shrink': 0.8},
        square=True,
        linewidths=0.5,
        linecolor='white',
        annot_kws={'size': 12, 'weight': 'bold'}
    )
    ax2.set_title('With Intent Classifier', fontsize=16, fontweight='bold', color='#374151', pad=20)
    ax2.set_xlabel('Predicted Intent', fontsize=12, fontweight='600', color='#6b7280')
    ax2.set_ylabel('True Intent', fontsize=12, fontweight='600', color='#6b7280')
    ax2.tick_params(axis='both', which='major', labelsize=10)

    # Improve overall layout
    plt.tight_layout(pad=3.0)

    # Convert plot to high-quality base64 image
    img_buffer = io.BytesIO()
    plt.savefig(
        img_buffer,
        format='png',
        dpi=200,
        bbox_inches='tight',
        facecolor='white',
        edgecolor='none',
        pad_inches=0.2
    )
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()

    # Create modern HTML with ZenML styling
    html_content = f"""
    <div style="
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #f8faff 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 32px;
        margin: 20px 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    ">
        <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="
                color: #1e293b;
                font-size: 24px;
                font-weight: 700;
                margin: 0 0 8px 0;
                background: linear-gradient(135deg, #8b5cf6, #06b6d4);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">
                🤖 Agent Performance Comparison
            </h2>
            <p style="
                color: #64748b;
                font-size: 14px;
                margin: 0;
                font-weight: 500;
            ">
                Confusion Matrices: Model Prediction Accuracy Analysis
            </p>
        </div>

        <div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}"
                 style="
                     max-width: 100%;
                     height: auto;
                     border-radius: 8px;
                     box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                 "
                 alt="Agent Performance Comparison - Confusion Matrices" />
        </div>

        <!-- Performance Comparison Section -->
        <div style="
            background: linear-gradient(135deg, #fefbff 0%, #f0f9ff 100%);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid #e0e7ff;
        ">
            <h3 style="
                color: #1e293b;
                font-size: 18px;
                font-weight: 700;
                margin: 0 0 16px 0;
                text-align: center;
            ">
                📊 Performance Metrics Comparison
            </h3>

            <div style="display: flex; justify-content: space-around; gap: 20px; flex-wrap: wrap;">
                <!-- Accuracy Comparison -->
                <div style="flex: 1; min-width: 250px;">
                    <h4 style="color: #374151; font-size: 14px; font-weight: 600; margin: 0 0 12px 0; text-align: center;">
                        🎯 Accuracy {'🏆 ' + accuracy_winner if accuracy_winner != 'Tie' else '🤝 Tie'}
                    </h4>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 12px; font-weight: 500; color: #6b7280; min-width: 60px;">LLM-Only:</span>
                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; position: relative;">
                            <div style="
                                background: {'linear-gradient(135deg, #059669, #10b981)' if accuracy_winner == 'LLM-only' else 'linear-gradient(135deg, #8b5cf6, #7c3aed)'};
                                height: 100%;
                                border-radius: 4px;
                                width: {llm_accuracy * 100}%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                color: white;
                                font-size: 11px;
                                font-weight: 600;
                            ">
                                {llm_accuracy:.1%}
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 12px; font-weight: 500; color: #6b7280; min-width: 60px;">Classifier:</span>
                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; position: relative;">
                            <div style="
                                background: {'linear-gradient(135deg, #059669, #10b981)' if accuracy_winner == 'With Classifier' else 'linear-gradient(135deg, #8b5cf6, #7c3aed)'};
                                height: 100%;
                                border-radius: 4px;
                                width: {classifier_accuracy * 100}%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                color: white;
                                font-size: 11px;
                                font-weight: 600;
                            ">
                                {classifier_accuracy:.1%}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- F1 Score Comparison -->
                <div style="flex: 1; min-width: 250px;">
                    <h4 style="color: #374151; font-size: 14px; font-weight: 600; margin: 0 0 12px 0; text-align: center;">
                        ⚖️ F1 Score {'🏆 ' + f1_winner if f1_winner != 'Tie' else '🤝 Tie'}
                    </h4>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 12px; font-weight: 500; color: #6b7280; min-width: 60px;">LLM-Only:</span>
                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; position: relative;">
                            <div style="
                                background: {'linear-gradient(135deg, #059669, #10b981)' if f1_winner == 'LLM-only' else 'linear-gradient(135deg, #8b5cf6, #7c3aed)'};
                                height: 100%;
                                border-radius: 4px;
                                width: {llm_f1 * 100}%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                color: white;
                                font-size: 11px;
                                font-weight: 600;
                            ">
                                {llm_f1:.3f}
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 12px; font-weight: 500; color: #6b7280; min-width: 60px;">Classifier:</span>
                        <div style="flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; position: relative;">
                            <div style="
                                background: {'linear-gradient(135deg, #059669, #10b981)' if f1_winner == 'With Classifier' else 'linear-gradient(135deg, #8b5cf6, #7c3aed)'};
                                height: 100%;
                                border-radius: 4px;
                                width: {classifier_f1 * 100}%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                color: white;
                                font-size: 11px;
                                font-weight: 600;
                            ">
                                {classifier_f1:.3f}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Overall Winner -->
            <div style="
                margin-top: 16px;
                padding: 12px;
                background: {'linear-gradient(135deg, #dcfdf7, #a7f3d0)' if (accuracy_winner == 'With Classifier' and f1_winner == 'With Classifier') or (accuracy_winner == 'With Classifier' and f1_winner == 'Tie') or (f1_winner == 'With Classifier' and accuracy_winner == 'Tie') else 'linear-gradient(135deg, #ede9fe, #c4b5fd)' if (accuracy_winner == 'LLM-only' and f1_winner == 'LLM-only') or (accuracy_winner == 'LLM-only' and f1_winner == 'Tie') or (f1_winner == 'LLM-only' and accuracy_winner == 'Tie') else 'linear-gradient(135deg, #fef3c7, #fde68a)'};
                border-radius: 6px;
                text-align: center;
                border: 1px solid {'#10b981' if (accuracy_winner == 'With Classifier' and f1_winner == 'With Classifier') or (accuracy_winner == 'With Classifier' and f1_winner == 'Tie') or (f1_winner == 'With Classifier' and accuracy_winner == 'Tie') else '#8b5cf6' if (accuracy_winner == 'LLM-only' and f1_winner == 'LLM-only') or (accuracy_winner == 'LLM-only' and f1_winner == 'Tie') or (f1_winner == 'LLM-only' and accuracy_winner == 'Tie') else '#f59e0b'};
            ">
                <p style="
                    color: {'#065f46' if (accuracy_winner == 'With Classifier' and f1_winner == 'With Classifier') or (accuracy_winner == 'With Classifier' and f1_winner == 'Tie') or (f1_winner == 'With Classifier' and accuracy_winner == 'Tie') else '#581c87' if (accuracy_winner == 'LLM-only' and f1_winner == 'LLM-only') or (accuracy_winner == 'LLM-only' and f1_winner == 'Tie') or (f1_winner == 'LLM-only' and accuracy_winner == 'Tie') else '#92400e'};
                    font-size: 13px;
                    margin: 0;
                    font-weight: 600;
                ">
                    {'🎉 With Intent Classifier wins overall! Better structured responses and targeted support.' if (accuracy_winner == 'With Classifier' and f1_winner == 'With Classifier') or (accuracy_winner == 'With Classifier' and f1_winner == 'Tie') or (f1_winner == 'With Classifier' and accuracy_winner == 'Tie') else '🎯 LLM-Only Mode wins overall! Generic responses work better for this dataset.' if (accuracy_winner == 'LLM-only' and f1_winner == 'LLM-only') or (accuracy_winner == 'LLM-only' and f1_winner == 'Tie') or (f1_winner == 'LLM-only' and accuracy_winner == 'Tie') else '🤝 Mixed results - approaches have different strengths. Check detailed metrics.'}
                </p>
            </div>
        </div>

        <div style="
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 16px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        ">
            <div style="text-align: center; flex: 1; min-width: 200px;">
                <div style="
                    background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 13px;
                    margin-bottom: 8px;
                ">
                    LLM-Only Mode
                </div>
                <p style="color: #64748b; font-size: 12px; margin: 0; line-height: 1.4;">
                    Generic banking responses<br/>
                    No intent classification, general advice
                </p>
            </div>

            <div style="text-align: center; flex: 1; min-width: 200px;">
                <div style="
                    background: linear-gradient(135deg, #10b981, #059669);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 13px;
                    margin-bottom: 8px;
                ">
                    With Intent Classifier
                </div>
                <p style="color: #64748b; font-size: 12px; margin: 0; line-height: 1.4;">
                    Structured responses by intent<br/>
                    Targeted support, domain-specific help
                </p>
            </div>
        </div>

        <div style="
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 6px;
            padding: 12px;
            margin-top: 16px;
            text-align: center;
        ">
            <p style="
                color: #92400e;
                font-size: 12px;
                margin: 0;
                font-weight: 500;
            ">
                💡 <strong>Interpretation:</strong> Darker colors indicate higher prediction counts.
                Diagonal values represent correct predictions.
            </p>
        </div>
    </div>
    """

    logger.info("Generated modern confusion matrix visualization with ZenML styling")
    return html_content


@step
def generate_test_dataset() -> Tuple[
    Annotated[List[str], "test_texts"],
    Annotated[List[str], "test_labels"]
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