"""Build a self-contained operations command center from synthetic signals."""

from html import escape
from random import Random
from typing import Annotated

from build_settings import create_docker_settings

from zenml import log_metadata, pipeline, step
from zenml.types import HTMLString


@step
def measure_inventory_health(
    item_count: int, seed: int, reorder_level: int
) -> Annotated[list[dict[str, int | str]], "inventory_health"]:
    """Measure stock coverage and identify products at risk of a stockout.

    Args:
        item_count: Number of products in the simulated catalog.
        seed: Seed for reproducible observations.
        reorder_level: Minimum units considered healthy.

    Returns:
        Product-level stock health observations.

    Raises:
        ValueError: If any configuration value is invalid.
    """
    if item_count < 1:
        raise ValueError("item_count must be positive.")
    if reorder_level < 0:
        raise ValueError("reorder_level must not be negative.")

    random = Random(seed)
    records = []
    for product_id in range(1, item_count + 1):
        available = random.randint(0, max(1, reorder_level * 3))
        records.append(
            {
                "product_id": f"SKU-{product_id:03d}",
                "available_units": available,
                "reorder_units": max(0, reorder_level - available),
                "severity": "critical"
                if available < reorder_level // 2
                else "watch"
                if available < reorder_level
                else "healthy",
            }
        )
    at_risk = sum(row["severity"] != "healthy" for row in records)
    log_metadata(
        {
            "product_count": item_count,
            "at_risk_products": at_risk,
            "reorder_level": reorder_level,
            "signal": "inventory",
        }
    )
    return records


@step
def forecast_customer_demand(
    segment_count: int, seed: int
) -> Annotated[list[dict[str, int | str]], "customer_demand"]:
    """Create a short-horizon demand forecast for customer segments.

    Args:
        segment_count: Number of customer segments.
        seed: Seed for reproducible forecasts.

    Returns:
        Segment-level demand forecasts and momentum labels.

    Raises:
        ValueError: If segment_count is not positive.
    """
    if segment_count < 1:
        raise ValueError("segment_count must be positive.")

    random = Random(seed)
    records = []
    for segment_id in range(1, segment_count + 1):
        baseline = random.randint(30, 160)
        growth_percent = random.randint(-12, 35)
        records.append(
            {
                "segment": f"SEG-{segment_id:02d}",
                "baseline_orders": baseline,
                "forecast_orders": round(baseline * (1 + growth_percent / 100)),
                "growth_percent": growth_percent,
                "momentum": "surging"
                if growth_percent >= 20
                else "growing"
                if growth_percent >= 8
                else "stable"
                if growth_percent >= 0
                else "cooling",
            }
        )
    surging = sum(row["momentum"] == "surging" for row in records)
    log_metadata(
        {
            "segment_count": segment_count,
            "surging_segments": surging,
            "signal": "customer_demand",
        }
    )
    return records


@step
def assess_warehouse_capacity(
    warehouse_count: int, seed: int
) -> Annotated[list[dict[str, int | str]], "warehouse_capacity"]:
    """Assess warehouse capacity for the forecast planning horizon.

    Args:
        warehouse_count: Number of warehouses to simulate.
        seed: Seed for reproducible capacity observations.

    Returns:
        Warehouse utilization and available capacity observations.

    Raises:
        ValueError: If warehouse_count is not positive.
    """
    if warehouse_count < 1:
        raise ValueError("warehouse_count must be positive.")

    random = Random(seed)
    records = []
    for warehouse_id in range(1, warehouse_count + 1):
        capacity = random.randint(600, 1200)
        used = random.randint(round(capacity * 0.45), round(capacity * 0.96))
        utilization = round(100 * used / capacity)
        records.append(
            {
                "warehouse": f"WH-{warehouse_id:02d}",
                "capacity_units": capacity,
                "used_units": used,
                "available_units": capacity - used,
                "utilization_percent": utilization,
                "status": "constrained"
                if utilization >= 85
                else "watch"
                if utilization >= 70
                else "healthy",
            }
        )
    constrained = sum(row["status"] == "constrained" for row in records)
    log_metadata(
        {
            "warehouse_count": warehouse_count,
            "constrained_warehouses": constrained,
            "signal": "warehouse_capacity",
        }
    )
    return records


