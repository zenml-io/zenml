#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Customer activity loading, feature preparation, and conversion scoring."""

import csv
import io
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.tree import DecisionTreeClassifier

from zenml import log_metadata, step
from zenml.client import Client


def _read_customer_csv(source_uri: str) -> str:
    """Read CSV text from a local file, HTTP endpoint, or artifact store.

    Args:
        source_uri: Location of the customer CSV without embedded credentials.

    Returns:
        Decoded CSV text.

    Raises:
        ValueError: If the URI contains credentials or the source cannot be read.
    """
    location = urlsplit(source_uri)
    if (
        location.username
        or location.password
        or location.query
        or location.fragment
    ):
        raise ValueError(
            "Source URIs must not contain credentials, queries, or fragments."
        )
    if location.scheme == "file" and location.netloc not in {"", "localhost"}:
        raise ValueError("File URIs must refer to the local host.")
    try:
        if location.scheme in {"http", "https"}:
            with urlopen(source_uri, timeout=30) as response:
                content = response.read()
        elif location.scheme in {"", "file"}:
            path = unquote(location.path) if location.scheme else source_uri
            content = Path(path).expanduser().read_bytes()
        else:
            with Client().active_stack.artifact_store.open(
                source_uri, "rb"
            ) as source:
                content = source.read()
        return content.decode("utf-8-sig")
    except Exception:
        raise ValueError("Unable to read the customer data source.") from None


@step(enable_cache=False)
def load_customer_data(
    source_uri: str,
) -> Annotated[list[dict[str, str]], "customer_records"]:
    """Read the current customer activity feed.

    Args:
        source_uri: Location of the customer CSV.

    Returns:
        The incoming rows with their original column names and values.

    Raises:
        ValueError: If the CSV is empty or has incomplete rows.
    """
    reader = csv.DictReader(io.StringIO(_read_customer_csv(source_uri)))
    rows = list(reader)
    if not reader.fieldnames or not rows:
        raise ValueError(
            "Customer data must contain a header and at least one row."
        )
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("Customer data contains incomplete CSV rows.")
    log_metadata(
        metadata={
            "row_count": len(rows),
            "column_count": len(reader.fieldnames),
        }
    )
    return rows


@step
def prepare_customer_features(
    raw_rows: list[dict[str, str]],
) -> Annotated[list[dict[str, float]], "customer_features"]:
    """Convert customer activity into numerical model features.

    Args:
        raw_rows: Customer activity records.

    Returns:
        Numerical basket values and account ages in input row order.
    """
    features = []
    for row in raw_rows:
        basket_value = row.get("basket_value_eur", row.get("basket_value"))
        if basket_value is None:
            raise ValueError(
                "Customer data must contain basket_value or basket_value_eur."
            )
        features.append(
            {
                "basket_value": float(basket_value),
                "account_length": float(row["account_length"]),
            }
        )
    log_metadata(
        metadata={
            "row_count": len(features),
            "basket_value_mean": sum(row["basket_value"] for row in features)
            / len(features),
            "account_length_mean": sum(
                row["account_length"] for row in features
            )
            / len(features),
        }
    )
    return features


@step
def train_customer_model() -> Annotated[
    DecisionTreeClassifier, "customer_model"
]:
    """Fit a compact conversion classifier on synthetic customer observations.

    Returns:
        A fitted conversion classifier.
    """
    observations = [
        [float(basket_value), float(account_length)]
        for basket_value in range(20, 201, 20)
        for account_length in range(6, 55, 12)
    ]
    outcomes = [int(row[0] >= 100) for row in observations]
    model = DecisionTreeClassifier(max_depth=2, random_state=42)
    model.fit(observations, outcomes)
    log_metadata(
        metadata={
            "training_rows": len(observations),
            "training_accuracy": float(model.score(observations, outcomes)),
        }
    )
    return model


@step
def score_customers(
    model: DecisionTreeClassifier,
    features: list[dict[str, float]],
    raw_rows: list[dict[str, str]],
) -> Annotated[list[dict[str, str | int | float]], "customer_predictions"]:
    """Predict conversion for each customer activity record.

    Args:
        model: Fitted conversion classifier.
        features: Numerical features in input row order.
        raw_rows: Customer identifiers and observed conversion labels.

    Returns:
        Customer identifiers, labels, predicted classes, and probabilities.
    """
    matrix = [[row["basket_value"], row["account_length"]] for row in features]
    labels = model.predict(matrix)
    probabilities = model.predict_proba(matrix)[:, 1]
    predictions = [
        {
            "customer_id": row["customer_id"],
            "converted": int(row["converted"]),
            "prediction": int(label),
            "conversion_probability": float(probability),
        }
        for row, label, probability in zip(
            raw_rows, labels, probabilities, strict=True
        )
    ]
    log_metadata(
        metadata={
            "row_count": len(predictions),
            "predicted_positive_count": int(sum(labels)),
            "mean_conversion_probability": float(probabilities.mean()),
        }
    )
    return predictions


@step
def evaluate_scores(
    predictions: list[dict[str, str | int | float]],
) -> Annotated[dict[str, float], "scoring_metrics"]:
    """Calculate classification metrics against observed conversions.

    Args:
        predictions: Predictions and observed conversion labels.

    Returns:
        Accuracy, precision, recall, and F1 score.
    """
    expected = [int(row["converted"]) for row in predictions]
    predicted = [int(row["prediction"]) for row in predictions]
    metrics = {
        "accuracy": float(accuracy_score(expected, predicted)),
        "precision": float(
            precision_score(expected, predicted, zero_division=0)
        ),
        "recall": float(recall_score(expected, predicted, zero_division=0)),
        "f1": float(f1_score(expected, predicted, zero_division=0)),
    }
    log_metadata(metadata={"row_count": len(predictions), **metrics})
    return metrics
