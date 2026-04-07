"""Unit tests for the Modal fast-CI scheduler."""

from pathlib import Path

import pytest
from scripts.ci.scheduler import (
    DEFAULT_INTEGRATION_TEST_DURATION_SECONDS,
    DEFAULT_UNIT_TEST_DURATION_SECONDS,
    ScheduledBatch,
    read_durations_file,
    schedule_batches,
)


def test_read_durations_file_parses_plain_text(tmp_path: Path) -> None:
    """Plain-text duration files should be parsed into a duration map."""
    path = tmp_path / ".test_durations"
    path.write_text(
        "\n".join(
            [
                "tests/unit/test_alpha.py::test_a 1.25",
                "tests/unit/test_beta.py::test_b 2.5",
            ]
        ),
        encoding="utf-8",
    )

    assert read_durations_file(path) == {
        "tests/unit/test_alpha.py::test_a": 1.25,
        "tests/unit/test_beta.py::test_b": 2.5,
    }


def test_read_durations_file_parses_json(tmp_path: Path) -> None:
    """JSON duration files should be parsed into a duration map."""
    path = tmp_path / ".test_durations"
    path.write_text(
        '{"tests/unit/test_alpha.py::test_a": 1.25}',
        encoding="utf-8",
    )

    assert read_durations_file(path) == {
        "tests/unit/test_alpha.py::test_a": 1.25,
    }


def test_schedule_batches_balances_heavy_tests_first() -> None:
    """The scheduler should distribute the heaviest tests first."""
    batches = schedule_batches(
        [
            "tests/unit/test_alpha.py::test_a",
            "tests/unit/test_beta.py::test_b",
            "tests/unit/test_gamma.py::test_c",
            "tests/unit/test_delta.py::test_d",
        ],
        max_batches=2,
        durations={
            "tests/unit/test_alpha.py::test_a": 10.0,
            "tests/unit/test_beta.py::test_b": 9.0,
            "tests/unit/test_gamma.py::test_c": 1.0,
            "tests/unit/test_delta.py::test_d": 1.0,
        },
        default_duration_seconds=DEFAULT_UNIT_TEST_DURATION_SECONDS,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=(
                "tests/unit/test_alpha.py::test_a",
                "tests/unit/test_delta.py::test_d",
            ),
            duration_seconds=11.0,
        ),
        ScheduledBatch(
            node_ids=(
                "tests/unit/test_beta.py::test_b",
                "tests/unit/test_gamma.py::test_c",
            ),
            duration_seconds=10.0,
        ),
    ]


def test_schedule_batches_uses_default_duration_for_unknown_tests() -> None:
    """Unknown tests should receive the suite default duration."""
    batches = schedule_batches(
        [
            "tests/integration/test_alpha.py::test_a",
            "tests/integration/test_beta.py::test_b",
            "tests/integration/test_gamma.py::test_c",
        ],
        max_batches=2,
        durations={
            "tests/integration/test_alpha.py::test_a": 30.0,
        },
        default_duration_seconds=DEFAULT_INTEGRATION_TEST_DURATION_SECONDS,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=(
                "tests/integration/test_alpha.py::test_a",
            ),
            duration_seconds=30.0,
        ),
        ScheduledBatch(
            node_ids=(
                "tests/integration/test_beta.py::test_b",
                "tests/integration/test_gamma.py::test_c",
            ),
            duration_seconds=10.0,
        ),
    ]


def test_schedule_batches_limits_batch_count_to_number_of_tests() -> None:
    """The scheduler should not create empty batches."""
    batches = schedule_batches(
        [
            "tests/unit/test_alpha.py::test_a",
            "tests/unit/test_beta.py::test_b",
        ],
        max_batches=20,
    )

    assert len(batches) == 2
    assert batches == [
        ScheduledBatch(
            node_ids=("tests/unit/test_alpha.py::test_a",),
            duration_seconds=DEFAULT_UNIT_TEST_DURATION_SECONDS,
        ),
        ScheduledBatch(
            node_ids=("tests/unit/test_beta.py::test_b",),
            duration_seconds=DEFAULT_UNIT_TEST_DURATION_SECONDS,
        ),
    ]


def test_schedule_batches_rejects_non_positive_batch_count() -> None:
    """A non-positive batch count should raise a validation error."""
    with pytest.raises(ValueError, match="max_batches must be greater than zero"):
        schedule_batches(["tests/unit/test_alpha.py::test_a"], max_batches=0)


def test_schedule_batches_keeps_class_scopes_together_for_loadscope() -> None:
    """Loadscope scheduling should keep tests from the same class together."""
    batches = schedule_batches(
        [
            "tests/unit/test_alpha.py::TestA::test_one",
            "tests/unit/test_alpha.py::TestA::test_two",
            "tests/unit/test_beta.py::test_three",
        ],
        max_batches=2,
        durations={
            "tests/unit/test_alpha.py::TestA::test_one": 5.0,
            "tests/unit/test_alpha.py::TestA::test_two": 4.0,
            "tests/unit/test_beta.py::test_three": 6.0,
        },
        default_duration_seconds=DEFAULT_UNIT_TEST_DURATION_SECONDS,
        group_by_scope=True,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=(
                "tests/unit/test_alpha.py::TestA::test_one",
                "tests/unit/test_alpha.py::TestA::test_two",
            ),
            duration_seconds=9.0,
        ),
        ScheduledBatch(
            node_ids=("tests/unit/test_beta.py::test_three",),
            duration_seconds=6.0,
        ),
    ]


