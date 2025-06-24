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
"""Entrypoint of the Modal orchestrator sandbox."""

import argparse
import os

from zenml.entrypoints.pipeline_entrypoint_configuration import (
    PipelineEntrypointConfiguration,
)
from zenml.integrations.modal.utils import ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID
from zenml.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--orchestrator_run_id", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the Modal orchestrator sandbox."""
    # Log to the container's stdout so it can be streamed by Modal
    logger.info("Modal orchestrator sandbox started.")

    # Parse arguments
    args = parse_args()

    # Set the orchestrator run ID in the environment
    os.environ[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = args.orchestrator_run_id

    logger.info(f"Deployment ID: {args.deployment_id}")
    logger.info(f"Orchestrator Run ID: {args.orchestrator_run_id}")
    if args.run_id:
        logger.info(f"Pipeline Run ID: {args.run_id}")

    try:
        # Create the entrypoint arguments for pipeline execution
        entrypoint_args = (
            PipelineEntrypointConfiguration.get_entrypoint_arguments(
                deployment_id=args.deployment_id
            )
        )

        logger.info("Creating pipeline configuration")
        config = PipelineEntrypointConfiguration(arguments=entrypoint_args)

        logger.info("Executing entire pipeline")
        config.run()

        logger.info("Pipeline execution completed successfully")

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
