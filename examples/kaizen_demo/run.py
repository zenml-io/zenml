# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run the inventory and customer operations pipelines."""

import argparse
from typing import Any

from scenario_01.pipeline import inventory_report
from scenario_02.pipeline import customer_scoring
from scenario_03.pipelines import customer_risk_training
from scenario_04.pipeline import replenishment_planning


def main() -> None:
    """Parse the requested operation and execute its pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser(
        "inventory", help="Create an inventory report."
    )
    inventory.add_argument("--batch-size", type=int, default=12)
    inventory.add_argument("--source-seed", type=int, default=42)
    inventory.add_argument("--reorder-level", type=int, default=15)
    customers = commands.add_parser(
        "customers", help="Score a customer export."
    )
    customers.add_argument("--source-uri", required=True)
    training = commands.add_parser(
        "train-risk", help="Train the customer risk model."
    )
    training.add_argument("--sample-count", type=int, default=320)
    training.add_argument("--random-seed", type=int, default=41)
    replenishment = commands.add_parser(
        "replenishment", help="Plan warehouse replenishment."
    )
    replenishment.add_argument("--batch-size", type=int, default=12)
    replenishment.add_argument("--source-seed", type=int, default=73)
    replenishment.add_argument("--minimum-stock", type=int, default=20)
    for command in (inventory, customers, training, replenishment):
        command.add_argument("--run-name", help="Name for this execution.")
        command.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    options: dict[str, Any] = {}
    if args.run_name:
        options["run_name"] = args.run_name
    if args.no_cache:
        options["enable_cache"] = False
    if args.command == "inventory":
        run = inventory_report.with_options(**options)(
            batch_size=args.batch_size,
            source_seed=args.source_seed,
            reorder_level=args.reorder_level,
        )
    elif args.command == "customers":
        run = customer_scoring.with_options(**options)(
            source_uri=args.source_uri
        )
    elif args.command == "train-risk":
        run = customer_risk_training.with_options(**options)(
            sample_count=args.sample_count, random_seed=args.random_seed
        )
    else:
        run = replenishment_planning.with_options(**options)(
            batch_size=args.batch_size,
            source_seed=args.source_seed,
            minimum_stock=args.minimum_stock,
        )
    print(f"Run {run.id}: {run.status}")


if __name__ == "__main__":
    main()
