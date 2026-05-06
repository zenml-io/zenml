#!/usr/bin/env python3
"""Audit integration tests for workspace-safety classification."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

INTEGRATION_ROOT = Path("tests/integration")
BASELINE_PATH = Path(".github/workspace-safety-baseline.txt")


def _is_global_state_marker(node: ast.AST) -> bool:
    """Return whether an AST node is a pytest global_state marker."""
    if isinstance(node, ast.Attribute):
        return node.attr == "global_state"
    if isinstance(node, ast.Call):
        return _is_global_state_marker(node.func)
    return False


def _decorators_include_global_state(
    node: ast.FunctionDef | ast.ClassDef,
) -> bool:
    """Return whether a function or class has the global_state marker."""
    return any(
        _is_global_state_marker(decorator) for decorator in node.decorator_list
    )


def _module_has_global_state_marker(tree: ast.Module) -> bool:
    """Return whether a module marks all tests as global-state tests."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "pytestmark":
                value = node.value
                values = value.elts if isinstance(value, ast.List) else [value]
                return any(_is_global_state_marker(item) for item in values)
    return False


def _test_uses_workspace_fixture(node: ast.FunctionDef) -> bool:
    """Return whether a test function requests the workspace fixture."""
    return any(arg.arg == "zenml_workspace" for arg in node.args.args)


def _iter_unclassified_tests(root: Path) -> list[str]:
    """List tests without a workspace fixture or global-state marker."""
    unclassified: list[str] = []
    for path in sorted(root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_is_global_state = _module_has_global_state_marker(tree)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith(
                "test_"
            ):
                if module_is_global_state or _decorators_include_global_state(
                    node
                ):
                    continue
                if not _test_uses_workspace_fixture(node):
                    unclassified.append(f"{path}::{node.name}")
                continue

            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                class_is_global_state = _decorators_include_global_state(node)
                for item in node.body:
                    if not isinstance(item, ast.FunctionDef):
                        continue
                    if not item.name.startswith("test_"):
                        continue
                    if (
                        module_is_global_state
                        or class_is_global_state
                        or _decorators_include_global_state(item)
                    ):
                        continue
                    if not _test_uses_workspace_fixture(item):
                        unclassified.append(
                            f"{path}::{node.name}::{item.name}"
                        )
    return unclassified


def _read_baseline(path: Path) -> set[str]:
    """Read a newline-delimited baseline file."""
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    unclassified = _iter_unclassified_tests(INTEGRATION_ROOT)
    if args.write_baseline:
        BASELINE_PATH.write_text(
            "# Integration tests grandfathered before workspace-safety audit.\n"
            + "\n".join(unclassified)
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {len(unclassified)} baseline entries to {BASELINE_PATH}")
        return

    baseline = _read_baseline(BASELINE_PATH)
    new_unclassified = [item for item in unclassified if item not in baseline]

    print(f"Unclassified integration tests: {len(unclassified)}")
    print(f"New unclassified integration tests: {len(new_unclassified)}")
    if args.enforce and new_unclassified:
        for item in new_unclassified:
            print(
                f"::error::{item} must use zenml_workspace or "
                "@pytest.mark.global_state"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
