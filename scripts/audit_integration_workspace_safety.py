#!/usr/bin/env python3
"""Audit integration tests for workspace-safety classification."""

from __future__ import annotations

import argparse
import ast
import subprocess
from pathlib import Path

INTEGRATION_ROOT = Path("tests/integration")
DEVELOP_REF = "origin/develop"


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


def _iter_unclassified_tests_from_sources(
    sources: dict[Path, str],
) -> list[str]:
    """List tests without a workspace fixture or global-state marker."""
    unclassified: list[str] = []
    for path, source in sorted(sources.items()):
        tree = ast.parse(source, filename=str(path))
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


def _iter_unclassified_tests(root: Path) -> list[str]:
    """List current unclassified integration tests."""
    sources = {
        path: path.read_text(encoding="utf-8")
        for path in root.rglob("test_*.py")
    }
    return _iter_unclassified_tests_from_sources(sources)


def _run_git(args: list[str]) -> str:
    """Run a git command and return stdout."""
    return subprocess.check_output(
        ["git", *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def _default_baseline_ref() -> str | None:
    """Return the merge base against develop when it is available."""
    for ref in (DEVELOP_REF, "develop"):
        try:
            return _run_git(["merge-base", "HEAD", ref])
        except subprocess.CalledProcessError:
            continue
    return None


def _read_baseline(ref: str | None) -> set[str]:
    """Read unclassified tests from a git ref instead of a static file."""
    if not ref:
        return set()

    try:
        files = _run_git(
            ["ls-tree", "-r", "--name-only", ref, str(INTEGRATION_ROOT)]
        ).splitlines()
    except subprocess.CalledProcessError:
        return set()

    sources: dict[Path, str] = {}
    for file_name in files:
        path = Path(file_name)
        if not path.name.startswith("test_") or path.suffix != ".py":
            continue
        try:
            sources[path] = _run_git(["show", f"{ref}:{file_name}"])
        except subprocess.CalledProcessError:
            continue
    return set(_iter_unclassified_tests_from_sources(sources))


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    unclassified = _iter_unclassified_tests(INTEGRATION_ROOT)
    baseline_ref = args.baseline_ref or _default_baseline_ref()
    baseline = _read_baseline(baseline_ref)
    new_unclassified = [item for item in unclassified if item not in baseline]

    print(f"Baseline ref: {baseline_ref or 'none'}")
    print(f"Baseline unclassified integration tests: {len(baseline)}")
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
