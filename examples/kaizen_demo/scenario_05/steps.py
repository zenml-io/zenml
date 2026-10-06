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

"""Customer classifier training and evaluation with explicit run provenance."""

from html import escape
from typing import Annotated
from uuid import UUID

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from zenml import get_step_context, log_metadata, step
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunResponse
from zenml.types import HTMLString
from zenml.utils.trigger_utils import get_upstream_run

FEATURE_COLUMNS = ["monthly_spend", "account_months", "support_requests"]
TARGET_COLUMN = "needs_follow_up"
TRAINING_PIPELINE = "customer_model_training"


@step
def fit_customer_model(
    sample_count: int, random_seed: int
) -> tuple[
    Annotated[Pipeline, "customer_classifier"],
    Annotated[pd.DataFrame, "customer_holdout"],
]:
    """Train a customer classifier without using its held-out observations.

    Args:
        sample_count: Number of synthetic customer observations.
        random_seed: Seed for data generation and the stratified split.

    Returns:
        The fitted classifier and a held-out dataset with observed labels.

    Raises:
        ValueError: If fewer than 120 observations are requested.
    """
    if sample_count < 120:
        raise ValueError("At least 120 customer observations are required.")

    random = np.random.default_rng(random_seed)
    records = pd.DataFrame(
        {
            "monthly_spend": random.uniform(20, 140, sample_count),
            "account_months": random.integers(1, 61, sample_count),
            "support_requests": random.integers(0, 7, sample_count),
        }
    )
    records[TARGET_COLUMN] = (
        0.04 * records["monthly_spend"]
        - 0.1 * records["account_months"]
        + 0.8 * records["support_requests"]
        + random.normal(0, 0.7, sample_count)
        > 2.5
    ).astype(int)
    training, holdout = train_test_split(
        records,
        test_size=0.25,
        random_state=random_seed,
        stratify=records[TARGET_COLUMN],
    )
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("classify", LogisticRegression(random_state=random_seed)),
        ]
    )
    model.fit(training[FEATURE_COLUMNS], training[TARGET_COLUMN])
    metadata = {
        "training_rows": len(training),
        "holdout_rows": len(holdout),
        "random_seed": random_seed,
        "feature_names": FEATURE_COLUMNS,
        "positive_fraction": float(training[TARGET_COLUMN].mean()),
    }
    log_metadata(metadata)
    log_metadata(metadata=metadata, infer_model=True)
    return model, holdout.reset_index(drop=True)


def _resolve_training_run(training_run_id: str | None) -> PipelineRunResponse:
    """Resolve a completed training run in the current evaluation's project.

    Args:
        training_run_id: Optional full UUID for an explicitly selected run.

    Returns:
        The validated training run.

    Raises:
        ValueError: If the run is missing, does not match the trigger, belongs
            to another project or pipeline, or did not complete successfully.
    """
    current_run = get_step_context().pipeline_run
    upstream = get_upstream_run(pipeline_run=current_run)
    if training_run_id is not None:
        requested_id = UUID(training_run_id)
        if upstream is not None and upstream.id != requested_id:
            raise ValueError(
                "The selected run does not match the upstream run."
            )
        training_run = Client().get_pipeline_run(requested_id)
    elif upstream is not None:
        training_run = upstream
    else:
        raise ValueError(
            "Evaluation requires an upstream training run or training_run_id."
        )

    if training_run.project.id != current_run.project.id:
        raise ValueError("The training run belongs to another project.")
    if (
        training_run.pipeline is None
        or training_run.pipeline.name != TRAINING_PIPELINE
    ):
        raise ValueError(f"Expected a run of {TRAINING_PIPELINE}.")
    if training_run.status != ExecutionStatus.COMPLETED:
        raise ValueError("The training run must have completed successfully.")
    return training_run


