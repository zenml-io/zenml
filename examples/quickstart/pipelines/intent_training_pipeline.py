"""Intent classification training pipeline."""

from typing import Any

from steps.data import load_toy_intent_data
from steps.train import train_classifier_step

from zenml import pipeline


@pipeline
def intent_training_pipeline() -> Any:
    """Train intent classifier and tag as production."""
    texts, labels = load_toy_intent_data()
    classifier = train_classifier_step(texts, labels)
    return classifier
