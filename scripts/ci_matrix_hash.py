#!/usr/bin/env python3
"""Compute a deterministic hash for CI matrix definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _strip_yaml_comment(line: str) -> str:
    """Strip comments without treating quoted # characters as comments."""
    quote: str | None = None
    output: list[str] = []

    for index, character in enumerate(line):
        if character in {"'", '"'}:
            if quote == character:
                quote = None
            elif quote is None:
                quote = character

        if (
            character == "#"
            and quote is None
            and (index == 0 or line[index - 1].isspace())
        ):
            break

        output.append(character)

    return "".join(output).rstrip()


def _canonicalize_yaml_lines(lines: list[str]) -> str:
    """Normalize indentation and comments for a small YAML subtree."""
    canonical_lines: list[str] = []
    indent_stack = [0]

    for line in lines:
        line = _strip_yaml_comment(line)
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        while indent < indent_stack[-1]:
            indent_stack.pop()
        if indent > indent_stack[-1]:
            indent_stack.append(indent)

        level = len(indent_stack) - 1
        canonical_lines.append(f"{'  ' * level}{line.strip()}")

    return "\n".join(canonical_lines)


def _parent_job_name(
    lines: list[str], strategy_index: int, indent: int
) -> str:
    """Return the job key that owns a strategy block."""
    for line in reversed(lines[:strategy_index]):
        stripped = _strip_yaml_comment(line).strip()
        if not stripped:
            continue

        line_indent = len(line) - len(line.lstrip(" "))
        if line_indent < indent and stripped.endswith(":"):
            return stripped[:-1]

    return f"strategy-at-line-{strategy_index + 1}"


def _extract_strategy_blocks(workflow_text: str) -> list[dict[str, str]]:
    """Extract canonical matrix-bearing strategy blocks."""
    lines = workflow_text.splitlines()
    blocks: list[dict[str, str]] = []

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

        blocks.append(
            {
                "job": _parent_job_name(lines, index, indent),
                "strategy": _canonicalize_yaml_lines(block),
            }
        )

    return sorted(blocks, key=lambda block: block["job"])


def compute_matrix_hash_from_text(workflow_text: str) -> str:
    """Compute the SHA256 hash for matrix-bearing strategy blocks."""
    blocks = _extract_strategy_blocks(workflow_text)
    payload = json.dumps(blocks, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_matrix_hash(workflow: Path) -> str:
    """Compute the SHA256 hash for a workflow file's strategy blocks."""
    return compute_matrix_hash_from_text(workflow.read_text(encoding="utf-8"))


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
