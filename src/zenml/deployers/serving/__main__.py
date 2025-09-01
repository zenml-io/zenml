#!/usr/bin/env python3

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
"""ZenML Pipeline Serving Main Entry Point.

This module provides the main entry point for ZenML pipeline serving.

Usage (via entrypoint configuration):
    python -m zenml.deployers.serving --deployment_id <ID> --host 0.0.0.0 --port 8001
"""

import argparse
import logging
import sys

from zenml.entrypoints.base_entrypoint_configuration import (
    ENTRYPOINT_CONFIG_SOURCE_OPTION,
    BaseEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


def _setup_logging() -> None:
    """Set up logging for the serving entrypoint."""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)


def main() -> None:
    """Main entry point for pipeline serving."""
    _setup_logging()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="ZenML Pipeline Serving",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add entrypoint configuration option (modern pattern)
    parser.add_argument(
        f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
        help="Source path to entrypoint configuration class",
    )

    parser.add_argument(
        "--deployment_id", help="Pipeline deployment ID to serve"
    )
    parser.add_argument("--host", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument(
        "--port", type=int, help="Port to bind to (default: 8001)"
    )
    parser.add_argument(
        "--workers", type=int, help="Number of workers (default: 1)"
    )
    parser.add_argument("--log_level", help="Log level (default: info)")
    parser.add_argument("--create_runs", help="Create ZenML runs for tracking")

    args = parser.parse_args()

    # Load the entrypoint configuration class
    entrypoint_config_class = source_utils.load_and_validate_class(
        args.entrypoint_config_source,
        expected_class=BaseEntrypointConfiguration,
    )

    # Create and run the entrypoint configuration
    remaining_args = []
    for key, value in vars(args).items():
        if key != "entrypoint_config_source" and value is not None:
            remaining_args.extend([f"--{key}", str(value)])

    entrypoint_config = entrypoint_config_class(arguments=remaining_args)
    entrypoint_config.run()


if __name__ == "__main__":
    main()
