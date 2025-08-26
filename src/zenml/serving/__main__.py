#!/usr/bin/env python3

#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
It supports both the modern entrypoint configuration pattern and legacy
environment variable configuration for backward compatibility.

Modern Usage (via entrypoint configuration):
    python -m zenml.serving --deployment_id <ID> --host 0.0.0.0 --port 8000

Legacy Usage (via environment variables):
    export ZENML_PIPELINE_DEPLOYMENT_ID=your-deployment-id
    python -m zenml.serving

Environment Variables (legacy mode):
    ZENML_PIPELINE_DEPLOYMENT_ID: Pipeline deployment ID to serve (required)
    ZENML_SERVICE_HOST: Host to bind to (default: 0.0.0.0)
    ZENML_SERVICE_PORT: Port to bind to (default: 8000)
    ZENML_SERVICE_WORKERS: Number of workers (default: 1)
    ZENML_LOG_LEVEL: Log level (default: INFO)
    ZENML_SERVING_CREATE_RUNS: Create ZenML runs for tracking (default: false)
"""

import argparse
import logging
import os
import sys
from typing import Optional

import uvicorn

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


def _run_with_entrypoint_config(args: argparse.Namespace) -> None:
    """Run serving using entrypoint configuration pattern.

    Args:
        args: Parsed command line arguments
    """
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


def _run_legacy_mode(
    deployment_id: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    workers: Optional[int] = None,
    log_level: Optional[str] = None,
) -> None:
    """Run serving using legacy environment variable configuration.

    Args:
        deployment_id: Pipeline deployment ID (overrides env var)
        host: Host to bind to (overrides env var)
        port: Port to bind to (overrides env var)
        workers: Number of workers (overrides env var)
        log_level: Log level (overrides env var)
    """
    # Check required deployment ID
    final_deployment_id = deployment_id or os.getenv(
        "ZENML_PIPELINE_DEPLOYMENT_ID"
    )
    if not final_deployment_id:
        logger.error(
            "❌ ZENML_PIPELINE_DEPLOYMENT_ID environment variable is required "
            "or pass --deployment_id argument"
        )
        logger.error(
            "Set it to the deployment ID of the pipeline you want to serve"
        )
        sys.exit(1)

    # Configuration from arguments or environment variables
    final_host = host or os.getenv("ZENML_SERVICE_HOST", "0.0.0.0")
    final_port = port or int(os.getenv("ZENML_SERVICE_PORT", "8000"))
    final_workers = workers or int(os.getenv("ZENML_SERVICE_WORKERS", "1"))
    final_log_level = (
        log_level or os.getenv("ZENML_LOG_LEVEL", "info")
    ).lower()

    # Set environment variable for the serving application
    os.environ["ZENML_PIPELINE_DEPLOYMENT_ID"] = final_deployment_id

    logger.info("🚀 Starting ZenML Pipeline Serving...")
    logger.info(f"   Deployment ID: {final_deployment_id}")
    logger.info(f"   Host: {final_host}")
    logger.info(f"   Port: {final_port}")
    logger.info(f"   Workers: {final_workers}")
    logger.info(f"   Log Level: {final_log_level}")
    logger.info("")
    logger.info(f"📖 API Documentation: http://{final_host}:{final_port}/docs")
    logger.info(f"🔍 Health Check: http://{final_host}:{final_port}/health")
    logger.info("")

    try:
        # Start the FastAPI server
        uvicorn.run(
            "zenml.serving.app:app",
            host=final_host,
            port=final_port,
            workers=final_workers,
            log_level=final_log_level,
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Serving stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start serving: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main entry point for pipeline serving.

    Supports both modern entrypoint configuration pattern and legacy
    environment variable configuration for backward compatibility.
    """
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

    # Add legacy serving options for backward compatibility
    parser.add_argument(
        "--deployment_id", help="Pipeline deployment ID to serve"
    )
    parser.add_argument("--host", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument(
        "--port", type=int, help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--workers", type=int, help="Number of workers (default: 1)"
    )
    parser.add_argument("--log_level", help="Log level (default: info)")
    parser.add_argument("--create_runs", help="Create ZenML runs for tracking")

    args = parser.parse_args()

    # Determine which mode to use
    if hasattr(
        args, ENTRYPOINT_CONFIG_SOURCE_OPTION.replace("-", "_")
    ) and getattr(args, ENTRYPOINT_CONFIG_SOURCE_OPTION.replace("-", "_")):
        # Modern entrypoint configuration pattern
        _run_with_entrypoint_config(args)
    else:
        # Legacy environment variable pattern
        _run_legacy_mode(
            deployment_id=args.deployment_id,
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level=args.log_level,
        )


if __name__ == "__main__":
    main()
