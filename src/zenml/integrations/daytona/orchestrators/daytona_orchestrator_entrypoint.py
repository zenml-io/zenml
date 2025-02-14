#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Entrypoint of the Daytona orchestrator."""

import argparse
import os

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.orchestrators.dag_runner import ThreadedDagRunner

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--deployment_id", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the Daytona orchestrator.

    This is responsible for running the pipeline steps in the Daytona workspace.
    """
    logger.info("Daytona orchestrator started.")

    # Parse arguments
    args = parse_args()

    # Get deployment
    deployment = Client().get_deployment(args.deployment_id)

    # Create DAG of steps
    pipeline_dag = {
        step_name: step.spec.upstream_steps
        for step_name, step in deployment.step_configurations.items()
    }

    def run_step(step_name: str) -> None:
        """Run a pipeline step.

        Args:
            step_name: Name of the step to run.
        """
        logger.info(f"Running step: {step_name}")

        # Get the entrypoint command and arguments
        entrypoint_command = " ".join(
            StepEntrypointConfiguration.get_entrypoint_command()
        )
        entrypoint_args = " ".join(
            StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name,
                deployment_id=args.deployment_id,
            )
        )

        # Run the step
        command = f"{entrypoint_command} {entrypoint_args}"
        logger.info(f"Executing command: {command}")
        os.system(command)

    # Run the DAG
    ThreadedDagRunner(dag=pipeline_dag, run_fn=run_step).run()

    logger.info("Pipeline execution completed.")


if __name__ == "__main__":
    main()
