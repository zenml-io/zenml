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

"""Visualization utilities for the ZenML quickstart."""

import base64
import io
import os
from typing import List, Tuple

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from zenml.logger import get_logger

logger = get_logger(__name__)


def load_template(template_name: str) -> str:
    """Load HTML template from the visualizations folder.

    Args:
        template_name: Name of the template file to load.

    Returns:
        Content of the template file as a string.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, template_name)

    with open(template_path, 'r') as f:
        return f.read()


def load_css(css_name: str) -> str:
    """Load CSS file from the visualizations folder.

    Args:
        css_name: Name of the CSS file to load.

    Returns:
        Content of the CSS file as a string.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, css_name)

    with open(css_path, 'r') as f:
        return f.read()


def get_winner_info(accuracy_winner: str, f1_winner: str) -> Tuple[str, str, str]:
    """Determine winner classes and messages based on metric comparisons.

    Args:
        accuracy_winner: Winner for accuracy metric ('With Classifier', 'LLM-only', or 'Tie').
        f1_winner: Winner for F1 metric ('With Classifier', 'LLM-only', or 'Tie').

    Returns:
        Tuple of (winner_class, winner_text_class, winner_message) for styling and display.
    """
    if (accuracy_winner == 'With Classifier' and f1_winner == 'With Classifier') or \
       (accuracy_winner == 'With Classifier' and f1_winner == 'Tie') or \
       (f1_winner == 'With Classifier' and accuracy_winner == 'Tie'):
        return "classifier-wins", "classifier-wins", "🎉 With Intent Classifier wins overall! Better structured responses and targeted support."
    elif (accuracy_winner == 'LLM-only' and f1_winner == 'LLM-only') or \
         (accuracy_winner == 'LLM-only' and f1_winner == 'Tie') or \
         (f1_winner == 'LLM-only' and accuracy_winner == 'Tie'):
        return "llm-wins", "llm-wins", "🎯 LLM-Only Mode wins overall! Generic responses work better for this dataset."
    else:
        return "mixed", "mixed", "🤝 Mixed results - approaches have different strengths. Check detailed metrics."


def render_evaluation_template(
    img_base64: str,
    llm_accuracy: float,
    classifier_accuracy: float,
    llm_f1: float,
    classifier_f1: float,
    accuracy_winner: str,
    f1_winner: str
) -> str:
    """Render the evaluation template with performance data.

    Args:
        img_base64: Base64-encoded image data for confusion matrices.
        llm_accuracy: Accuracy score for LLM-only mode.
        classifier_accuracy: Accuracy score for classifier mode.
        llm_f1: F1 score for LLM-only mode.
        classifier_f1: F1 score for classifier mode.
        accuracy_winner: Winner for accuracy metric.
        f1_winner: Winner for F1 metric.

    Returns:
        Rendered HTML template as a string.
    """

    # Load template and CSS
    template = load_template("evaluation_template.html")
    css_styles = load_css("styles.css")

    # Determine winner classes and messages
    winner_class, winner_text_class, winner_message = get_winner_info(accuracy_winner, f1_winner)

    # Prepare template variables
    template_vars = {
        'css_styles': css_styles,
        'img_base64': img_base64,
        'accuracy_winner_badge': f'🏆 {accuracy_winner}' if accuracy_winner != 'Tie' else '🤝 Tie',
        'f1_winner_badge': f'🏆 {f1_winner}' if f1_winner != 'Tie' else '🤝 Tie',
        'llm_accuracy_percent': llm_accuracy * 100,
        'classifier_accuracy_percent': classifier_accuracy * 100,
        'llm_f1_percent': llm_f1 * 100,
        'classifier_f1_percent': classifier_f1 * 100,
        'llm_accuracy_display': f'{llm_accuracy:.1%}',
        'classifier_accuracy_display': f'{classifier_accuracy:.1%}',
        'llm_f1_display': f'{llm_f1:.3f}',
        'classifier_f1_display': f'{classifier_f1:.3f}',
        'llm_accuracy_class': 'winner' if accuracy_winner == 'LLM-only' else 'loser',
        'classifier_accuracy_class': 'winner' if accuracy_winner == 'With Classifier' else 'loser',
        'llm_f1_class': 'winner' if f1_winner == 'LLM-only' else 'loser',
        'classifier_f1_class': 'winner' if f1_winner == 'With Classifier' else 'loser',
        'winner_class': winner_class,
        'winner_text_class': winner_text_class,
        'winner_message': winner_message
    }

    # Render template
    return template.format(**template_vars)


def create_comparison_plots(
    labels: List[str], llm_preds: List[str], classifier_preds: List[str]
) -> str:
    """Create modern, interactive-style confusion matrices with ZenML branding.

    Args:
        labels: List of ground truth labels.
        llm_preds: List of predictions from LLM-only mode.
        classifier_preds: List of predictions from classifier mode.

    Returns:
        Base64-encoded HTML string containing the confusion matrix plots.
    """
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
