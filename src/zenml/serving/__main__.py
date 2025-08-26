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
"""
ZenML Pipeline Serving Main Entry Point

This module allows running the pipeline serving FastAPI application directly
via `python -m zenml.serving` or as a standalone script.

Environment Variables:
    ZENML_PIPELINE_DEPLOYMENT_ID: Pipeline deployment ID to serve (required)
    ZENML_SERVICE_HOST: Host to bind to (default: 0.0.0.0)
    ZENML_SERVICE_PORT: Port to bind to (default: 8000)
    ZENML_SERVICE_WORKERS: Number of workers (default: 1)
    ZENML_LOG_LEVEL: Log level (default: INFO)
    ZENML_SERVING_CREATE_RUNS: Create ZenML runs for tracking (default: false)

Usage:
    # Set deployment ID and start serving
    export ZENML_PIPELINE_DEPLOYMENT_ID=your-deployment-id
    python -m zenml.serving
    
    # Or with custom configuration
    ZENML_SERVICE_PORT=8080 python -m zenml.serving
"""

import os
import sys

import uvicorn

from zenml.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for pipeline serving."""
    # Check required environment variables
    deployment_id = os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID")
    if not deployment_id:
        logger.error(
            "❌ ZENML_PIPELINE_DEPLOYMENT_ID environment variable is required"
        )
        logger.error(
            "Set it to the deployment ID of the pipeline you want to serve"
        )
        sys.exit(1)

    # Configuration from environment variables
    host = os.getenv("ZENML_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("ZENML_SERVICE_PORT", "8000"))
    workers = int(os.getenv("ZENML_SERVICE_WORKERS", "1"))
    log_level = os.getenv("ZENML_LOG_LEVEL", "info").lower()

    logger.info("🚀 Starting ZenML Pipeline Serving...")
    logger.info(f"   Deployment ID: {deployment_id}")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Workers: {workers}")
    logger.info(f"   Log Level: {log_level}")
    logger.info("")
    logger.info(f"📖 API Documentation: http://{host}:{port}/docs")
    logger.info(f"🔍 Health Check: http://{host}:{port}/health")
    logger.info("")

    try:
        # Start the FastAPI server
        uvicorn.run(
            "zenml.serving.app:app",
            host=host,
            port=port,
            workers=workers,
            log_level=log_level,
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Serving stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start serving: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
