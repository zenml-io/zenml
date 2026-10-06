#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Plan warehouse replenishment from available stock and stocking policy."""

from random import Random
from typing import Annotated

from build_settings import create_docker_settings

from zenml import log_metadata, pipeline, step


@step
def load_warehouse_inventory(
    batch_size: int, source_seed: int
) -> Annotated[list[dict[str, int]], "warehouse_inventory"]:
    """Generate a reproducible warehouse stock sample.

    Args:
        batch_size: Number of warehouse items.
        source_seed: Seed used to generate available quantities.

    Returns:
        Item identifiers and available units.

    Raises:
        ValueError: If the batch size is not positive.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")
    random = Random(source_seed)
    records = [
        {"item_id": index + 1, "available_units": random.randint(0, 30)}
        for index in range(batch_size)
    ]
    log_metadata({"item_count": len(records), "source_seed": source_seed})
    return records


@step(enable_cache=False)
def plan_replenishment(
    records: list[dict[str, int]], minimum_stock: int
) -> tuple[
    Annotated[list[dict[str, int]], "replenishment_orders"],
    Annotated[dict[str, int], "planning_summary"],
]:
    """Calculate itemized orders and summarize the stocking policy.

    Args:
        records: Warehouse items and available quantities.
        minimum_stock: Target quantity for each warehouse item.

    Returns:
        Itemized replenishment orders and aggregate planning totals.

    Raises:
        ValueError: If the minimum stock is negative.
    """
    if minimum_stock < 0:
        raise ValueError("minimum_stock must not be negative.")
    orders = [
        {
            **record,
            "target_units": minimum_stock,
            "order_units": minimum_stock - record["available_units"],
        }
        for record in records
        if record["available_units"] < minimum_stock
    ]
    summary = {
        "item_count": len(records),
        "available_units": sum(row["available_units"] for row in records),
        "replenishment_item_count": len(orders),
        "replenishment_units": sum(row["order_units"] for row in orders),
        "minimum_stock": minimum_stock,
    }
    log_metadata(summary)
    return orders, summary


@pipeline(settings={"docker": create_docker_settings()})
def replenishment_planning(
    batch_size: int = 12, source_seed: int = 73, minimum_stock: int = 20
) -> dict[str, int]:
    """Plan replenishment for a reproducible warehouse inventory.

    Args:
        batch_size: Number of warehouse items.
        source_seed: Seed used to generate available quantities.
        minimum_stock: Target quantity for each warehouse item.

    Returns:
        Aggregate quantities, order counts, and the effective stocking policy.
    """
    records = load_warehouse_inventory(
        batch_size=batch_size, source_seed=source_seed
    )
    _, summary = plan_replenishment(
        records=records, minimum_stock=minimum_stock
    )
    return summary
