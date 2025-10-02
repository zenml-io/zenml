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

"""Training step for intent classifier."""

from typing import Annotated, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from zenml import ArtifactConfig, add_tags, log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def train_classifier_step(
    texts: List[str], labels: List[str]
) -> Annotated[
    Pipeline, ArtifactConfig(name="intent-classifier", tags=["demo"])
]:
    """Train a classifier and tag THIS artifact version as 'production'.

    Args:
        texts: List of text samples for training.
        labels: List of corresponding labels for the text samples.

    Returns:
        Trained sklearn pipeline with TF-IDF vectorizer and LogisticRegression.
    """
    logger.info(f"Training classifier on {len(texts)} examples...")

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.3, random_state=42, stratify=labels
    )

    # Use TF-IDF vectorizer for simple, reliable intent classification
    logger.info("Using TF-IDF vectorization for intent classification")
    vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
    pipeline_name = "tfidf"

    # Create and train pipeline
    pipeline = Pipeline(
        [
            ("vectorizer", vectorizer),
            ("classifier", LogisticRegression(random_state=42, max_iter=1000)),
        ]
    )

    logger.info("Fitting pipeline...")
    pipeline.fit(X_train, y_train)

    # Evaluate
    logger.info("Evaluating model...")
    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    logger.info("Training completed!")
    logger.info(f"Vectorizer: {pipeline_name}")
    logger.info(f"Accuracy on test set: {accuracy:.3f}")
    logger.info("Classification Report:")
    logger.info(f"\n{classification_report(y_test, y_pred, zero_division=0)}")

    # Log training metadata to artifact
    intent_counts = {intent: labels.count(intent) for intent in set(labels)}
    log_metadata(
        metadata={
            "training_metrics": {
                "accuracy": round(accuracy, 3),
                "samples": len(texts),
                "intent_classes": len(set(labels)),
            },
            "model_config": {
                "vectorizer": pipeline_name,
                "classifier": "LogisticRegression",
                "intent_distribution": intent_counts,
            },
        },
        infer_artifact=True,  # Log to the output artifact
    )

    # Tag the artifact version produced by THIS step as 'production'
    add_tags(tags=["production"], infer_artifact=True)
    logger.info("Tagged artifact version as 'production'")

    return pipeline
