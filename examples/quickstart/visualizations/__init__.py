"""Visualization utilities for the ZenML quickstart."""

import os
from typing import Dict, Any


def load_template(template_name: str) -> str:
    """Load HTML template from the visualizations folder."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, template_name)

    with open(template_path, 'r') as f:
        return f.read()


def load_css(css_name: str) -> str:
    """Load CSS file from the visualizations folder."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, css_name)

    with open(css_path, 'r') as f:
        return f.read()


def render_evaluation_template(
    img_base64: str,
    llm_accuracy: float,
    classifier_accuracy: float,
    llm_f1: float,
    classifier_f1: float,
    accuracy_winner: str,
    f1_winner: str
) -> str:
    """Render the evaluation template with performance data."""

    # Load template and CSS
    template = load_template("evaluation_template.html")
    css_styles = load_css("styles.css")

    # Determine winner classes and messages
    def get_winner_info():
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

    winner_class, winner_text_class, winner_message = get_winner_info()

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