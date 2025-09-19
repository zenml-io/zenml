"""Training step for intent classifier."""

from typing import Annotated, List

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from zenml import ArtifactConfig, add_tags, log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)

# Try to import sentence transformers, fall back to TF-IDF if not available
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    from sklearn.feature_extraction.text import TfidfVectorizer


class SentenceTransformerVectorizer:
    """Custom vectorizer using sentence transformers."""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None

    def fit(self, X, y=None):
        """Initialize the sentence transformer model."""
        self.model = SentenceTransformer(self.model_name)
        return self

    def transform(self, X):
        """Transform texts to embeddings."""
        if self.model is None:
            raise ValueError("Vectorizer not fitted")
        return self.model.encode(X)

    def fit_transform(self, X, y=None):
        """Fit and transform in one step."""
        return self.fit(X, y).transform(X)


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

    # Choose vectorizer based on availability
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        logger.info(
            "Using SentenceTransformers for embeddings (modern approach)"
        )
        vectorizer = SentenceTransformerVectorizer()
        pipeline_name = "sentence-transformer"
    else:
        logger.info(
            "SentenceTransformers not available, falling back to TF-IDF"
        )
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
    logger.info(f"\n{classification_report(y_test, y_pred)}")

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