@step(enable_cache=False)
def build_action_board(
    inventory: list[dict[str, int | str]],
    demand: list[dict[str, int | str]],
    capacity: list[dict[str, int | str]],
) -> tuple[
    Annotated[list[dict[str, str | int]], "operations_actions"],
    Annotated[dict[str, int | str], "operations_summary"],
    Annotated[HTMLString, "operations_command_center"],
]:
    """Join the signals into prioritized actions and an HTML command center.

    Args:
        inventory: Product stock health observations.
        demand: Customer segment forecasts.
        capacity: Warehouse capacity observations.

    Returns:
        Prioritized action board, summary metrics, and a self-contained dashboard.
    """
    actions: list[dict[str, str | int]] = []
    for row in inventory:
        if row["severity"] != "healthy":
            actions.append(
                {
                    "priority": 1 if row["severity"] == "critical" else 2,
                    "owner": "Supply",
                    "action": f"Replenish {row['product_id']}",
                    "reason": f"{row['available_units']} units available",
                }
            )
    for row in demand:
        if row["momentum"] == "surging":
            actions.append(
                {
                    "priority": 1,
                    "owner": "Growth",
                    "action": f"Protect capacity for {row['segment']}",
                    "reason": f"{row['growth_percent']}% demand growth",
                }
            )
    for row in capacity:
        if row["status"] != "healthy":
            actions.append(
                {
                    "priority": 1 if row["status"] == "constrained" else 2,
                    "owner": "Fulfillment",
                    "action": f"Rebalance {row['warehouse']}",
                    "reason": f"{row['utilization_percent']}% utilized",
                }
            )
    actions.sort(key=lambda row: (row["priority"], row["owner"], row["action"]))
    summary: dict[str, int | str] = {
        "action_count": len(actions),
        "priority_one_actions": sum(row["priority"] == 1 for row in actions),
        "at_risk_products": sum(row["severity"] != "healthy" for row in inventory),
        "surging_segments": sum(row["momentum"] == "surging" for row in demand),
        "constrained_warehouses": sum(
            row["status"] == "constrained" for row in capacity
        ),
        "readiness": (
            "intervene now"
            if any(row["priority"] == 1 for row in actions)
            else "on track"
        ),
    }
    log_metadata(summary)

    action_rows = "".join(
        "<tr>"
        f"<td><b>P{row['priority']}</b></td><td>{escape(str(row['owner']))}</td>"
        f"<td>{escape(str(row['action']))}</td>"
        f"<td>{escape(str(row['reason']))}</td></tr>"
        for row in actions[:12]
    ) or "<tr><td colspan='4'>No interventions required.</td></tr>"
    dashboard = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Operations Command Center</title>
<style>body{{font:16px system-ui;background:#101827;color:#eef2ff;max-width:1100px;margin:40px auto;padding:0 24px}}h1{{color:#7dd3fc}}.grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:18px}}.value{{font-size:28px;font-weight:700;color:#fbbf24}}table{{width:100%;margin-top:24px;border-collapse:collapse;background:#1e293b}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #334155}}th{{color:#7dd3fc}}small{{color:#94a3b8}}</style></head>
<body><h1>⚡ Operations Command Center</h1><small>One joined view of synthetic inventory, demand, and warehouse signals.</small>
<div class='grid'>
<div class='card'>Readiness<div class='value'>{summary['readiness']}</div></div>
<div class='card'>Actions<div class='value'>{summary['action_count']}</div></div>
<div class='card'>Urgent<div class='value'>{summary['priority_one_actions']}</div></div>
<div class='card'>Stock risk<div class='value'>{summary['at_risk_products']}</div></div>
<div class='card'>Capacity risk<div class='value'>{summary['constrained_warehouses']}</div></div>
</div><h2>Prioritized action board</h2><table><tr><th>Priority</th><th>Owner</th><th>Action</th><th>Signal</th></tr>{action_rows}</table></body></html>"""
    return actions, summary, HTMLString(dashboard)


@pipeline(settings={"docker": create_docker_settings()})
def operations_command_center(
    item_count: int = 24,
    segment_count: int = 5,
    warehouse_count: int = 3,
    seed: int = 2026,
    reorder_level: int = 30,
) -> dict[str, int | str]:
    """Create a prioritized operations dashboard from parallel business signals.

    Args:
        item_count: Number of products in the inventory signal.
        segment_count: Number of customer segments in the demand signal.
        warehouse_count: Number of warehouses in the capacity signal.
        seed: Base seed for reproducible synthetic data.
        reorder_level: Minimum healthy inventory level.

    Returns:
        Summary metrics for the generated action board.
    """
    inventory = measure_inventory_health(item_count, seed, reorder_level)
    demand = forecast_customer_demand(segment_count, seed + 1)
    capacity = assess_warehouse_capacity(warehouse_count, seed + 2)
    _, summary, _ = build_action_board(inventory, demand, capacity)
    return summary
