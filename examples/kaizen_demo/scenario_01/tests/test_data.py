"""Verify deterministic inventory history and reconciled stock movements."""

from copy import deepcopy
from datetime import date, timedelta

import pytest
from scenario_01.data import generate_inventory, simulate_daily_inventory


def test_catalog_is_reproducible_and_simulation_does_not_mutate_it() -> None:
    """Daily reporting must retain the same stable source catalog."""
    catalog = generate_inventory(60, 42)
    original = deepcopy(catalog)
    first = simulate_daily_inventory(catalog, "2026-09-15", "2026-09-01", 15)
    repeated = simulate_daily_inventory(
        catalog, "2026-09-15", "2026-09-01", 15
    )
    assert first == repeated
    assert catalog == original == generate_inventory(60, 42)
    assert len(catalog) == len({row["product_id"] for row in catalog}) == 60
    assert len({row["category"] for row in catalog}) == 6


def test_daily_history_preserves_stock_continuity_and_varies() -> None:
    """Each business day's opening stock must equal the prior day's close."""
    catalog = generate_inventory(60, 42)
    previous = {row["product_id"]: row["initial_quantity"] for row in catalog}
    total_series = []
    for offset in range(25):
        day = (date(2026, 9, 1) + timedelta(days=offset)).isoformat()
        rows, summary = simulate_daily_inventory(
            catalog, day, "2026-09-01", 15
        )
        assert {
            row["product_id"]: row["opening_units"] for row in rows
        } == previous
        previous = {row["product_id"]: row["closing_units"] for row in rows}
        assert summary["business_date"] == day
        assert summary["data_origin"] == "synthetic"
        assert all(row["business_date"] == day for row in rows)
        total_series.append((summary["total_units"], summary["sold_units"]))
    assert len(set(total_series)) > 20


def test_stock_movements_and_summary_totals_reconcile() -> None:
    """Receipts, demand, sales, stock value, and shortages must reconcile."""
    rows, summary = simulate_daily_inventory(
        generate_inventory(60, 42), "2026-09-13", "2026-09-01", 15
    )
    for row in rows:
        assert (
            row["opening_units"] + row["received_units"]
            == row["sold_units"] + row["closing_units"]
        )
        assert (
            row["demand_units"] == row["sold_units"] + row["unfulfilled_units"]
        )
        assert (
            row["inventory_value_cents"]
            == row["closing_units"] * row["unit_cost_cents"]
        )
        assert row["reorder_units"] == max(0, 15 - row["closing_units"])
        assert all(
            value >= 0 for value in row.values() if isinstance(value, int)
        )
    assert (
        summary["opening_units"] + summary["received_units"]
        == summary["sold_units"] + summary["total_units"]
    )
    assert (
        summary["demand_units"]
        == summary["sold_units"] + summary["unfulfilled_units"]
    )
    assert summary["total_units"] == sum(row["closing_units"] for row in rows)
    assert summary["inventory_value_cents"] == sum(
        row["inventory_value_cents"] for row in rows
    )
    assert summary["out_of_stock_count"] == sum(
        row["closing_units"] == 0 for row in rows
    )
    assert summary["reorder_count"] == sum(
        row["reorder_units"] > 0 for row in rows
    )


def test_product_order_does_not_change_the_simulated_outcomes() -> None:
    """Product identity must determine random demand independently of ordering."""
    catalog = generate_inventory(60, 42)
    rows, summary = simulate_daily_inventory(
        catalog, "2026-09-10", "2026-09-01", 15
    )
    reversed_rows, reversed_summary = simulate_daily_inventory(
        list(reversed(catalog)), "2026-09-10", "2026-09-01", 15
    )
    assert summary == reversed_summary
    assert rows == list(reversed(reversed_rows))


@pytest.mark.parametrize(
    "business_date,start_date,reorder_level",
    [
        ("2026-08-31", "2026-09-01", 15),
        ("2026-09-01", "2026-09-01", -1),
        ("20260901", "2026-09-01", 15),
    ],
)
def test_invalid_reporting_parameters_are_rejected(
    business_date: str, start_date: str, reorder_level: int
) -> None:
    """Reject ambiguous dates, backward history, and negative reorder targets.

    Args:
        business_date: Requested reporting date.
        start_date: Initial stock snapshot date.
        reorder_level: Minimum desired closing quantity.
    """
    with pytest.raises(ValueError):
        simulate_daily_inventory(
            generate_inventory(1, 42), business_date, start_date, reorder_level
        )


def test_duplicate_products_are_rejected() -> None:
    """Duplicate products must not double-count stock or demand."""
    catalog = generate_inventory(1, 42)
    with pytest.raises(ValueError, match="unique products"):
        simulate_daily_inventory(catalog * 2, "2026-09-01", "2026-09-01", 15)
