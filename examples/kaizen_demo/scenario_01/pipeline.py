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

"""Summarize stock levels and replenishment requirements."""

from random import Random
from typing import Annotated

from zenml import log_metadata, pipeline, step


@step
def load_inventory(
    batch_size: int, source_seed: int
) -> Annotated[list[dict[str, int]], "inventory_records"]:
    """Build a reproducible inventory dataset.

    Args:
        batch_size: Number of products to include.
        source_seed: Seed used to generate stock levels and unit costs.

    Returns:
        Product identifiers, quantities, and unit costs in cents.

    Raises:
        ValueError: If the batch size is not positive.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")

    random = Random(source_seed)
    records = [
        {
            "product_id": index + 1,
            "quantity": random.randint(0, 40),
            "unit_cost_cents": random.randint(100, 2500),
        }
        for index in range(batch_size)
    ]
    log_metadata({"record_count": len(records), "source_seed": source_seed})
    return records


@step(enable_cache=False)
def summarize_inventory(
    records: list[dict[str, int]], reorder_level: int
) -> Annotated[dict[str, int], "report"]:
    """Calculate inventory value and replenishment quantities.

    Args:
        records: Products with quantities and unit costs in cents.
        reorder_level: Minimum target quantity for each product.

    Returns:
        Product counts, available stock, inventory value, and reorder totals.

    Raises:
        ValueError: If the reorder level is negative.
    """
    if reorder_level < 0:
        raise ValueError("reorder_level must not be negative.")

    report = {
        "product_count": len(records),
        "total_units": sum(record["quantity"] for record in records),
        "inventory_value_cents": sum(
            record["quantity"] * record["unit_cost_cents"]
            for record in records
        ),
        "out_of_stock_count": sum(
            record["quantity"] == 0 for record in records
        ),
        "reorder_count": sum(
            record["quantity"] < reorder_level for record in records
        ),
        "reorder_units": sum(
            max(0, reorder_level - record["quantity"]) for record in records
        ),
    }
    log_metadata(report)
    return report


@pipeline(enable_cache=True)
def inventory_report(
    batch_size: int = 12, source_seed: int = 42, reorder_level: int = 15
) -> None:
    """Create an inventory report for a product batch.

    Args:
        batch_size: Number of products to include.
        source_seed: Seed used to generate stock levels and unit costs.
        reorder_level: Minimum target quantity for each product.
    """
    records = load_inventory(batch_size=batch_size, source_seed=source_seed)
    summarize_inventory(records=records, reorder_level=reorder_level)
