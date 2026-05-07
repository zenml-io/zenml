"""Normalize pytest JUnit testcase names for offload duration lookup."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _node_id_from_pytest_junit(classname: str, name: str) -> str | None:
    parts = classname.split(".")
    module_end = next(
        (
            index
            for index, part in enumerate(parts)
            if part.startswith("test_")
        ),
        None,
    )
    if module_end is None:
        return None

    module_parts = parts[: module_end + 1]
    class_parts = parts[module_end + 1 :]
    path = "/".join(module_parts) + ".py"
    return "::".join([path, *class_parts, name])


def normalize_junit(path: Path) -> int:
    """Rewrite testcase names to pytest node IDs and return changed count."""
    tree = ET.parse(path)
    root = tree.getroot()
    changed = 0

    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname")
        name = testcase.attrib.get("name")
        if not classname or not name:
            continue
        node_id = _node_id_from_pytest_junit(classname, name)
        if node_id is None or node_id == name:
            continue
        testcase.set("name", node_id)
        changed += 1

    if changed:
        tree.write(path, encoding="utf-8", xml_declaration=True)
    return changed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    if not args.path.exists():
        print(f"JUnit file does not exist: {args.path}")
        return 0
    changed = normalize_junit(args.path)
    print(f"Normalized {changed} JUnit testcase names in {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
