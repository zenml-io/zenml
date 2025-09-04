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
"""FastAPI application for serving ZenML pipelines."""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from zenml.deployers.serving.service import PipelineServingService
from zenml.logger import get_logger

logger = get_logger(__name__)

# Track service start time
service_start_time: Optional[float] = None
_service: Optional[PipelineServingService] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan."""
    global service_start_time

    # Check for test mode
    if os.getenv("ZENML_SERVING_TEST_MODE", "false").lower() == "true":
        logger.info("🧪 Running in test mode - skipping initialization")
        service_start_time = time.time()
        yield
        return

    # Startup
    logger.info("🚀 Starting ZenML Pipeline Serving service...")
    service_start_time = time.time()

    deployment_id = os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID")
    if not deployment_id:
        raise ValueError(
            "ZENML_PIPELINE_DEPLOYMENT_ID environment variable is required"
        )

    try:
        global _service
        _service = PipelineServingService(deployment_id)
        await _service.initialize()
        logger.info("✅ Pipeline serving service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down ZenML Pipeline Serving service...")


# Create FastAPI application
app = FastAPI(
    title="ZenML Pipeline Serving",
    description="Serve ZenML pipelines as FastAPI endpoints",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


class PipelineInvokeRequest(BaseModel):
    """Request model for pipeline invocation."""

    parameters: Dict[str, Any] = {}
    run_name: Optional[str] = None
    timeout: Optional[int] = None


def get_pipeline_service() -> PipelineServingService:
    """Get the pipeline serving service."""
    assert _service is not None
    return _service


# Add CORS middleware to allow frontend access
# TODO: In production, restrict allow_origins to specific domains for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> str:
    """Root endpoint with service information."""
    info = service.get_service_info()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ZenML Pipeline Serving</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ color: #2563eb; }}
            .section {{ margin: 20px 0; }}
            .status {{ padding: 5px 10px; border-radius: 4px; background: #10b981; color: white; }}
        </style>
    </head>
    <body>
        <h1 class="header">🚀 ZenML Pipeline Serving</h1>
        <div class="section">
            <h2>Service Status</h2>
            <p>Status: <span class="status">Running</span></p>
            <p>Pipeline: <strong>{info["pipeline"]["name"]}</strong></p>
            <p>Steps: {len(info["pipeline"]["steps"])}</p>
            <p>Uptime: {info["service"]["uptime"]:.1f}s</p>
        </div>
        <div class="section">
            <h2>Documentation</h2>
            <p><a href="/docs">📖 Interactive API Documentation</a></p>
        </div>
    </body>
    </html>
    """
    return html_content


@app.post("/invoke")
async def invoke_pipeline(
    request: PipelineInvokeRequest,
    service: PipelineServingService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Execute pipeline with dependency injection."""
    try:
        result = await service.execute_pipeline(
            parameters=request.parameters,
            run_name=request.run_name,
            timeout=request.timeout,
        )
        return result
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}


@app.get("/concurrency/stats")
async def concurrency_stats() -> Dict[str, Any]:
    """Placeholder stats endpoint."""
    return {"execution": {}, "jobs": {}, "streams": {}}


@app.get("/health")
async def health_check(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Service health check endpoint."""
    if not service.is_healthy():
        raise HTTPException(503, "Service is unhealthy")

    info = service.get_service_info()
    uptime = time.time() - service_start_time if service_start_time else 0

    return {
        "status": "healthy",
        "deployment_id": info["service"]["deployment_id"],
        "pipeline_name": info["pipeline"]["name"],
        "uptime": uptime,
        "last_execution": service.last_execution_time,
    }


@app.get("/info")
async def pipeline_info(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get detailed pipeline information and parameter schema."""
    info = service.get_service_info()

    return {
        "pipeline": {
            "name": info["pipeline"]["name"],
            "steps": info["pipeline"]["steps"],
            "parameters": info["pipeline"]["parameters"],
        },
        "deployment": {
            "id": info["deployment"]["id"],
            "created_at": info["deployment"]["created_at"],
            "stack": info["deployment"]["stack"],
        },
    }


@app.get("/metrics")
async def execution_metrics(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get pipeline execution metrics and statistics."""
    metrics = service.get_execution_metrics()
    return metrics


@app.get("/status")
async def service_status(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get detailed service status information."""
    info = service.get_service_info()

    return {
        "service_name": "ZenML Pipeline Serving",
        "version": "0.2.0",
        "deployment_id": info["service"]["deployment_id"],
        "status": "running" if service.is_healthy() else "unhealthy",
        "started_at": datetime.fromtimestamp(
            service_start_time, tz=timezone.utc
        )
        if service_start_time
        else datetime.now(timezone.utc),
        "configuration": {
            "deployment_id": os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID"),
            "host": os.getenv("ZENML_SERVICE_HOST", "0.0.0.0"),
            "port": int(os.getenv("ZENML_SERVICE_PORT", "8001")),
        },
    }


# Custom exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request, exc: ValueError
) -> HTTPException:
    """Handle ValueError exceptions."""
    logger.error(f"ValueError in request {request.url}: {str(exc)}")
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(RuntimeError)
async def runtime_error_handler(
    request: Request, exc: RuntimeError
) -> HTTPException:
    """Handle RuntimeError exceptions."""
    logger.error(f"RuntimeError in request {request.url}: {str(exc)}")
    return HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment_id", help="Pipeline deployment ID")
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

    if args.deployment_id:
        os.environ["ZENML_PIPELINE_DEPLOYMENT_ID"] = args.deployment_id

    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")

    uvicorn.run(
        "zenml.deployers.serving.app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
        reload=False,
    )
