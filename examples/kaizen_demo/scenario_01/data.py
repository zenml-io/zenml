"""Generate a stable product catalog and coherent synthetic daily inventory."""

from datetime import date, timedelta
from hashlib import sha256
from random import Random

from pydantic import BaseModel, Field


class InventoryProduct(BaseModel):
    """A product's fixed opening stock, costs, and simulation parameters."""

    product_id: int = Field(ge=1)
    category: str
    initial_quantity: int = Field(ge=0)
    unit_cost_cents: int = Field(ge=0)
    typical_daily_demand: int = Field(ge=1)
    replenishment_weekday: int = Field(ge=0, le=6)
    replenishment_target: int = Field(ge=0)
    demand_seed: int = Field(ge=0)


def generate_inventory(
    batch_size: int, source_seed: int
) -> list[dict[str, int | str]]:
    """Create a reproducible catalog independent of the reporting date.

    Args:
        batch_size: Number of products to generate.
        source_seed: Seed for the fixed catalog and demand parameters.

    Returns:
        Product records with starting stock, costs, and demand characteristics.

    Raises:
        ValueError: If the batch size is not positive.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")
    random = Random(source_seed)
    categories = (
        "Beverages",
        "Snacks",
        "Pantry",
        "Household",
        "Personal care",
        "Office",
    )
    records = []
    for index in range(batch_size):
        daily_demand = random.randint(2, 10)
        product = InventoryProduct(
            product_id=index + 1,
            category=categories[index % len(categories)],
            initial_quantity=random.randint(8, 45),
            unit_cost_cents=random.randint(180, 3600),
            typical_daily_demand=daily_demand,
            replenishment_weekday=index % 5,
            replenishment_target=daily_demand * 5 + random.randint(5, 20),
            demand_seed=random.randrange(2**31),
        )
        records.append(product.model_dump())
    return records


def simulate_daily_inventory(
    records: list[dict[str, int | str]],
    business_date: str,
    simulation_start_date: str,
    reorder_level: int,
) -> tuple[list[dict[str, int | str]], dict[str, int | str]]:
    """Replay deterministic stock movements through one synthetic business day.

    Args:
        records: Stable product catalog with initial stock and demand rules.
        business_date: ISO calendar date represented by the output.
        simulation_start_date: ISO calendar date of the catalog's opening stock.
        reorder_level: Minimum desired closing quantity for each product.

    Returns:
        Itemized movements for the requested day and reconciled summary totals.

    Raises:
        ValueError: If dates, catalog, or reorder level are invalid.
    """
    selected, start = (
        date.fromisoformat(business_date),
        date.fromisoformat(simulation_start_date),
    )
    if (
        selected.isoformat() != business_date
        or start.isoformat() != simulation_start_date
    ):
        raise ValueError("Dates must use the YYYY-MM-DD format.")
    if selected < start:
        raise ValueError(
            "business_date must not precede simulation_start_date."
        )
    if reorder_level < 0:
        raise ValueError("reorder_level must not be negative.")
    products = [InventoryProduct.model_validate(record) for record in records]
    if not products or len(
        {product.product_id for product in products}
    ) != len(products):
        raise ValueError("The catalog must contain unique products.")
    closing = {
        product.product_id: product.initial_quantity for product in products
    }
    day = start
    daily_records: list[dict[str, int | str]] = []
    while day <= selected:
        daily_records = []
        for product in products:
            record = _simulate_product(
                product, day, closing[product.product_id], reorder_level
            )
            closing[product.product_id] = int(record["closing_units"])
            daily_records.append(record)
        day += timedelta(days=1)
    summary: dict[str, int | str] = {
        "business_date": business_date,
        "simulation_start_date": simulation_start_date,
        "data_origin": "synthetic",
        "product_count": len(daily_records),
        "total_units": sum(int(row["closing_units"]) for row in daily_records),
        "inventory_value_cents": sum(
            int(row["inventory_value_cents"]) for row in daily_records
        ),
        "out_of_stock_count": sum(
            row["closing_units"] == 0 for row in daily_records
        ),
        "reorder_count": sum(
            int(row["reorder_units"]) > 0 for row in daily_records
        ),
        "reorder_units": sum(
            int(row["reorder_units"]) for row in daily_records
        ),
        "opening_units": sum(
            int(row["opening_units"]) for row in daily_records
        ),
        "received_units": sum(
            int(row["received_units"]) for row in daily_records
        ),
        "demand_units": sum(int(row["demand_units"]) for row in daily_records),
        "sold_units": sum(int(row["sold_units"]) for row in daily_records),
        "unfulfilled_units": sum(
            int(row["unfulfilled_units"]) for row in daily_records
        ),
    }
    return daily_records, summary


def _simulate_product(
    product: InventoryProduct, day: date, opening: int, reorder_level: int
) -> dict[str, int | str]:
    """Calculate one product's deterministic receipts, sales, and closing stock.

    Args:
        product: Fixed product characteristics.
        day: Business date being simulated.
        opening: Closing stock carried forward from the previous day.
        reorder_level: Minimum desired closing quantity.

    Returns:
        The day's itemized stock movements and inventory value.
    """
    seed = int.from_bytes(
        sha256(f"{product.demand_seed}:{day.isoformat()}".encode()).digest()[
            :8
        ],
        "big",
    )
    random = Random(seed)
    weekday = day.weekday()
    demand_factor = (1.05, 1.0, 1.0, 1.1, 1.25, 0.8, 0.65)[weekday]
    if weekday >= 5 and product.category in {"Beverages", "Snacks"}:
        demand_factor = 1.2
    demand = round(
        product.typical_daily_demand * demand_factor * random.uniform(0.6, 1.4)
    )
    received = 0
    if weekday == product.replenishment_weekday:
        received = max(
            0,
            round(product.replenishment_target * random.uniform(0.85, 1.1))
            - opening,
        )
    sold = min(opening + received, demand)
    closing = opening + received - sold
    return {
        "business_date": day.isoformat(),
        "product_id": product.product_id,
        "category": product.category,
        "opening_units": opening,
        "received_units": received,
        "demand_units": demand,
        "sold_units": sold,
        "closing_units": closing,
        "unfulfilled_units": demand - sold,
        "unit_cost_cents": product.unit_cost_cents,
        "inventory_value_cents": closing * product.unit_cost_cents,
        "reorder_units": max(0, reorder_level - closing),
    }
