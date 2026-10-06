# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Summarize synthetic daily stock movements and replenishment requirements."""

from datetime import date
from typing import Annotated

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from build_settings import create_docker_settings

from zenml import log_metadata, pipeline, step
from zenml.types import HTMLString

from .data import (
    generate_inventory,
    simulate_daily_inventory,
    simulate_inventory_history,
)

INVENTORY_SOURCE_VERSION = "inventory-catalog-v2"


@step
def load_inventory(
    batch_size: int, source_seed: int, source_version: str = INVENTORY_SOURCE_VERSION
) -> Annotated[list[dict[str, int | str]], "inventory_records"]:
    """Build a fixed catalog with synthetic inventory and demand parameters.

    Args:
        batch_size: Number of products to include.
        source_seed: Seed used to generate the catalog and demand parameters.

    Returns:
        Stable product identifiers, categories, starting stock, and unit costs.

    Raises:
        ValueError: If the batch size is not positive.
    """
    if source_version != INVENTORY_SOURCE_VERSION:
        raise ValueError("Unsupported inventory source version.")
    records = generate_inventory(batch_size, source_seed)
    log_metadata(
        {
            "record_count": len(records),
            "source_seed": source_seed,
            "data_origin": "synthetic",
        }
    )
    return records


@step(enable_cache=False)
def summarize_inventory(
    records: list[dict[str, int | str]],
    reorder_level: int,
    business_date: str,
    simulation_start_date: str,
) -> tuple[
    Annotated[dict[str, int | str], "report"],
    Annotated[list[dict[str, int | str]], "daily_inventory_records"],
    Annotated[HTMLString, "inventory_report_html"],
]:
    """Calculate stock movements for a synthetic business date.

    Args:
        records: Fixed product catalog with initial quantities and costs.
        reorder_level: Minimum target quantity for each product.
        business_date: ISO calendar date represented by the report.
        simulation_start_date: Date of the catalog's initial stock snapshot.

    Returns:
        Reconciled daily summary and itemized product-level stock movements.

    Raises:
        ValueError: If dates, catalog, or reorder level are invalid.
    """
    _, report = simulate_daily_inventory(
        records, business_date, simulation_start_date, reorder_level
    )
    history = simulate_inventory_history(
        records, business_date, simulation_start_date, reorder_level
    )
    report_html = _build_inventory_report(history, report, reorder_level)
    log_metadata(report)
    return report, history, HTMLString(report_html)


def _build_inventory_report(
    history: list[dict[str, int | str]],
    report: dict[str, int | str],
    reorder_level: int,
) -> str:
    """Build a self-contained interactive report from saved daily outputs.

    Args:
        history: Itemized historical inventory outputs.
        report: Summary for the final business date.
        reorder_level: Stock threshold shown on the histogram.

    Returns:
        A standalone Plotly HTML document.
    """
    latest_date = str(report["business_date"])
    latest = [row for row in history if row["business_date"] == latest_date]
    categories: dict[str, int] = {}
    for row in latest:
        category = str(row["category"])
        categories[category] = categories.get(category, 0) + int(
            row["closing_units"]
        )
    dates = sorted({str(row["business_date"]) for row in history})
    stock_by_date = [
        sum(
            int(row["closing_units"])
            for row in history
            if row["business_date"] == day
        )
        for day in dates
    ]
    receipts_by_date = [
        sum(
            int(row["received_units"])
            for row in history
            if row["business_date"] == day
        )
        for day in dates
    ]
    figure = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Closing stock distribution",
            "Stock by category",
            "Daily stock trend",
            "Daily replenishment",
        ),
        specs=[[{}, {}], [{}, {}]],
        horizontal_spacing=0.1,
        vertical_spacing=0.16,
    )
    figure.add_trace(
        go.Histogram(
            x=[int(row["closing_units"]) for row in latest],
            nbinsx=12,
            marker_color="#4f46e5",
            name="Closing stock",
        ),
        row=1,
        col=1,
    )
    figure.add_vline(
        x=reorder_level,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text="Reorder level",
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=list(categories),
            y=list(categories.values()),
            marker_color="#06b6d4",
            name="Units by category",
        ),
        row=1,
        col=2,
    )
    figure.add_trace(
        go.Scatter(
            x=dates,
            y=stock_by_date,
            mode="lines+markers",
            line=dict(color="#0f766e", width=3),
            name="Closing stock",
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=dates,
            y=receipts_by_date,
            marker_color="#f59e0b",
            name="Received units",
        ),
        row=2,
        col=2,
    )
    figure.update_layout(
        title=(
            f"Inventory health · {latest_date}"
            f"<br><sup>{report['product_count']} products · "
            f"{report['total_units']} closing units · "
            f"{report['reorder_count']} products below target</sup>"
        ),
        template="plotly_white",
        height=850,
        width=1250,
        hovermode="x unified",
        margin=dict(t=110, l=55, r=35, b=55),
        legend=dict(orientation="h", y=-0.08),
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(showgrid=True, gridcolor="#e5e7eb")
    return figure.to_html(full_html=True, include_plotlyjs=True)


@pipeline(enable_cache=True, settings={"docker": create_docker_settings()})
def inventory_report(
    batch_size: int = 60,
    source_seed: int = 42,
    reorder_level: int = 15,
    business_date: str | None = None,
    simulation_start_date: str = "2026-01-01",
) -> None:
    """Report a synthetic business day using a cached product catalog.

    Args:
        batch_size: Number of products to include.
        source_seed: Seed used to generate stock levels and unit costs.
        reorder_level: Minimum target quantity for each product.
        business_date: ISO business date, defaulting to the submission date.
        simulation_start_date: ISO date of the catalog's starting quantities.
    """
    records = load_inventory(
        batch_size=batch_size,
        source_seed=source_seed,
        source_version=INVENTORY_SOURCE_VERSION,
    )
    summarize_inventory(
        records=records,
        reorder_level=reorder_level,
        business_date=business_date or date.today().isoformat(),
        simulation_start_date=simulation_start_date,
    )
