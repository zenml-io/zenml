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
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import create_model
from starlette.concurrency import run_in_threadpool

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
        _service = PipelineServingService(UUID(deployment_id))
        await _service.initialize()
        # Register a clean, focused router for the /invoke endpoint.
        app.include_router(_build_invoke_router(_service))
        logger.info("✅ Pipeline serving service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down ZenML Pipeline Serving service...")
    try:
        if _service:
            await _service.cleanup()
            logger.info("✅ Pipeline serving service cleaned up successfully")
    except Exception as e:
        logger.error(f"❌ Error during service cleanup: {e}")


# Create FastAPI application with OpenAPI security scheme
app = FastAPI(
    title="ZenML Pipeline Serving",
    description="Serve ZenML pipelines as FastAPI endpoints",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Define security scheme for OpenAPI documentation
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Enter your API key as a Bearer token",
    auto_error=False,  # We handle errors in our dependency
)


def _build_invoke_router(service: PipelineServingService) -> APIRouter:
    """Create an idiomatic APIRouter that exposes /invoke."""
    assert service._params_model is not None
    router = APIRouter()

    InvokeBody = create_model(
        "PipelineInvokeRequest",
        parameters=(service._params_model, ...),
        run_name=(Optional[str], None),
        timeout=(Optional[int], None),
        use_in_memory=(Optional[bool], None),
    )

    @router.post(
        "/invoke",
        name="invoke_pipeline",
        summary="Invoke the pipeline with validated parameters",
    )
    async def invoke(
        body: InvokeBody,  # type: ignore[valid-type]
        _: None = Depends(verify_token),
    ) -> Dict[str, Any]:
        return await run_in_threadpool(
            service.execute_pipeline,
            body.parameters.model_dump(),  # type: ignore[attr-defined]
            body.run_name,  # type: ignore[attr-defined]
            body.timeout,  # type: ignore[attr-defined]
            body.use_in_memory,  # type: ignore[attr-defined]
        )

    return router


def get_pipeline_service() -> PipelineServingService:
    """Get the pipeline serving service."""
    assert _service is not None
    return _service


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> None:
    """Verify the provided Bearer token for authentication.

    This dependency function integrates with FastAPI's security system
    to provide proper OpenAPI documentation and authentication UI.

    Args:
        credentials: HTTP Bearer credentials from the request

    Raises:
        HTTPException: If authentication is required but token is invalid
    """
    auth_key = os.getenv("ZENML_SERVING_AUTH_KEY", "").strip()
    auth_enabled = auth_key and auth_key != ""

    # If authentication is not enabled, allow all requests
    if not auth_enabled:
        return

    # If authentication is enabled, validate the token
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != auth_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Token is valid, authentication successful
    return


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
            <p>Pipeline: <strong>{info["pipeline_name"]}</strong></p>
        </div>
        <div class="section">
            <h2>Documentation</h2>
            <p><a href="/docs">📖 Interactive API Documentation</a></p>
        </div>
    </body>
    </html>
    """
    return html_content


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
        "deployment_id": info["deployment_id"],
        "pipeline_name": info["pipeline_name"],
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
            "name": info["pipeline_name"],
            "parameters": service.deployment.pipeline_spec.parameters
            if service.deployment and service.deployment.pipeline_spec
            else {},
        },
        "deployment": {
            "id": info["deployment_id"],
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
        "deployment_id": info["deployment_id"],
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
    parser.add_argument(
        "--deployment_id",
        default=os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID"),
        help="Pipeline deployment ID",
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
    parser.add_argument(
        "--auth_key", default=os.getenv("ZENML_SERVING_AUTH_KEY", "")
    )
    args = parser.parse_args()

    if args.deployment_id:
        os.environ["ZENML_PIPELINE_DEPLOYMENT_ID"] = args.deployment_id
    if args.auth_key:
        os.environ["ZENML_SERVING_AUTH_KEY"] = args.auth_key

    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")

    uvicorn.run(
        "zenml.deployers.serving.app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
        reload=False,
    )
