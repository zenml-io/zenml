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
from uuid import UUID

from scenario_01.pipeline import inventory_report
from scenario_02.pipeline import customer_scoring
from scenario_03.pipelines import customer_risk_training
from scenario_04.pipeline import replenishment_planning
from scenario_05.pipelines import (
    customer_model_evaluation,
    customer_model_training,
)
from scenario_06.pipeline import customer_segment_training
from scenario_07.data import SOURCE_URI, TRAINING_PIPELINE
from scenario_07.pipelines import bike_demand_scoring, bike_demand_training

from zenml import Model
from zenml.client import Client
from zenml.enums import ExecutionStatus


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
    retention = commands.add_parser(
        "train-retention", help="Train a customer retention classifier."
    )
    retention.add_argument("--sample-count", type=int, default=400)
    retention.add_argument("--random-seed", type=int, default=23)
    evaluation = commands.add_parser(
        "evaluate-retention",
        help="Evaluate a customer retention training run.",
    )
    evaluation.add_argument("--training-run-id", required=True)
    segments = commands.add_parser(
        "train-segments", help="Train a customer segment classifier."
    )
    segments.add_argument("--cpu-count", type=int, default=4)
    segments.add_argument("--sample-count", type=int, default=480)
    segments.add_argument("--random-seed", type=int, default=29)
    bike_training = commands.add_parser(
        "train-bikes", help="Train and compare hourly bike demand models."
    )
    bike_training.add_argument("--model-version", required=True)
    bike_training.add_argument(
        "--model-variant",
        choices=("baseline", "gradient_boosting"),
        default="gradient_boosting",
    )
    bike_training.add_argument("--train-end", default="2012-07-01")
    bike_training.add_argument("--evaluation-end", default="2012-10-01")
    bike_scoring = commands.add_parser(
        "score-bikes",
        help="Score a historical day with an exact training run.",
    )
    bike_scoring.add_argument("--training-run-id", type=UUID, required=True)
    bike_scoring.add_argument("--scoring-date", default="2012-10-15")
    for command in (bike_training, bike_scoring):
        command.add_argument("--source-uri", default=SOURCE_URI)
        command.add_argument("--source-sha256")
    for command in (
        inventory,
        customers,
        training,
        replenishment,
        retention,
        evaluation,
        segments,
        bike_training,
        bike_scoring,
    ):
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
    elif args.command == "replenishment":
        run = replenishment_planning.with_options(**options)(
            batch_size=args.batch_size,
            source_seed=args.source_seed,
            minimum_stock=args.minimum_stock,
        )
    elif args.command == "train-retention":
        run = customer_model_training.with_options(**options)(
            sample_count=args.sample_count, random_seed=args.random_seed
        )
    elif args.command == "evaluate-retention":
        run = customer_model_evaluation.with_options(**options)(
            training_run_id=args.training_run_id
        )
    elif args.command == "train-segments":
        run = customer_segment_training.with_options(**options)(
            cpu_count=args.cpu_count,
            sample_count=args.sample_count,
            random_seed=args.random_seed,
        )
    elif args.command == "train-bikes":
        options["model"] = Model(
            name="bike-demand", version=args.model_version
        )
        run = bike_demand_training.with_options(**options)(
            model_version=args.model_version,
            model_variant=args.model_variant,
            source_uri=args.source_uri,
            source_sha256=args.source_sha256,
            train_end=args.train_end,
            evaluation_end=args.evaluation_end,
        )
    else:
        client = Client()
        training_run = client.get_pipeline_run(
            args.training_run_id, project=client.active_project.id
        )
        if (
            training_run.project.id != client.active_project.id
            or training_run.pipeline is None
            or training_run.pipeline.name != TRAINING_PIPELINE
            or training_run.status != ExecutionStatus.COMPLETED
            or training_run.model_version is None
            or training_run.model_version.model.name != "bike-demand"
        ):
            parser.error(
                "Select a completed bike training run with a model version in this project."
            )
        options["model"] = training_run.model_version.to_model_class()
        run = bike_demand_scoring.with_options(**options)(
            training_run_id=str(args.training_run_id),
            scoring_date=args.scoring_date,
            source_uri=args.source_uri,
            source_sha256=args.source_sha256,
        )
    print(f"Run {run.id}: {run.status}")


if __name__ == "__main__":
    main()
