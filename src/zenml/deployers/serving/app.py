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
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from zenml.deployers.serving.auth import BearerTokenAuthMiddleware
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
        # Update OpenAPI schema if a serve contract is available
        _install_runtime_openapi(app, _service)
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

    parameters: Dict[str, Any] = Field(default_factory=dict)
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

# Add authentication middleware
# This middleware will protect all endpoints except root, health, info, metrics,
# and status
app.add_middleware(BearerTokenAuthMiddleware)


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


@app.post("/invoke")
async def invoke_pipeline(
    request: PipelineInvokeRequest,
    service: PipelineServingService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Execute pipeline with dependency injection."""
    try:
        # Validate request parameters against runtime schema if available
        if service.request_schema:
            err = _validate_request_parameters(
                request.parameters, service.request_schema
            )
            if err:
                raise ValueError(f"Invalid parameters: {err}")
        # Offload synchronous execution to a thread to avoid blocking the event loop
        result = await run_in_threadpool(
            service.execute_pipeline,
            request.parameters,
            request.run_name,
            request.timeout,
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


def _install_runtime_openapi(
    app: FastAPI, service: PipelineServingService
) -> None:
    """Install contract-based OpenAPI schema for the /invoke route.

    Args:
        app: The FastAPI app.
        service: The pipeline serving service.
    """
    from fastapi.openapi.utils import get_openapi

    def custom_openapi() -> Dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        try:
            path_item = openapi_schema.get("paths", {}).get("/invoke", {})
            post_op = path_item.get("post") or {}
            # Request body schema derived at runtime
            request_schema: Dict[str, Any] = {
                "type": "object",
                "properties": {
                    "parameters": service.request_schema or {"type": "object"},
                    "run_name": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["parameters"],
            }
            post_op.setdefault("requestBody", {}).setdefault(
                "content", {}
            ).setdefault("application/json", {})["schema"] = request_schema

            # Response schema derived at runtime
            response_schema: Dict[str, Any] = {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "outputs": service.response_schema or {"type": "object"},
                    "execution_time": {"type": "number"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "pipeline_name": {"type": "string"},
                            "parameters_used": {"type": "object"},
                            "deployment_id": {"type": "string"},
                        },
                    },
                },
                "required": [
                    "success",
                    "outputs",
                    "execution_time",
                    "metadata",
                ],
            }
            responses = post_op.setdefault("responses", {})
            responses["200"] = {
                "description": "Successful Response",
                "content": {"application/json": {"schema": response_schema}},
            }
            path_item["post"] = post_op
            openapi_schema.setdefault("paths", {})["/invoke"] = path_item
        except Exception:
            # Keep default schema if any error occurs
            pass

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def _validate_request_parameters(
    params: Dict[str, Any], schema: Dict[str, Any]
) -> Optional[str]:
    """Minimal validation for request parameters using contract.request_schema.

    Returns an error string if invalid, otherwise None.
    """
    schema = schema or {}
    required = schema.get("required", [])
    props = schema.get("properties", {})

    # Check if params is actually a dict
    if not isinstance(params, dict):
        return "parameters must be an object"

    missing = [k for k in required if k not in params]
    if missing:
        return f"missing required fields: {missing}"

    for key, val in params.items():
        spec = props.get(key)
        if not spec:
            # allow extra fields for now
            continue
        expected = spec.get("type")
        if (
            expected
            and expected != "any"
            and not _json_type_matches(val, expected)
        ):
            return f"field '{key}' expected type {expected}, got {type(val).__name__}"
    return None


def _json_type_matches(value: Any, expected: str) -> bool:
    t = expected.lower()
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "array":
        return isinstance(value, list)
    if t == "object":
        return isinstance(value, dict)
    return True
