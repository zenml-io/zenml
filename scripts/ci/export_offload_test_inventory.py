#!/usr/bin/env python3
"""Export pytest collection inventory for CI offload coverage."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import tomllib

DEFAULT_CONFIG = Path("offload.toml")
MODAL_MYSQL_CONFIG = Path("offload-modal-server-mysql.toml")


@dataclass(frozen=True)
class OffloadInventory:
    """Collected offload coverage inventory."""

    default_integration_selected: list[str]
    modal_mysql_integration_selected: list[str]
    excluded_from_modal_mysql_vs_default: list[str]
    modal_mysql_examples_excluded: list[str]
    modal_mysql_global_state_excluded: list[str]
    default_explicit_deselections: list[str]
    modal_mysql_explicit_deselections: list[str]


def _load_filter_args(config_path: Path, group: str) -> list[str]:
    """Load pytest filter arguments from an offload TOML group."""
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    filters = config["groups"][group]["filters"]
    return shlex.split(filters)


def _explicit_deselections(args: list[str]) -> list[str]:
    """Return node IDs named by --deselect arguments."""
    deselections: list[str] = []
    iterator = iter(args)
    for arg in iterator:
        if arg == "--deselect":
            deselections.append(next(iterator))
        elif arg.startswith("--deselect="):
            deselections.append(arg.split("=", 1)[1])
    return sorted(deselections)


def _collect_node_ids(args: list[str]) -> list[str]:
    """Collect pytest node IDs for the supplied pytest arguments."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:pytest_postgresql",
        "--collect-only",
        "-q",
        *args,
    ]
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "pytest collection failed with exit code "
            f"{result.returncode}:\n{result.stdout}"
        )

    return sorted(
        line.strip()
        for line in result.stdout.splitlines()
        if "::" in line and not line.startswith("<")
    )


def build_inventory(
    *,
    default_config: Path = DEFAULT_CONFIG,
    modal_mysql_config: Path = MODAL_MYSQL_CONFIG,
) -> OffloadInventory:
    """Build an inventory for default and Modal/MySQL offload coverage."""
    default_args = _load_filter_args(default_config, "integration")
    modal_args = _load_filter_args(modal_mysql_config, "integration")

    default_selected = _collect_node_ids(default_args)
    modal_selected = _collect_node_ids(modal_args)
    example_nodes = _collect_node_ids(
        ["tests/integration/examples", "-m", "not slow"]
    )
    global_state_nodes = _collect_node_ids(
        ["tests/integration", "-m", "not slow and global_state"]
    )

    modal_selected_set = set(modal_selected)
    return OffloadInventory(
        default_integration_selected=default_selected,
        modal_mysql_integration_selected=modal_selected,
        excluded_from_modal_mysql_vs_default=sorted(
            set(default_selected) - modal_selected_set
        ),
        modal_mysql_examples_excluded=sorted(
            node for node in example_nodes if node not in modal_selected_set
        ),
        modal_mysql_global_state_excluded=sorted(
            node
            for node in global_state_nodes
            if node not in modal_selected_set
        ),
        default_explicit_deselections=_explicit_deselections(default_args),
        modal_mysql_explicit_deselections=_explicit_deselections(modal_args),
    )


def _print_section(title: str, nodes: list[str]) -> None:
    """Print a markdown section with node IDs."""
    print(f"## {title}")
    print()
    print(f"Count: {len(nodes)}")
    print()
    for node in nodes:
        print(f"- `{node}`")
    print()


def print_markdown(inventory: OffloadInventory) -> None:
    """Print a markdown inventory report."""
    print_summary(inventory)
    _print_section(
        "Default-Selected Nodes Excluded From Modal/MySQL",
        inventory.excluded_from_modal_mysql_vs_default,
    )
    _print_section(
        "Default Integration Nodes Selected",
        inventory.default_integration_selected,
    )
    _print_section(
        "Modal/MySQL Integration Nodes Selected",
        inventory.modal_mysql_integration_selected,
    )


def print_summary(inventory: OffloadInventory) -> None:
    """Print a compact markdown inventory summary."""
    print("# Offload Test Coverage Inventory")
    print()
    print("| Category | Count |")
    print("| --- | ---: |")
    print(
        "| Default integration nodes selected | "
        f"{len(inventory.default_integration_selected)} |"
    )
    print(
        "| Modal/MySQL integration nodes selected | "
        f"{len(inventory.modal_mysql_integration_selected)} |"
    )
    print(
        "| Default-selected nodes excluded from Modal/MySQL | "
        f"{len(inventory.excluded_from_modal_mysql_vs_default)} |"
    )
    print(
        "| Example nodes excluded from Modal/MySQL | "
        f"{len(inventory.modal_mysql_examples_excluded)} |"
    )
    print(
        "| Global-state nodes excluded from Modal/MySQL | "
        f"{len(inventory.modal_mysql_global_state_excluded)} |"
    )
    print()
    _print_section(
        "Default Explicit Deselections",
        inventory.default_explicit_deselections,
    )
    _print_section(
        "Modal/MySQL Explicit Deselections",
        inventory.modal_mysql_explicit_deselections,
    )
    _print_section(
        "Example Nodes Excluded From Modal/MySQL",
        inventory.modal_mysql_examples_excluded,
    )
    _print_section(
        "Global-State Nodes Excluded From Modal/MySQL",
        inventory.modal_mysql_global_state_excluded,
    )


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--default-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--modal-mysql-config", type=Path, default=MODAL_MYSQL_CONFIG
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print counts and intentional exclusion lists only.",
    )
    args = parser.parse_args()

    inventory = build_inventory(
        default_config=args.default_config,
        modal_mysql_config=args.modal_mysql_config,
    )
    if args.json:
        print(json.dumps(asdict(inventory), indent=2, sort_keys=True))
    elif args.summary:
        print_summary(inventory)
    else:
        print_markdown(inventory)


if __name__ == "__main__":
    main()
