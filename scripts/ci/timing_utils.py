"""Shared timing helpers for CI scripts."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_timestamp(value: str | None) -> float | None:
    """Parse epoch seconds or ISO 8601 text into a Unix timestamp."""
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        pass

    normalized = value.strip().replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.timestamp()


def timestamp_to_iso(timestamp: float | None) -> str | None:
    """Return an ISO 8601 UTC string for a Unix timestamp."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
