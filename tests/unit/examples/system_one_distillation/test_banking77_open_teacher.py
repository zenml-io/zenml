"""Tests for the open Banking77 teacher contract."""

import pytest
from examples.system_one_distillation.banking77_open_teacher import (
    OPEN_TEACHER_CODE_REVISION,
    OPEN_TEACHER_MODEL_ID,
    OPEN_TEACHER_MODEL_REVISION,
    normalize_choice_distribution,
)


def test_open_teacher_is_fully_pinned() -> None:
    """The model package and inference code cannot move between runs."""
    assert OPEN_TEACHER_MODEL_ID == "ZefanCai/Open-Jev-27B-v1.1"
    assert len(OPEN_TEACHER_MODEL_REVISION) == 40
    assert len(OPEN_TEACHER_CODE_REVISION) == 40


def test_normalize_choice_distribution_preserves_taxonomy_order() -> None:
    """Small rounding drift is normalized without changing label order."""
    result = normalize_choice_distribution(
        {"second": 0.34, "first": 0.67}, taxonomy=("first", "second")
    )

    assert list(result) == ["first", "second"]
    assert sum(result.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "probabilities",
    [
        {"first": 1.0},
        {"first": 0.5, "second": -0.5},
        {"first": 0.0, "second": 0.0},
        {"first": float("nan"), "second": 1.0},
    ],
)
def test_normalize_choice_distribution_rejects_invalid_output(
    probabilities: dict[str, float],
) -> None:
    """Missing, negative, empty, and non-finite distributions fail visibly."""
    with pytest.raises(ValueError):
        normalize_choice_distribution(
            probabilities, taxonomy=("first", "second")
        )
