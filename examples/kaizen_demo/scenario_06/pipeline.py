# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Train and evaluate a customer segment classifier."""

from typing import Annotated

from build_settings import create_docker_settings
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from zenml import ArtifactConfig, log_metadata, pipeline, step
from zenml.config import ResourceSettings
from zenml.enums import StepRuntime
from zenml.types import HTMLString


@step(runtime=StepRuntime.ISOLATED, enable_cache=False)
def train_customer_segment_model(
    sample_count: int, random_seed: int, cpu_count: int
) -> tuple[
    Annotated[
        RandomForestClassifier, ArtifactConfig(name="customer_segment_model")
    ],
    Annotated[HTMLString, "customer_segment_evaluation"],
    Annotated[dict[str, float], "customer_segment_metrics"],
]:
    """Fit a classifier and evaluate it on a held-out customer sample.

    Args:
        sample_count: Number of synthetic customer observations.
        random_seed: Seed for data generation, splitting, and model fitting.
        cpu_count: Number of workers available for fitting the forest.

    Returns:
        The fitted model, an HTML evaluation report, and classification metrics.

    Raises:
        ValueError: If the sample is too small or the worker count is invalid.
    """
    if sample_count < 160:
        raise ValueError("At least 160 customer observations are required.")
    if cpu_count < 1:
        raise ValueError("cpu_count must be positive.")

    features, labels = make_classification(
        n_samples=sample_count,
        n_features=6,
        n_informative=4,
        n_redundant=1,
        class_sep=1.2,
        random_state=random_seed,
    )
    train_features, test_features, train_labels, test_labels = (
        train_test_split(
            features,
            labels,
            test_size=0.25,
            stratify=labels,
            random_state=random_seed,
        )
    )
    model = RandomForestClassifier(
        n_estimators=48,
        max_depth=6,
        min_samples_leaf=2,
        n_jobs=cpu_count,
        random_state=random_seed,
    )
    model.fit(train_features, train_labels)
    predictions = model.predict(test_features)
    probabilities = model.predict_proba(test_features)[:, 1]
    metrics = {
        "accuracy": float(accuracy_score(test_labels, predictions)),
        "precision": float(
            precision_score(test_labels, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(test_labels, predictions, zero_division=0)
        ),
        "f1": float(f1_score(test_labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(test_labels, probabilities)),
    }
    matrix = confusion_matrix(test_labels, predictions, labels=[0, 1])
    metric_rows = "".join(
        f"<tr><th>{name.replace('_', ' ').upper()}</th><td>{value:.3f}</td></tr>"
        for name, value in metrics.items()
    )
    report = HTMLString(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Customer segment evaluation</title>
<style>
body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 760px;
        margin: 32px auto; padding: 0 24px; color: #17212b; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; }}
th, td {{ padding: 10px 14px; border-bottom: 1px solid #dce3e8;
          text-align: left; }}
thead, th {{ background: #f2f6f8; }}
</style>
</head>
<body>
<h1>Customer segment evaluation</h1>
<p>A random forest classifies two customer segments using six synthetic
features. Evaluation uses a stratified holdout that was excluded from fitting.</p>
<p>Training observations: <strong>{len(train_labels)}</strong>.
Held-out observations: <strong>{len(test_labels)}</strong>.</p>
<h2>Held-out metrics</h2>
<table><thead><tr><th>Metric</th><th>Score</th></tr></thead>
<tbody>{metric_rows}</tbody></table>
<h2>Confusion matrix</h2>
<table><thead><tr><th>Observed segment</th><th>Predicted 0</th>
<th>Predicted 1</th></tr></thead><tbody>
<tr><th>Segment 0</th><td>{matrix[0, 0]}</td><td>{matrix[0, 1]}</td></tr>
<tr><th>Segment 1</th><td>{matrix[1, 0]}</td><td>{matrix[1, 1]}</td></tr>
</tbody></table>
</body>
</html>"""
    )
    log_metadata(
        {
            "training_rows": len(train_labels),
            "evaluation_rows": len(test_labels),
            **metrics,
        }
    )
    return model, report, metrics


@pipeline(
    dynamic=True,
    settings={"docker": create_docker_settings()},
)
def customer_segment_training(
    cpu_count: int = 4, sample_count: int = 480, random_seed: int = 29
) -> None:
    """Train a customer segment model with configured compute resources.

    Args:
        cpu_count: CPU cores to request for model training.
        sample_count: Number of synthetic customer observations.
        random_seed: Seed for reproducible training and evaluation.
    """
    train_customer_segment_model.with_options(
        settings={
            "resources": ResourceSettings(
                cpu_count=cpu_count,
                memory="1GiB",
                preemptible=False,
            )
        },
        parameters={
            "sample_count": sample_count,
            "random_seed": random_seed,
            "cpu_count": cpu_count,
        },
    )()
