"""Shared external-id helpers for slow-CI qualification Check Runs."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any


def format_external_id(
    *, run_id: str, matrix_hash: str, completed_at: str
) -> str:
    """Format the slow-CI qualification external ID."""
    return json.dumps(
        {
            "run_id": run_id,
            "matrix_hash": matrix_hash,
            "completed_at": completed_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_datetime(value: str) -> dt.datetime:
    """Parse a GitHub or ISO timestamp."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_external_id(external_id: str) -> tuple[str, str, dt.datetime]:
    """Parse a slow-CI qualification external ID.

    Older Check Runs used ``run_id:matrix_hash:completed_at``. Keep accepting
    that form so the health gate can read qualifications created before this
    helper existed.
    """
    try:
        payload: Any = json.loads(external_id)
    except json.JSONDecodeError:
        try:
            run_id, matrix_hash, completed_at = external_id.split(":", 2)
        except ValueError as exc:
            raise RuntimeError(
                "Qualification Check Run has invalid external_id: "
                f"{external_id!r}"
            ) from exc
        return run_id, matrix_hash, parse_datetime(completed_at)

    try:
        run_id = str(payload["run_id"])
        matrix_hash = str(payload["matrix_hash"])
        completed_at = str(payload["completed_at"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            "Qualification Check Run has invalid external_id payload: "
            f"{external_id!r}"
        ) from exc

    return run_id, matrix_hash, parse_datetime(completed_at)
