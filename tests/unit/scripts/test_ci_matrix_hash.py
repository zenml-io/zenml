"""Tests for CI matrix hash computation."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from scripts.ci_matrix_hash import compute_matrix_hash


def test_matrix_hash_ignores_yaml_formatting_and_comments(
    tmp_path: Path,
) -> None:
    """Formatting-only workflow edits should not invalidate qualifications."""
    first = tmp_path / "first.yml"
    second = tmp_path / "second.yml"
    first.write_text(
        dedent(
            """
        jobs:
          unit:
            strategy:
              fail-fast: false
              matrix:
                python-version: ['3.10', '3.13']
        """
        )
    )
    second.write_text(
        dedent(
            """
        jobs:
          unit:
              # comment-only churn
              strategy:
                  fail-fast: false
                  matrix:
                      python-version: ['3.10', '3.13']
        """
        )
    )

    assert compute_matrix_hash(first) == compute_matrix_hash(second)


def test_matrix_hash_changes_when_strategy_changes(tmp_path: Path) -> None:
    """Actual matrix changes should invalidate qualifications."""
    first = tmp_path / "first.yml"
    second = tmp_path / "second.yml"
    first.write_text(
        dedent(
            """
        jobs:
          unit:
            strategy:
              matrix:
                python-version: ['3.10']
        """
        )
    )
    second.write_text(
        dedent(
            """
        jobs:
          unit:
            strategy:
              matrix:
                python-version: ['3.13']
        """
        )
    )

    assert compute_matrix_hash(first) != compute_matrix_hash(second)
