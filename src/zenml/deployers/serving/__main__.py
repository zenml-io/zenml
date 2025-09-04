"""Entry point for ZenML pipeline serving module."""

import argparse
import os

import uvicorn

from zenml.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for serving."""
    parser = argparse.ArgumentParser(
        description="ZenML Pipeline Serving Service"
    )
    # Handle both ZenML internal arguments and user arguments
    parser.add_argument(
        "--entrypoint_config_source",
        help="Entrypoint configuration source (for ZenML internal use)",
    )
    parser.add_argument(
        "--deployment_id",
        help="Pipeline deployment ID (ZenML internal format)",
    )
    parser.add_argument(
        "--deployment-id",
        dest="deployment_id",
        help="Pipeline deployment ID (user-friendly format)",
    )
    parser.add_argument(
        "--create_runs", help="Whether to create runs (for ZenML internal use)"
    )
    parser.add_argument(
        "--host", default=os.getenv("ZENML_SERVICE_HOST", "0.0.0.0")
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ZENML_SERVICE_PORT", "8001")),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("ZENML_SERVICE_WORKERS", "1")),
    )
    parser.add_argument(
        "--log_level", default=os.getenv("ZENML_LOG_LEVEL", "info").lower()
    )

    args = parser.parse_args()

    # Set deployment ID from either argument format
    if args.deployment_id:
        os.environ["ZENML_PIPELINE_DEPLOYMENT_ID"] = args.deployment_id

    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")
    logger.info(f"Pipeline deployment ID: {args.deployment_id}")

    uvicorn.run(
        "zenml.deployers.serving.app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
