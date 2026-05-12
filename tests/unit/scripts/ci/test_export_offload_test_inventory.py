"""Tests for offload coverage inventory export."""

from __future__ import annotations

from pathlib import Path

from scripts.ci import export_offload_test_inventory as inventory


def test_explicit_deselections_accept_both_pytest_forms() -> None:
    """Inventory parsing accepts both supported --deselect forms."""
    assert inventory._explicit_deselections(
        [
            "tests/integration",
            "--deselect=tests/test_a.py::test_a",
            "--deselect",
            "tests/test_b.py::test_b",
        ]
    ) == [
        "tests/test_a.py::test_a",
        "tests/test_b.py::test_b",
    ]


def test_build_inventory_reports_modal_mysql_exclusions(
    tmp_path: Path, monkeypatch
) -> None:
    """Modal/MySQL inventory reports default, example, and global-state gaps."""
    default_config = tmp_path / "offload.toml"
    default_config.write_text(
        """
        [groups.integration]
        filters = "tests/integration -m 'not slow' --deselect=tests/integration/examples/test_xgboost.py::test_example"
        """
    )
    modal_config = tmp_path / "offload-modal-server-mysql.toml"
    modal_config.write_text(
        """
        [groups.integration]
        filters = "tests/integration --ignore=tests/integration/examples -m 'not slow and not global_state' --deselect=tests/integration/functional/test_state.py::test_serial"
        """
    )

    collections = {
        (
            "tests/integration",
            "-m",
            "not slow",
            "--deselect=tests/integration/examples/test_xgboost.py::test_example",
        ): [
            "tests/integration/functional/test_ok.py::test_ok",
            "tests/integration/functional/test_state.py::test_global",
            "tests/integration/examples/test_other.py::test_example",
        ],
        (
            "tests/integration",
            "--ignore=tests/integration/examples",
            "-m",
            "not slow and not global_state",
            "--deselect=tests/integration/functional/test_state.py::test_serial",
        ): [
            "tests/integration/functional/test_ok.py::test_ok",
        ],
        ("tests/integration/examples", "-m", "not slow"): [
            "tests/integration/examples/test_other.py::test_example",
            "tests/integration/examples/test_xgboost.py::test_example",
        ],
        ("tests/integration", "-m", "not slow and global_state"): [
            "tests/integration/functional/test_state.py::test_global",
        ],
    }

    def collect(args: list[str]) -> list[str]:
        return collections[tuple(args)]

    monkeypatch.setattr(inventory, "_collect_node_ids", collect)

    result = inventory.build_inventory(
        default_config=default_config,
        modal_mysql_config=modal_config,
    )

    assert result.default_integration_selected == [
        "tests/integration/functional/test_ok.py::test_ok",
        "tests/integration/functional/test_state.py::test_global",
        "tests/integration/examples/test_other.py::test_example",
    ]
    assert result.modal_mysql_integration_selected == [
        "tests/integration/functional/test_ok.py::test_ok",
    ]
    assert result.excluded_from_modal_mysql_vs_default == [
        "tests/integration/examples/test_other.py::test_example",
        "tests/integration/functional/test_state.py::test_global",
    ]
    assert result.modal_mysql_examples_excluded == [
        "tests/integration/examples/test_other.py::test_example",
        "tests/integration/examples/test_xgboost.py::test_example",
    ]
    assert result.modal_mysql_global_state_excluded == [
        "tests/integration/functional/test_state.py::test_global",
    ]
    assert result.default_explicit_deselections == [
        "tests/integration/examples/test_xgboost.py::test_example"
    ]
    assert result.modal_mysql_explicit_deselections == [
        "tests/integration/functional/test_state.py::test_serial"
    ]
