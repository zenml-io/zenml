"""Train bike rental demand models and score historical daily operations."""

from build_settings import create_docker_settings

from zenml import Model, pipeline

from .data import SOURCE_URI
from .steps import (
    evaluate_bike_model,
    fit_bike_model,
    load_bike_data,
    prepare_bike_history,
    score_bike_day,
)


@pipeline(settings={"docker": create_docker_settings()})
def bike_demand_training(
    model_version: str,
    model_variant: str = "gradient_boosting",
    source_uri: str = SOURCE_URI,
    source_sha256: str | None = None,
    train_end: str = "2012-07-01",
    evaluation_end: str = "2012-10-01",
) -> None:
    """Train and evaluate an hourly demand model on chronological partitions.

    Args:
        model_version: Explicit name of the ZenML bike-demand model version.
        model_variant: baseline or gradient_boosting.
        source_uri: Public UCI archive or hourly CSV location.
        source_sha256: Optional expected source digest.
        train_end: Exclusive end of model fitting observations.
        evaluation_end: Exclusive end of held-out evaluation observations.
    """
    model_context = Model(
        name="bike-demand",
        version=model_version,
        description="Hourly bike rental demand using calendar and observed weather.",
        limitations="Historical evaluation using observed weather, not a live weather forecast.",
    )
    observations, provenance = load_bike_data.with_options(
        model=model_context
    )(source_uri=source_uri, source_sha256=source_sha256)
    training, evaluation, _ = prepare_bike_history.with_options(
        model=model_context
    )(observations, provenance, train_end, evaluation_end)
    estimator, manifest = fit_bike_model.with_options(model=model_context)(
        training,
        provenance,
        model_variant,
        model_version,
        train_end,
        evaluation_end,
    )
    evaluate_bike_model.with_options(model=model_context)(
        estimator, training, evaluation, manifest
    )


@pipeline(enable_cache=False, settings={"docker": create_docker_settings()})
def bike_demand_scoring(
    training_run_id: str,
    scoring_date: str = "2012-10-15",
    source_uri: str = SOURCE_URI,
    source_sha256: str | None = None,
) -> None:
    """Score a historical day with one explicitly selected training run.

    Args:
        training_run_id: Full UUID of the training run supplying the estimator.
        scoring_date: Date on or after the evaluation interval's end.
        source_uri: Archive or CSV from the same dataset version as training.
        source_sha256: Optional expected source digest.
    """
    observations, provenance = load_bike_data(
        source_uri=source_uri, source_sha256=source_sha256
    )
    score_bike_day(observations, provenance, training_run_id, scoring_date)
