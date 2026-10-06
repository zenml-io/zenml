"""Train, evaluate, and score bike demand with explicit artifact provenance."""

from typing import Annotated
from uuid import UUID

import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline

from zenml import ArtifactConfig, get_step_context, log_metadata, step
from zenml.client import Client
from zenml.enums import ArtifactType, ExecutionStatus
from zenml.types import HTMLString

from .data import (
    FEATURE_COLUMNS,
    TRAINING_PIPELINE,
    fit_estimator,
    measure_importance,
    measure_predictions,
    predict_demand,
    read_source,
    select_scoring_day,
    split_history,
    validate_training_manifest,
)
from .reports import (
    render_daily_operations,
    render_demand_explorer,
    render_model_scorecard,
)


@step(enable_cache=False)
def load_bike_data(
    source_uri: str, source_sha256: str | None = None
) -> tuple[
    Annotated[pd.DataFrame, "bike_hourly_observations"],
    Annotated[dict[str, str | int], "bike_data_provenance"],
]:
    """Load and validate the current version of the hourly rental source.

    Args:
        source_uri: Public archive or hourly CSV location.
        source_sha256: Optional expected digest of the source bytes.

    Returns:
        Hourly observations and their source provenance.
    """
    observations, provenance = read_source(source_uri, source_sha256)
    log_metadata(provenance)
    return observations, provenance


@step
def prepare_bike_history(
    observations: pd.DataFrame,
    provenance: dict[str, str | int],
    train_end: str,
    evaluation_end: str,
) -> tuple[
    Annotated[pd.DataFrame, "bike_training_observations"],
    Annotated[pd.DataFrame, "bike_evaluation_observations"],
    Annotated[HTMLString, "bike_demand_explorer"],
]:
    """Partition historical data and describe its observed rental patterns.

    Args:
        observations: Validated hourly observations.
        provenance: Dataset source and digest.
        train_end: Exclusive end of training observations.
        evaluation_end: Exclusive end of evaluation observations.

    Returns:
        Chronological training and evaluation partitions and an HTML explorer.
    """
    training, evaluation = split_history(
        observations, train_end, evaluation_end
    )
    report_context = {
        **provenance,
        "train_end": train_end,
        "evaluation_end": evaluation_end,
        "source_artifact_id": str(
            get_step_context().inputs["observations"][0].id
        ),
    }
    log_metadata(
        {
            "training_rows": len(training),
            "evaluation_rows": len(evaluation),
            "train_end": train_end,
            "evaluation_end": evaluation_end,
        }
    )
    return (
        training,
        evaluation,
        HTMLString(render_demand_explorer(observations, report_context)),
    )


@step(enable_cache=False)
def fit_bike_model(
    training: pd.DataFrame,
    provenance: dict[str, str | int],
    model_variant: str,
    model_version: str,
    train_end: str,
    evaluation_end: str,
) -> tuple[
    Annotated[
        Pipeline,
        ArtifactConfig(
            name="bike_demand_estimator", artifact_type=ArtifactType.MODEL
        ),
    ],
    Annotated[dict[str, str | int | list[str]], "bike_training_manifest"],
]:
    """Fit a demand estimator and persist its exact data and model contract.

    Args:
        training: Observations preceding the evaluation interval.
        provenance: Dataset source and digest.
        model_variant: Calendar baseline or gradient boosting.
        model_version: Named ZenML model version.
        train_end: Exclusive training boundary.
        evaluation_end: Exclusive evaluation boundary.

    Returns:
        The trained estimator and a manifest needed for later scoring.
    """
    model = fit_estimator(training, model_variant)
    manifest: dict[str, str | int | list[str]] = {
        **provenance,
        "model_variant": model_variant,
        "model_version": model_version,
        "feature_columns": FEATURE_COLUMNS,
        "train_end": train_end,
        "evaluation_end": evaluation_end,
        "training_rows": len(training),
        "training_run_id": str(get_step_context().pipeline_run.id),
        "training_data_artifact_id": str(
            get_step_context().inputs["training"][0].id
        ),
    }
    log_metadata(manifest)
    log_metadata(metadata=manifest, infer_model=True)
    return model, manifest


