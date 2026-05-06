#!/usr/bin/env python3
"""Compute a deterministic hash for CI matrix definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _extract_strategy_blocks(workflow: Path) -> list[str]:
    """Extract strategy blocks without requiring a YAML parser in CI."""
    lines = workflow.read_text(encoding="utf-8").splitlines()
    blocks: list[str] = []

    for index, line in enumerate(lines):
        if line.strip() != "strategy:":
            continue

        indent = len(line) - len(line.lstrip(" "))
        block = [line[indent:]]
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                block.append("")
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip(" "))
            if candidate_indent <= indent:
                break
            block.append(candidate[indent:])
        blocks.append("\n".join(block).rstrip())

    return blocks


def compute_matrix_hash(workflow: Path) -> str:
    """Compute the SHA256 hash for matrix-bearing strategy blocks."""
    blocks = _extract_strategy_blocks(workflow)
    payload = json.dumps(blocks, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "workflow",
        nargs="?",
        default=".github/workflows/ci-slow-develop.yml",
    )
    args = parser.parse_args()
    print(compute_matrix_hash(Path(args.workflow)))


if __name__ == "__main__":
    main()
