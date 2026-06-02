"""Helpers for writing GitHub Actions outputs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def _is_sensitive_output_name(name: str) -> bool:
    """Return whether an output name likely carries sensitive data."""
    lowered = name.lower()
    return any(
        token in lowered for token in ("password", "token", "secret", "key")
    )


def write_github_outputs(values: Mapping[str, object]) -> None:
    """Write GitHub Actions outputs, redacting sensitive stdout fallback."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        for name, value in values.items():
            safe_value = (
                "***REDACTED***"
                if _is_sensitive_output_name(name)
                else str(value)
            )
            print(f"{name}={safe_value}")
        return

    with Path(output_path).open("a", encoding="utf-8") as output_file:
        for name, value in values.items():
            output_file.write(f"{name}={value}\n")