@step
def evaluate_bike_model(
    model: Pipeline,
    training: pd.DataFrame,
    evaluation: pd.DataFrame,
    manifest: dict[str, str | int | list[str]],
) -> tuple[
    Annotated[dict[str, float | int | str], "bike_evaluation_metrics"],
    Annotated[pd.DataFrame, "bike_evaluation_predictions"],
    Annotated[HTMLString, "bike_model_scorecard"],
]:
    """Compare held-out predictions to a calendar-only baseline.

    Args:
        model: Trained demand pipeline.
        training: Observations used for fitting the comparison baseline.
        evaluation: Later observations excluded from fitting.
        manifest: Model training and data provenance.

    Returns:
        Structured quality metrics, predictions, and an HTML model scorecard.
    """
    predictions = predict_demand(model, evaluation)
    baseline = predict_demand(fit_estimator(training, "baseline"), evaluation)
    predictions["baseline_predicted"] = baseline["predicted"]
    rush_hours = predictions["hr"].isin([7, 8, 9, 16, 17, 18]) & (
        predictions["workingday"] == 1
    )
    metrics: dict[str, float | int | str] = {
        **measure_predictions(predictions),
        "baseline_mae": float(
            mean_absolute_error(
                predictions["cnt"], predictions["baseline_predicted"]
            )
        ),
        "evaluation_rows": len(evaluation),
        "model_variant": str(manifest["model_variant"]),
        "model_version": str(manifest["model_version"]),
        "train_end": str(manifest["train_end"]),
        "evaluation_end": str(manifest["evaluation_end"]),
    }
    if rush_hours.any():
        metrics["rush_hour_mae"] = float(
            mean_absolute_error(
                predictions.loc[rush_hours, "cnt"],
                predictions.loc[rush_hours, "predicted"],
            )
        )
        metrics["baseline_rush_hour_mae"] = float(
            mean_absolute_error(
                predictions.loc[rush_hours, "cnt"],
                predictions.loc[rush_hours, "baseline_predicted"],
            )
        )
    importance = measure_importance(model, evaluation)
    log_metadata(metrics)
    log_metadata(metadata=metrics, infer_model=True)
    report_provenance = {
        **manifest,
        "model_artifact_id": str(get_step_context().inputs["model"][0].id),
        "evaluation_artifact_id": str(
            get_step_context().inputs["evaluation"][0].id
        ),
    }
    report = render_model_scorecard(
        predictions, metrics, importance, report_provenance
    )
    return metrics, predictions, HTMLString(report)


@step(enable_cache=False)
def score_bike_day(
    observations: pd.DataFrame,
    provenance: dict[str, str | int],
    training_run_id: str,
    scoring_date: str,
) -> tuple[
    Annotated[pd.DataFrame, "bike_daily_predictions"],
    Annotated[dict[str, float | int | str], "bike_daily_metrics"],
    Annotated[HTMLString, "bike_daily_operations"],
]:
    """Score a historical day with the exact model from a completed run.

    Args:
        observations: Historical observations including the requested date.
        provenance: Dataset source and content digest.
        training_run_id: Full UUID of a completed bike training run.
        scoring_date: Calendar day after the training evaluation interval.

    Returns:
        Daily predictions, provenance-aware metrics, and an operations report.

    Raises:
        ValueError: If run, artifacts, provenance, or scoring date is invalid.
        TypeError: If artifacts do not contain an sklearn pipeline and manifest.
    """
    current_run = get_step_context().pipeline_run
    training_run = Client().get_pipeline_run(
        UUID(training_run_id), project=current_run.project.id
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
    fit_step = training_run.steps.get("fit_bike_model")
    if fit_step is None:
        raise ValueError("The training run has no fit_bike_model step.")
    source_model_version = fit_step.model_version or training_run.model_version
    current_model_version = get_step_context().model_version
    if current_model_version is not None and (
        source_model_version is None
        or current_model_version.id != source_model_version.id
    ):
        raise ValueError(
            "Scoring is attached to a different model version than its training run."
        )
    estimators = fit_step.outputs.get("bike_demand_estimator", [])
    manifests = fit_step.outputs.get("bike_training_manifest", [])
    if len(estimators) != 1 or len(manifests) != 1:
        raise ValueError("Expected one model and one training manifest.")
    model, manifest = estimators[0].load(), manifests[0].load()
    if not isinstance(model, Pipeline) or not isinstance(manifest, dict):
        raise TypeError(
            "Expected an sklearn pipeline and a metadata dictionary."
        )
    validate_training_manifest(
        manifest, str(training_run.id), str(provenance["sha256"])
    )
    day = select_scoring_day(
        observations, scoring_date, manifest["evaluation_end"]
    )
    predictions = predict_demand(model, day)
    metrics: dict[str, float | int | str] = {
        **measure_predictions(predictions),
        "observed_total": int(predictions["cnt"].sum()),
        "predicted_total": float(predictions["predicted"].sum()),
        "scoring_date": scoring_date,
        "peak_hour": int(
            predictions.loc[predictions["predicted"].idxmax(), "hr"]
        ),
        "training_run_id": str(training_run.id),
        "model_artifact_id": str(estimators[0].id),
        "model_version": str(manifest["model_version"]),
    }
    log_metadata(metrics)
    if get_step_context().model_version is not None:
        log_metadata(
            metadata={f"daily_{key}": value for key, value in metrics.items()},
            infer_model=True,
        )
    report_context = {**manifest, **provenance, **metrics}
    return (
        predictions,
        metrics,
        HTMLString(
            render_daily_operations(predictions, metrics, report_context)
        ),
    )
