"""Training step for intent classifier."""

from typing import Annotated, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from zenml import ArtifactConfig, add_tags, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def train_classifier_step(
    texts: List[str], labels: List[str]
) -> Annotated[
    Pipeline, ArtifactConfig(name="intent-classifier", tags=["demo"])
]:
    """Train a classifier and tag THIS artifact version as 'production'."""
    logger.info(f"Training classifier on {len(texts)} examples...")

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.3, random_state=42, stratify=labels
    )

    # Create and train pipeline
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(max_features=1000, stop_words="english"),
            ),
            ("classifier", LogisticRegression(random_state=42, max_iter=1000)),
        ]
    )

    pipeline.fit(X_train, y_train)

    # Evaluate
    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    logger.info("Training completed!")
    logger.info(f"Accuracy on test set: {accuracy:.3f}")
    logger.info("Classification Report:")
    logger.info(f"\n{classification_report(y_test, y_pred)}")

    # Tag the artifact version produced by THIS step as 'production'
    add_tags(tags=["production"], infer_artifact=True)
    logger.info("Tagged artifact version as 'production'")

    return pipeline