def test_schedule_batches_chunks_oversized_scope_groups() -> None:
    """Scope grouping should split oversized groups into deterministic chunks."""
    batches = schedule_batches(
        [
            "tests/integration/test_alpha.py::test_one",
            "tests/integration/test_alpha.py::test_two",
            "tests/integration/test_alpha.py::test_three",
            "tests/integration/test_beta.py::test_four",
        ],
        max_batches=3,
        durations={
            "tests/integration/test_alpha.py::test_one": 5.0,
            "tests/integration/test_alpha.py::test_two": 4.0,
            "tests/integration/test_alpha.py::test_three": 3.0,
            "tests/integration/test_beta.py::test_four": 2.0,
        },
        default_duration_seconds=DEFAULT_INTEGRATION_TEST_DURATION_SECONDS,
        group_by_scope=True,
        max_group_size=2,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=(
                "tests/integration/test_alpha.py::test_one",
                "tests/integration/test_alpha.py::test_two",
            ),
            duration_seconds=9.0,
        ),
        ScheduledBatch(
            node_ids=("tests/integration/test_alpha.py::test_three",),
            duration_seconds=3.0,
        ),
        ScheduledBatch(
            node_ids=("tests/integration/test_beta.py::test_four",),
            duration_seconds=2.0,
        ),
    ]


def test_schedule_batches_chunks_scope_groups_by_duration_target() -> None:
    """Timing-aware chunking should split oversized files by cumulative cost."""
    batches = schedule_batches(
        [
            "tests/integration/test_alpha.py::test_one",
            "tests/integration/test_alpha.py::test_two",
            "tests/integration/test_alpha.py::test_three",
            "tests/integration/test_alpha.py::test_four",
        ],
        max_batches=2,
        durations={
            "tests/integration/test_alpha.py::test_one": 7.0,
            "tests/integration/test_alpha.py::test_two": 6.0,
            "tests/integration/test_alpha.py::test_three": 4.0,
            "tests/integration/test_alpha.py::test_four": 3.0,
        },
        default_duration_seconds=DEFAULT_INTEGRATION_TEST_DURATION_SECONDS,
        group_by_scope=True,
        max_group_duration_seconds=10.0,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=(
                "tests/integration/test_alpha.py::test_two",
                "tests/integration/test_alpha.py::test_three",
            ),
            duration_seconds=10.0,
        ),
        ScheduledBatch(
            node_ids=(
                "tests/integration/test_alpha.py::test_one",
                "tests/integration/test_alpha.py::test_four",
            ),
            duration_seconds=10.0,
        ),
    ]


def test_schedule_batches_uses_file_average_for_unknown_tests() -> None:
    """Unknown tests should inherit file-level timing before defaulting."""
    batches = schedule_batches(
        [
            "tests/unit/test_alpha.py::test_known",
            "tests/unit/test_alpha.py::test_unknown",
            "tests/unit/test_beta.py::test_other",
        ],
        max_batches=2,
        durations={
            "tests/unit/test_alpha.py::test_known": 8.0,
            "tests/unit/test_beta.py::test_other": 1.0,
        },
        default_duration_seconds=DEFAULT_UNIT_TEST_DURATION_SECONDS,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=(
                "tests/unit/test_alpha.py::test_known",
                "tests/unit/test_beta.py::test_other",
            ),
            duration_seconds=9.0,
        ),
        ScheduledBatch(
            node_ids=("tests/unit/test_alpha.py::test_unknown",),
            duration_seconds=8.0,
        ),
    ]


def test_schedule_batches_defaults_to_individual_nodes() -> None:
    """Default scheduling should not keep class scopes together."""
    batches = schedule_batches(
        [
            "tests/unit/test_alpha.py::TestA::test_one",
            "tests/unit/test_alpha.py::TestA::test_two",
            "tests/unit/test_beta.py::test_three",
        ],
        max_batches=2,
        durations={
            "tests/unit/test_alpha.py::TestA::test_one": 5.0,
            "tests/unit/test_alpha.py::TestA::test_two": 4.0,
            "tests/unit/test_beta.py::test_three": 6.0,
        },
        default_duration_seconds=DEFAULT_UNIT_TEST_DURATION_SECONDS,
    )

    assert batches == [
        ScheduledBatch(
            node_ids=("tests/unit/test_beta.py::test_three",),
            duration_seconds=6.0,
        ),
        ScheduledBatch(
            node_ids=(
                "tests/unit/test_alpha.py::TestA::test_one",
                "tests/unit/test_alpha.py::TestA::test_two",
            ),
            duration_seconds=9.0,
        ),
    ]
