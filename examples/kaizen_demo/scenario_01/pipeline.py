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

from build_settings import create_docker_settings

from zenml import log_metadata, pipeline, step

from .data import generate_inventory, simulate_daily_inventory


@step
def load_inventory(
    batch_size: int, source_seed: int
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
    daily_records, report = simulate_daily_inventory(
        records, business_date, simulation_start_date, reorder_level
    )
    log_metadata(report)
    return report, daily_records


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
    records = load_inventory(batch_size=batch_size, source_seed=source_seed)
    summarize_inventory(
        records=records,
        reorder_level=reorder_level,
        business_date=business_date or date.today().isoformat(),
        simulation_start_date=simulation_start_date,
    )
