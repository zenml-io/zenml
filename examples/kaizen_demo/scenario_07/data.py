"""Validated bike rental data and reproducible historical model evaluation."""

import hashlib
import io
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen
from zipfile import ZipFile, is_zipfile

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

SOURCE_URI = "https://archive.ics.uci.edu/static/public/275/bike%2Bsharing%2Bdataset.zip"
FEATURE_COLUMNS = [
    "hr",
    "weekday",
    "workingday",
    "holiday",
    "mnth",
    "yr",
    "season",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
]
TRAINING_PIPELINE = "bike_demand_training"


def read_source(
    source_uri: str, source_sha256: str | None = None
) -> tuple[pd.DataFrame, dict[str, str | int]]:
    """Read a public hourly CSV or UCI archive and record its content digest.

    Args:
        source_uri: Local, HTTP, or active artifact-store location.
        source_sha256: Expected SHA-256 digest of the complete source bytes.

    Returns:
        Validated hourly observations and source provenance.

    Raises:
        ValueError: If the URI, digest, archive, or dataset is invalid.
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
    if location.scheme in {"http", "https"}:
        with urlopen(source_uri, timeout=45) as response:
            payload = response.read(20_000_001)
    elif location.scheme in {"", "file"}:
        path = unquote(location.path) if location.scheme else source_uri
        payload = Path(path).expanduser().read_bytes()
    else:
        from zenml.client import Client

        with Client().active_stack.artifact_store.open(
            source_uri, "rb"
        ) as source:
            payload = source.read(20_000_001)
    if len(payload) > 20_000_000:
        raise ValueError("The hourly source must be smaller than 20 MB.")
    digest = hashlib.sha256(payload).hexdigest()
    if source_sha256 is not None and digest != source_sha256.lower():
        raise ValueError(
            "The source does not match the expected SHA-256 digest."
        )
    stream = io.BytesIO(payload)
    if is_zipfile(stream):
        with ZipFile(stream) as archive:
            members = [
                name
                for name in archive.namelist()
                if Path(name).name == "hour.csv"
            ]
            if (
                len(members) != 1
                or archive.getinfo(members[0]).file_size > 20_000_000
            ):
                raise ValueError("Expected one hourly CSV smaller than 20 MB.")
            records = pd.read_csv(io.BytesIO(archive.read(members[0])))
    else:
        stream.seek(0)
        records = pd.read_csv(stream)
    records = validate_records(records)
    return records, {
        "dataset_name": "UCI Bike Sharing",
        "source_uri": source_uri,
        "sha256": digest,
        "row_count": len(records),
        "first_timestamp": records["timestamp"].min().isoformat(),
        "last_timestamp": records["timestamp"].max().isoformat(),
    }


def validate_records(records: pd.DataFrame) -> pd.DataFrame:
    """Validate hourly observations and discard target-derived input columns.

    Args:
        records: Raw hourly UCI observations.

    Returns:
        Sorted observations with an unambiguous local timestamp.

    Raises:
        ValueError: If required data, numeric values, or timestamps are invalid.
    """
    required = ["dteday", "cnt", *FEATURE_COLUMNS]
    if records.empty or not set(required).issubset(records.columns):
        raise ValueError(
            "The dataset must contain the UCI hourly columns and observations."
        )
    result = records.loc[:, required].copy()
    for column in ["cnt", *FEATURE_COLUMNS]:
        result[column] = pd.to_numeric(result[column], errors="raise")
    if not np.isfinite(result[["cnt", *FEATURE_COLUMNS]].to_numpy()).all():
        raise ValueError("Observations must contain finite numeric values.")
    if (
        not result["hr"].between(0, 23).all()
        or not (result["hr"] % 1 == 0).all()
    ):
        raise ValueError("Hours must be integers from 0 through 23.")
    if (result["cnt"] < 0).any():
        raise ValueError("Rental counts must not be negative.")
    dates = pd.to_datetime(result["dteday"], format="%Y-%m-%d", errors="raise")
    result["timestamp"] = dates + pd.to_timedelta(result["hr"], unit="h")
    if (
        result["timestamp"].isna().any()
        or result["timestamp"].duplicated().any()
    ):
        raise ValueError(
            "Each observation must have a unique valid timestamp."
        )
    return result.sort_values("timestamp").reset_index(drop=True)


def split_history(
    records: pd.DataFrame, train_end: str, evaluation_end: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate earlier fitting data from the following evaluation interval.

    Args:
        records: Validated observations with timestamps.
        train_end: Exclusive training boundary and inclusive evaluation start.
        evaluation_end: Exclusive evaluation boundary.

    Returns:
        Training and evaluation observations with no overlapping timestamps.

    Raises:
        ValueError: If boundaries are reversed or either partition is empty.
    """
    records = restore_timestamps(records)
    start, end = pd.Timestamp(train_end), pd.Timestamp(evaluation_end)
    if start >= end:
        raise ValueError("train_end must precede evaluation_end.")
    training = records.loc[records["timestamp"] < start].copy()
    evaluation = records.loc[
        (records["timestamp"] >= start) & (records["timestamp"] < end)
    ].copy()
    if len(training) < 48 or evaluation.empty:
        raise ValueError(
            "At least 48 training observations and a nonempty evaluation interval are required."
        )
    return training, evaluation


