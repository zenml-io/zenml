"""Build a polished, multi-signal operations control-tower brief."""

from datetime import date, timedelta
from random import Random
from typing import Annotated

from zenml import log_metadata, pipeline, step
from zenml.types import HTMLString

from .reports import render_control_tower


@step
def create_operations_snapshot(
    sample_count: int = 240, random_seed: int = 2026
) -> Annotated[list[dict[str, float | int | str]], "operations_snapshot"]:
    """Generate a reproducible customer, inventory, and warehouse snapshot.

    Args:
        sample_count: Number of synthetic customer observations.
        random_seed: Seed for the synthetic snapshot.

    Returns:
        Records containing the signals needed by the control tower.

    Raises:
        ValueError: If sample_count is not positive.
    """
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    rng = Random(random_seed)
    records = []
    for index in range(sample_count):
        stock = rng.randint(4, 52)
        demand = rng.randint(8, 42)
        records.append(
            {
                "customer_id": f"C-{index + 1:04d}",
                "basket_value": round(rng.uniform(35, 260), 2),
                "converted": int(rng.random() < 0.31 + (index % 7) * 0.006),
                "stock_on_hand": stock,
                "weekly_demand": demand,
                "warehouse_capacity": rng.randint(62, 94),
            }
        )
    log_metadata(
        {
            "record_count": len(records),
            "data_origin": "synthetic",
            "random_seed": random_seed,
            "signals": ["customer_conversion", "inventory_cover", "warehouse_capacity"],
        }
    )
    return records


@step
def analyze_operations(
    records: list[dict[str, float | int | str]],
) -> tuple[
    Annotated[dict[str, float | int], "operations_metrics"],
    Annotated[list[dict[str, str | int]], "operations_alerts"],
]:
    """Turn raw signals into prioritized operating metrics and actions.

    Args:
        records: Synthetic customer, inventory, and warehouse records.

    Returns:
        A metrics dictionary and a short prioritized action queue.
    """
    total_value = sum(float(record["basket_value"]) for record in records)
    conversion_rate = 100 * sum(int(record["converted"]) for record in records) / len(records)
    stockout_rate = 100 * sum(
        int(float(record["stock_on_hand"]) < float(record["weekly_demand"]))
        for record in records
    ) / len(records)
    capacity = sum(int(record["warehouse_capacity"]) for record in records) / len(records)
    revenue_at_risk = total_value * conversion_rate / 100 * stockout_rate / 100
    readiness = max(0.0, min(100.0, 100 - stockout_rate * 0.8 - max(0, capacity - 78) * 0.35))
    metrics: dict[str, float | int] = {
        "revenue_at_risk": round(revenue_at_risk, 2),
        "conversion_rate": round(conversion_rate, 2),
        "stockout_risk": round(stockout_rate, 2),
        "readiness_score": round(readiness, 2),
        "customers_scored": len(records),
    }
    alerts: list[dict[str, str | int]] = [
        {
            "severity": "high",
            "title": "Protect high-value baskets",
            "action": "Reserve replenishment stock for at-risk demand lanes.",
            "impact": f"${revenue_at_risk:,.0f}",
        },
        {
            "severity": "medium",
            "title": "Rebalance warehouse capacity",
            "action": "Shift inbound slots before the next demand cycle.",
            "impact": f"{capacity:.0f}% full",
        },
        {
            "severity": "low",
            "title": "Nudge the conversion cohort",
            "action": "Queue a follow-up for undecided customers.",
            "impact": f"{100 - conversion_rate:.1f}%",
        },
    ]
    log_metadata(metrics)
    return metrics, alerts


@step(enable_cache=False)
def publish_control_tower(
    metrics: dict[str, float | int],
    alerts: list[dict[str, str | int]],
    run_date: str,
) -> Annotated[HTMLString, "control_tower_brief"]:
    """Publish the executive HTML brief as a first-class ZenML artifact.

    Args:
        metrics: Aggregated operating metrics.
        alerts: Prioritized actions.
        run_date: Date represented by the synthetic snapshot.

    Returns:
        A self-contained HTML control-tower report.
    """
    log_metadata({"report_date": run_date, "alert_count": len(alerts), **metrics})
    return HTMLString(render_control_tower(metrics, alerts, run_date))


@pipeline
def operations_control_tower(
    sample_count: int = 240,
    random_seed: int = 2026,
    run_date: str | None = None,
) -> None:
    """Create a decision-ready operations brief from three signal families.

    Args:
        sample_count: Number of synthetic customer observations.
        random_seed: Seed for reproducible demo data.
        run_date: Date represented by the report, defaulting to today.
    """
    records = create_operations_snapshot(sample_count, random_seed)
    metrics, alerts = analyze_operations(records)
    publish_control_tower(metrics, alerts, run_date or date.today().isoformat())
