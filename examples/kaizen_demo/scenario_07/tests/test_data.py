"""Check chronological evaluation, feature leakage, and scoring provenance."""

import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scenario_07.data import (
    FEATURE_COLUMNS,
    fit_estimator,
    predict_demand,
    read_source,
    select_scoring_day,
    split_history,
    validate_records,
    validate_training_manifest,
)


@pytest.fixture
def observations() -> pd.DataFrame:
    """Create four complete hourly days with distinct rental outcomes.

    Returns:
        Validated hourly observations.
    """
    timestamps = pd.date_range("2012-07-01", periods=96, freq="h")
    records = pd.DataFrame(
        {column: 1 for column in FEATURE_COLUMNS}, index=range(96)
    )
    records["dteday"] = timestamps.strftime("%Y-%m-%d")
    records["hr"] = timestamps.hour
    records["cnt"] = timestamps.hour * 10 + timestamps.day
    records["casual"] = records["cnt"] - 1
    records["registered"] = 1
    return validate_records(records)


def test_target_derived_features_are_discarded(
    observations: pd.DataFrame,
) -> None:
    """Target-derived columns must never enter the permitted feature set.

    Args:
        observations: Validated hourly observations.
    """
    assert not {"casual", "registered", "instant"}.intersection(
        observations.columns
    )
    assert not {"casual", "registered", "cnt", "timestamp"}.intersection(
        FEATURE_COLUMNS
    )
    model = fit_estimator(observations.iloc[:48], "baseline")
    changed = observations.iloc[48:].copy()
    expected = predict_demand(model, changed)["predicted"]
    changed["cnt"] = 999_999
    changed["casual"] = 999_999
    changed["registered"] = 999_999
    np.testing.assert_array_equal(
        predict_demand(model, changed)["predicted"], expected
    )


def test_split_respects_exclusive_boundaries(
    observations: pd.DataFrame,
) -> None:
    """Evaluation starts where fitting ends and stops before scoring.

    Args:
        observations: Validated hourly observations.
    """
    training, evaluation = split_history(
        observations.sample(frac=1, random_state=1), "2012-07-03", "2012-07-04"
    )
    assert len(training) == 48
    assert len(evaluation) == 24
    assert training["timestamp"].max() < evaluation["timestamp"].min()
    assert evaluation["timestamp"].min() == pd.Timestamp("2012-07-03")
    assert evaluation["timestamp"].max() < pd.Timestamp("2012-07-04")
    scoring = select_scoring_day(observations, "2012-07-04", "2012-07-04")
    assert scoring["timestamp"].min() > evaluation["timestamp"].max()


def test_scoring_rejects_overlap_and_incomplete_days(
    observations: pd.DataFrame,
) -> None:
    """Scoring cannot reuse evaluation data or silently score a partial day.

    Args:
        observations: Validated hourly observations.
    """
    with pytest.raises(ValueError, match="on or after"):
        select_scoring_day(observations, "2012-07-03", "2012-07-04")
    with pytest.raises(ValueError, match="24 hours"):
        select_scoring_day(observations.iloc[:-1], "2012-07-04", "2012-07-04")


def test_duplicate_timestamps_are_rejected(observations: pd.DataFrame) -> None:
    """Duplicate source hours must not inflate scores or demand totals.

    Args:
        observations: Validated hourly observations.
    """
    with pytest.raises(ValueError, match="unique"):
        validate_records(pd.concat([observations, observations.iloc[:1]]))


def test_source_hash_is_verified(
    tmp_path: Path, observations: pd.DataFrame
) -> None:
    """A changed source is rejected before its observations are consumed.

    Args:
        tmp_path: Isolated temporary directory.
        observations: Validated hourly observations.
    """
    source = tmp_path / "hour.csv"
    observations.to_csv(source, index=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    records, provenance = read_source(str(source), digest)
    assert len(records) == len(observations)
    assert provenance["sha256"] == digest
    with pytest.raises(ValueError, match="SHA-256"):
        read_source(str(source), "0" * 64)


def test_csv_artifact_roundtrip_preserves_temporal_split_and_alignment(
    observations: pd.DataFrame,
) -> None:
    """CSV-backed artifacts must work at every date-sensitive step boundary.

    Args:
        observations: Validated hourly observations.
    """

    def roundtrip(frame: pd.DataFrame) -> pd.DataFrame:
        return pd.read_csv(
            io.StringIO(frame.to_csv(index=True)),
            index_col=0,
            parse_dates=True,
        )

    loaded = roundtrip(observations)
    assert loaded["timestamp"].dtype == object
    training, evaluation = split_history(loaded, "2012-07-03", "2012-07-04")
    pd.testing.assert_index_equal(training.index, observations.index[:48])
    pd.testing.assert_index_equal(evaluation.index, observations.index[48:72])
    assert training["timestamp"].max() < evaluation["timestamp"].min()

    model = fit_estimator(roundtrip(training), "baseline")
    expected = predict_demand(model, evaluation)
    predictions = predict_demand(model, roundtrip(evaluation))
    pd.testing.assert_frame_equal(predictions, expected)
    assert pd.api.types.is_datetime64_any_dtype(predictions["timestamp"])
    day = select_scoring_day(loaded, "2012-07-04", "2012-07-04")
    assert len(day) == 24
    pd.testing.assert_index_equal(day.index, observations.index[72:])
    pd.testing.assert_index_equal(
        predict_demand(model, roundtrip(day)).index, day.index
    )


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("training_run_id", "another-run", "another training run"),
        ("sha256", "another-dataset", "same dataset"),
        ("feature_columns", ["cnt"], "feature contract"),
    ],
)
def test_model_provenance_mismatches_are_rejected(
    field: str, value: str | list[str], error: str
) -> None:
    """Scoring requires the exact requested model and its original dataset.

    Args:
        field: Manifest field to replace.
        value: Incompatible value.
        error: Expected validation error fragment.
    """
    manifest = {
        "training_run_id": "selected-run",
        "sha256": "selected-dataset",
        "feature_columns": FEATURE_COLUMNS,
        "evaluation_end": "2012-10-01",
    }
    validate_training_manifest(manifest, "selected-run", "selected-dataset")
    manifest[field] = value
    with pytest.raises(ValueError, match=error):
        validate_training_manifest(
            manifest, "selected-run", "selected-dataset"
        )