def select_scoring_day(
    records: pd.DataFrame, scoring_date: str, evaluation_end: str
) -> pd.DataFrame:
    """Select a complete historical day after the model's evaluation period.

    Args:
        records: Validated hourly observations.
        scoring_date: Historical calendar date to score.
        evaluation_end: Exclusive end of the model evaluation interval.

    Returns:
        Exactly 24 hourly observations for the selected day.

    Raises:
        ValueError: If the day overlaps evaluation or lacks a full 24 hours.
    """
    records = restore_timestamps(records)
    day = pd.Timestamp(scoring_date)
    if day != day.normalize() or day < pd.Timestamp(evaluation_end):
        raise ValueError("Select a calendar day on or after evaluation_end.")
    selected = records.loc[
        (records["timestamp"] >= day)
        & (records["timestamp"] < day + pd.Timedelta(days=1))
    ].copy()
    if len(selected) != 24 or set(selected["hr"]) != set(range(24)):
        raise ValueError("The selected scoring day must contain all 24 hours.")
    return selected


def fit_estimator(training: pd.DataFrame, model_variant: str) -> Pipeline:
    """Fit a calendar baseline or a bounded gradient boosting demand model.

    Args:
        training: Historical fitting observations.
        model_variant: Either baseline or gradient_boosting.

    Returns:
        A fitted sklearn pipeline with explicit feature selection.

    Raises:
        ValueError: If the model variant is unknown.
    """
    if model_variant == "baseline":
        transform = ColumnTransformer(
            [
                (
                    "calendar",
                    OneHotEncoder(
                        handle_unknown="ignore", sparse_output=False
                    ),
                    ["hr", "workingday"],
                )
            ]
        )
        estimator = Ridge(alpha=1.0)
    elif model_variant == "gradient_boosting":
        transform = ColumnTransformer(
            [("features", "passthrough", FEATURE_COLUMNS)]
        )
        estimator = HistGradientBoostingRegressor(
            max_iter=150,
            max_leaf_nodes=15,
            learning_rate=0.08,
            early_stopping=False,
            random_state=17,
        )
    else:
        raise ValueError(
            "model_variant must be baseline or gradient_boosting."
        )
    model = Pipeline([("features", transform), ("regressor", estimator)])
    with threadpool_limits(limits=1):
        model.fit(training[FEATURE_COLUMNS], training["cnt"])
    return model


def predict_demand(
    model: Pipeline, observations: pd.DataFrame
) -> pd.DataFrame:
    """Score hourly observations without passing observed rentals to the model.

    Args:
        model: Fitted sklearn demand pipeline.
        observations: Historical observations including observed rentals.

    Returns:
        Predictions and retrospective errors alongside the observation data.
    """
    result = restore_timestamps(observations)
    with threadpool_limits(limits=1):
        result["predicted"] = np.maximum(
            model.predict(observations[FEATURE_COLUMNS]), 0
        )
    result["error"] = result["predicted"] - result["cnt"]
    result["absolute_error"] = result["error"].abs()
    return result


def restore_timestamps(records: pd.DataFrame) -> pd.DataFrame:
    """Restore timestamp types after CSV materialization without reindexing.

    Args:
        records: Hourly observations with string or datetime timestamps.

    Returns:
        A copy with parsed timestamps and its original row index preserved.

    Raises:
        ValueError: If timestamps are missing, invalid, or repeated.
    """
    if "timestamp" not in records:
        raise ValueError("Hourly observations require a timestamp column.")
    restored = records.copy()
    restored["timestamp"] = pd.to_datetime(
        restored["timestamp"], errors="raise"
    )
    if (
        restored["timestamp"].isna().any()
        or restored["timestamp"].duplicated().any()
    ):
        raise ValueError(
            "Hourly observations require unique valid timestamps."
        )
    return restored


def measure_predictions(predictions: pd.DataFrame) -> dict[str, float]:
    """Compute regression scores on supplied observed and predicted rentals.

    Args:
        predictions: Hourly predictions with cnt and predicted columns.

    Returns:
        MAE, RMSE, and coefficient of determination.
    """
    return {
        "mae": float(
            mean_absolute_error(predictions["cnt"], predictions["predicted"])
        ),
        "rmse": float(
            root_mean_squared_error(
                predictions["cnt"], predictions["predicted"]
            )
        ),
        "r2": float(r2_score(predictions["cnt"], predictions["predicted"])),
    }


def measure_importance(
    model: Pipeline, evaluation: pd.DataFrame
) -> pd.DataFrame:
    """Estimate model reliance on features using held-out permutation MAE.

    Args:
        model: Fitted demand pipeline.
        evaluation: Observations excluded from model fitting.

    Returns:
        Feature names and mean increases in raw-prediction MAE after shuffling.
    """
    sample = evaluation.sample(n=min(720, len(evaluation)), random_state=17)
    with threadpool_limits(limits=1):
        result = permutation_importance(
            model,
            sample[FEATURE_COLUMNS],
            sample["cnt"],
            scoring="neg_mean_absolute_error",
            n_repeats=2,
            random_state=17,
            n_jobs=1,
        )
    return (
        pd.DataFrame(
            {"feature": FEATURE_COLUMNS, "importance": result.importances_mean}
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def validate_training_manifest(
    manifest: dict, training_run_id: str, source_sha256: str
) -> None:
    """Check that a model manifest identifies the requested run and dataset.

    Args:
        manifest: Stored training metadata.
        training_run_id: Exact source training run UUID.
        source_sha256: Digest of the scoring dataset.

    Raises:
        ValueError: If the run, dataset, features, or boundary is inconsistent.
    """
    if manifest.get("training_run_id") != training_run_id:
        raise ValueError("The model manifest belongs to another training run.")
    if manifest.get("sha256") != source_sha256:
        raise ValueError(
            "Historical scoring must use the same dataset version as training."
        )
    if manifest.get("feature_columns") != FEATURE_COLUMNS:
        raise ValueError("The model uses an unexpected feature contract.")
    if not isinstance(manifest.get("evaluation_end"), str):
        raise ValueError("The manifest must identify the evaluation boundary.")