@step(enable_cache=False)
def evaluate_customer_model(
    training_run_id: str | None = None,
) -> tuple[
    Annotated[dict[str, float | int | str], "evaluation_metrics"],
    Annotated[HTMLString, "evaluation_report"],
]:
    """Evaluate the exact classifier and held-out data from a training run.

    Args:
        training_run_id: Full training run UUID for manual evaluation, or None
            to resolve the training run from the platform trigger.

    Returns:
        Structured metrics with source identifiers and an HTML quality report.

    Raises:
        ValueError: If the source run or its expected outputs are unavailable.
        TypeError: If the source artifacts have incompatible types.
    """
    training_run = _resolve_training_run(training_run_id)
    training_step = training_run.steps.get("fit_customer_model")
    if training_step is None:
        raise ValueError("The training run has no fit_customer_model step.")
    outputs = training_step.outputs
    models = outputs.get("customer_classifier", [])
    datasets = outputs.get("customer_holdout", [])
    if len(models) != 1 or len(datasets) != 1:
        raise ValueError("Expected one classifier and one held-out dataset.")
    model_artifact, dataset_artifact = models[0], datasets[0]
    model, holdout = model_artifact.load(), dataset_artifact.load()
    if not isinstance(model, Pipeline) or not isinstance(
        holdout, pd.DataFrame
    ):
        raise TypeError("Expected an sklearn pipeline and pandas dataset.")
    if holdout.empty or not set(FEATURE_COLUMNS + [TARGET_COLUMN]).issubset(
        holdout.columns
    ):
        raise ValueError(
            "The held-out dataset does not have the required data."
        )

    observed = holdout[TARGET_COLUMN]
    predictions = model.predict(holdout[FEATURE_COLUMNS])
    probabilities = model.predict_proba(holdout[FEATURE_COLUMNS])[:, 1]
    tn, fp, fn, tp = confusion_matrix(
        observed, predictions, labels=[0, 1]
    ).ravel()
    metrics: dict[str, float | int | str] = {
        "accuracy": float(accuracy_score(observed, predictions)),
        "precision": float(
            precision_score(observed, predictions, zero_division=0)
        ),
        "recall": float(recall_score(observed, predictions, zero_division=0)),
        "f1": float(f1_score(observed, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(observed, probabilities)),
        "holdout_rows": len(holdout),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "training_run_id": str(training_run.id),
        "model_artifact_id": str(model_artifact.id),
        "holdout_artifact_id": str(dataset_artifact.id),
    }
    if training_run.model_version is not None:
        metrics["model_version_id"] = str(training_run.model_version.id)
    log_metadata(metrics)
    metric_rows = "".join(
        f"<tr><th>{label}</th><td>{float(metrics[key]):.1%}</td></tr>"
        for key, label in (
            ("accuracy", "Accuracy"),
            ("precision", "Precision"),
            ("recall", "Recall"),
            ("f1", "F1 score"),
            ("roc_auc", "ROC AUC"),
        )
    )
    source_rows = "".join(
        f"<dt>{escape(key.replace('_', ' ').title())}</dt>"
        f"<dd><code>{escape(str(value))}</code></dd>"
        for key, value in metrics.items()
        if key.endswith("_id")
    )
    report = HTMLString(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Customer model evaluation</title>
<style>
body{{font:16px system-ui,sans-serif;color:#172b3a;background:#f2f5f7;
margin:0;padding:28px}}main{{max-width:900px;margin:auto;background:white;
padding:28px;border-radius:12px}}h1{{margin:0 0 12px}}h2{{font-size:20px}}
p{{line-height:1.5}}.panels{{display:flex;flex-wrap:wrap;gap:32px}}
section{{flex:1;min-width:260px}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px;text-align:left;border-bottom:1px solid #e0e6ea}}
thead{{background:#edf3f6}}dt{{font-weight:600;margin-top:12px}}
dd{{margin:4px 0;overflow-wrap:anywhere}}.note{{color:#526675}}
</style></head><body><main>
<h1>Customer model evaluation</h1>
<p>Training run: <strong>{escape(training_run.name)}</strong>.<br>
Evaluated on {len(holdout)} held-out customers that were excluded from fitting.</p>
<div class="panels"><section><h2>Classification quality</h2>
<table><tbody>{metric_rows}</tbody></table></section>
<section><h2>Observed versus predicted</h2><table>
<thead><tr><th>Observed</th><th>No follow-up</th><th>Follow-up</th></tr></thead>
<tbody><tr><th>No follow-up</th><td>{tn}</td><td>{fp}</td></tr>
<tr><th>Follow-up</th><td>{fn}</td><td>{tp}</td></tr></tbody></table>
<p class="note">Predictions use a probability threshold of 0.5.</p>
</section></div><h2>Evaluation provenance</h2><dl>{source_rows}</dl>
<p class="note">Synthetic customer activity; these measurements demonstrate
the evaluation workflow and do not establish real-world model quality.</p>
</main></body></html>"""
    )
    return metrics, report
