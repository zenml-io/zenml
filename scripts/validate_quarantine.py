#!/usr/bin/env python3
"""Validate the CI quarantine registry."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml

REQUIRED_FIELDS = {
    "test_id",
    "owner",
    "quarantined_at",
    "expiry",
    "tracking_issue",
    "reason",
    "skip_in",
}


def _parse_date(value: object) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def main() -> None:
    """Run the CLI."""
    path = Path(".github/quarantined-tests.yml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    for index, entry in enumerate(data.get("quarantined", [])):
        missing = REQUIRED_FIELDS - set(entry)
        if missing:
            errors.append(f"entry {index} is missing fields: {sorted(missing)}")
            continue
        quarantined_at = _parse_date(entry["quarantined_at"])
        expiry = _parse_date(entry["expiry"])
        if expiry <= dt.date.today():
            errors.append(f"{entry['test_id']} has an expired quarantine")
        if expiry > quarantined_at + dt.timedelta(days=30):
            errors.append(f"{entry['test_id']} expiry is more than 30 days out")
        if not str(entry["owner"]).strip():
            errors.append(f"{entry['test_id']} owner is empty")
        if not str(entry["tracking_issue"]).startswith("https://github.com/"):
            errors.append(f"{entry['test_id']} tracking_issue must be a GitHub URL")
        if "medium" not in entry.get("skip_in", []):
            errors.append(f"{entry['test_id']} must declare where it is skipped")

    if errors:
        for error in errors:
            print(f"::error::{error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
