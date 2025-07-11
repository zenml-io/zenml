"""Model training steps for the agent comparison pipeline."""

import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline as SklearnPipeline
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def train_intent_classifier(
    queries: pd.DataFrame,
) -> Annotated[BaseEstimator, "intent_classifier_model"]:
    """Train a simple intent classifier on customer service queries.

    Args:
        queries: DataFrame containing customer service queries with 'query_text' column

    Returns:
        Trained scikit-learn pipeline (TF-IDF + LogisticRegression) for intent classification
    """
    # Create training data with labels based on keywords
    training_texts = []
    training_labels = []

    for _, row in queries.iterrows():
        query = row["query_text"].lower()

        # Simple rule-based labeling for training
        if any(word in query for word in ["return", "exchange", "refund"]):
            label = "returns"
        elif any(
            word in query for word in ["payment", "billing", "charge", "price"]
        ):
            label = "billing"
        elif any(word in query for word in ["shipping", "delivery", "ship"]):
            label = "shipping"
        elif any(
            word in query for word in ["warranty", "guarantee", "broken"]
        ):
            label = "warranty"
        else:
            label = "general"

        training_texts.append(row["query_text"])
        training_labels.append(label)

    # Train a simple classifier
    classifier = SklearnPipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=100, stop_words="english")),
            ("clf", LogisticRegression(random_state=42)),
        ]
    )

    classifier.fit(training_texts, training_labels)

    logger.info(f"Trained intent classifier on {len(training_texts)} queries")
    return classifier
