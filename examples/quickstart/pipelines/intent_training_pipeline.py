"""Intent classification training pipeline."""

import os
from typing import Any

from steps.data import load_toy_intent_data
from steps.train import train_classifier_step

from zenml import pipeline
from zenml.config import DockerSettings


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            parent_image="zenmldocker/zenml:0.85.0-py3.12",
            environment={
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            },
        )
    },
)
def intent_training_pipeline() -> Any:
    """Train intent classifier and tag as production."""
    texts, labels = load_toy_intent_data()
    classifier = train_classifier_step(texts, labels)
    return classifier
