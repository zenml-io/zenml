"""Tests for slow-CI qualification external IDs."""

from __future__ import annotations

from scripts.ci_qualification_ids import (
    format_external_id,
    parse_external_id,
)


def test_format_and_parse_external_id_roundtrip() -> None:
    """JSON external IDs round-trip timestamps that contain colons."""
    external_id = format_external_id(
        run_id="123",
        matrix_hash="abc",
        completed_at="2026-06-02T10:06:00+00:00",
    )

    run_id, matrix_hash, completed_at = parse_external_id(external_id)

    assert run_id == "123"
    assert matrix_hash == "abc"
    assert completed_at.isoformat() == "2026-06-02T10:06:00+00:00"


def test_parse_external_id_accepts_legacy_colon_format() -> None:
    """Existing qualification Check Runs remain readable by the gate."""
    run_id, matrix_hash, completed_at = parse_external_id(
        "123:abc:2026-06-02T10:06:00+00:00"
    )

    assert run_id == "123"
    assert matrix_hash == "abc"
    assert completed_at.isoformat() == "2026-06-02T10:06:00+00:00"
