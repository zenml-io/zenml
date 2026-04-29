"""Validate XML artifacts produced by CI scripts."""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


class ArtifactValidationError(RuntimeError):
    """Raised when an XML artifact is missing, stale, or invalid."""


def validate_xml_artifact(
    path: Path,
    *,
    label: str,
    allowed_root_tags: set[str],
    min_bytes: int = 1,
    mtime_after: float | None = None,
) -> None:
    """Validate that an XML artifact exists, is fresh, and parses."""
    if not path.exists():
        raise ArtifactValidationError(f"{label} not found: {path}")

    try:
        stat = path.stat()
    except OSError as exc:
        raise ArtifactValidationError(
            f"Could not stat {label} {path}: {exc}"
        ) from exc

    if stat.st_size < min_bytes:
        raise ArtifactValidationError(
            f"{label} is too small: {path} ({stat.st_size} bytes)"
        )

    if mtime_after is not None and stat.st_mtime < mtime_after:
        raise ArtifactValidationError(f"{label} is stale: {path}")

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ArtifactValidationError(
            f"{label} is not parseable XML: {path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ArtifactValidationError(
            f"Could not read {label} {path}: {exc}"
        ) from exc

    if root.tag not in allowed_root_tags:
        expected = ", ".join(sorted(allowed_root_tags))
        raise ArtifactValidationError(
            f"{label} has unexpected root tag '{root.tag}' in {path}; expected {expected}"
        )


def _emit_error(message: str) -> None:
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::error::{message}", file=sys.stderr)
    else:
        print(message, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Validate an XML artifact from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--root-tag", action="append", required=True)
    parser.add_argument("--min-bytes", type=int, default=1)
    parser.add_argument("--mtime-after", type=float)
    args = parser.parse_args(argv)

    try:
        validate_xml_artifact(
            args.path,
            label=args.label,
            allowed_root_tags=set(args.root_tag),
            min_bytes=args.min_bytes,
            mtime_after=args.mtime_after,
        )
    except ArtifactValidationError as exc:
        _emit_error(str(exc))
        return 1

    print(f"Validated {args.label}: {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
