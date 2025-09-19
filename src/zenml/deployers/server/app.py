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
"""FastAPI application for running ZenML pipeline deployments."""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, create_model

from zenml.deployers.server.service import PipelineDeploymentService
from zenml.logger import get_logger

logger = get_logger(__name__)

# Track service start time
service_start_time: Optional[float] = None
_service: Optional[PipelineDeploymentService] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan.

    Args:
        app: The FastAPI application instance being deployed.

    Yields:
        None: Control is handed back to FastAPI once initialization completes.

    Raises:
        ValueError: If no deployment identifier is configured.
        Exception: If initialization or cleanup fails.
    """
    global service_start_time

    # Check for test mode
    if os.getenv("ZENML_DEPLOYMENT_TEST_MODE", "false").lower() == "true":
        logger.info("🧪 Running in test mode - skipping initialization")
        service_start_time = time.time()
        yield
        return

    # Startup
    logger.info("🚀 Starting ZenML Pipeline Serving service...")
    service_start_time = time.time()

    snapshot_id = os.getenv("ZENML_SNAPSHOT_ID")
    if not snapshot_id:
        raise ValueError("ZENML_SNAPSHOT_ID environment variable is required")

    try:
        global _service
        # Defer UUID parsing to the service itself to simplify testing
        _service = PipelineDeploymentService(snapshot_id)
        _service.initialize()
        # params model is available.
        try:
            params_model = _service.params_model
            if isinstance(params_model, type) and issubclass(
                params_model, BaseModel
            ):
                app.include_router(_build_invoke_router(_service))
                _install_runtime_openapi(app, _service)
        except Exception:
            # Skip router installation if parameter model is not ready
            pass
        logger.info("✅ Pipeline deployment service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down ZenML Pipeline Deployment service...")
    try:
        if _service:
            _service.cleanup()
            logger.info(
                "✅ Pipeline deployment service cleaned up successfully"
            )
    except Exception as e:
        logger.error(f"❌ Error during service cleanup: {e}")
    finally:
        # Ensure globals are reset to avoid stale references across lifecycles
        _service = None
        service_start_time = None


# Create FastAPI application with OpenAPI security scheme
app = FastAPI(
    title="ZenML Pipeline Deployment",
    description="deploy ZenML pipelines as FastAPI endpoints",
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


def _build_invoke_router(service: PipelineDeploymentService) -> APIRouter:
    """Create an idiomatic APIRouter that exposes /invoke.

    Args:
        service: The deployment service used to execute pipeline runs.

    Returns:
        A router exposing the `/invoke` endpoint wired to the service.
    """
    assert service.params_model is not None
    router = APIRouter()

    InvokeBody = create_model(
        "PipelineInvokeRequest",
        parameters=(service.params_model, ...),
        run_name=(Optional[str], None),
        timeout=(Optional[int], None),
        use_in_memory=(Optional[bool], None),
    )

    @router.post(
        "/invoke",
        name="invoke_pipeline",
        summary="Invoke the pipeline with validated parameters",
    )
    def _(
        body: InvokeBody,  # type: ignore[valid-type]
        _: None = Depends(verify_token),
    ) -> Dict[str, Any]:
        return service.execute_pipeline(
            body.parameters.model_dump(),  # type: ignore[attr-defined]
            body.run_name,  # type: ignore[attr-defined]
            body.timeout,  # type: ignore[attr-defined]
            body.use_in_memory,  # type: ignore[attr-defined]
        )

    return router


def get_pipeline_service() -> PipelineDeploymentService:
    """Get the pipeline deployment service.

    Returns:
        The initialized pipeline deployment service instance.
    """
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
    auth_key = os.getenv("ZENML_DEPLOYMENT_AUTH_KEY", "").strip()
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
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> str:
    """Root endpoint with service information.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        An HTML page describing the serving deployment.
    """
    info = service.get_service_info()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ZenML Pipeline Deployment</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ color: #2563eb; }}
            .section {{ margin: 20px 0; }}
            .status {{ padding: 5px 10px; border-radius: 4px; background: #10b981; color: white; }}
        </style>
    </head>
    <body>
        <h1 class="header">🚀 ZenML Pipeline Deployment</h1>
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
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Service health check endpoint.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        A dictionary describing the health of the service.

    Raises:
        HTTPException: If the service is not healthy.
    """
    if not service.is_healthy():
        raise HTTPException(503, "Service is unhealthy")

    info = service.get_service_info()
    uptime = time.time() - service_start_time if service_start_time else 0

    return {
        "status": "healthy",
        "snapshot_id": info["snapshot_id"],
        "pipeline_name": info["pipeline_name"],
        "uptime": uptime,
        "last_execution": service.last_execution_time,
    }


@app.get("/info")
async def pipeline_info(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get detailed pipeline information and parameter schema.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        A dictionary containing pipeline metadata and schema information.
    """
    info = service.get_service_info()

    return {
        "pipeline": {
            "name": info["pipeline_name"],
            "parameters": service.snapshot.pipeline_spec.parameters
            if service.snapshot and service.snapshot.pipeline_spec
            else {},
        },
        "snapshot": {
            "id": info["snapshot_id"],
        },
    }


@app.get("/metrics")
async def execution_metrics(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get pipeline execution metrics and statistics.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        A dictionary with execution metrics captured by the service.
    """
    metrics = service.get_execution_metrics()
    return metrics


@app.get("/schema")
async def get_schemas(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Expose current request/response schemas for verification/debugging.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        A dictionary containing request and response schema definitions.
    """
    return {
        "request_schema": service.request_schema,
        "output_schema": service.output_schema,
    }


@app.get("/status")
async def service_status(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get detailed service status information.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        A dictionary containing status and configuration information.
    """
    info = service.get_service_info()

    return {
        "service_name": "ZenML Pipeline Deployment",
        "version": "0.2.0",
        "snapshot_id": info["snapshot_id"],
        "status": "running" if service.is_healthy() else "unhealthy",
        "started_at": datetime.fromtimestamp(
            service_start_time, tz=timezone.utc
        )
        if service_start_time
        else datetime.now(timezone.utc),
        "configuration": {
            "snapshot_id": os.getenv("ZENML_SNAPSHOT_ID"),
            "host": os.getenv("ZENML_SERVICE_HOST", "0.0.0.0"),
            "port": int(os.getenv("ZENML_SERVICE_PORT", "8001")),
        },
    }


# Custom exception handlers
@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions (synchronous for unit tests).

    Args:
        request: The request.
        exc: The exception.

    Returns:
        The error response.
    """
    logger.error("ValueError in request: %s", exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Handle RuntimeError exceptions (synchronous for unit tests).

    Args:
        request: The request.
        exc: The exception.

    Returns:
        The error response.
    """
    logger.error("RuntimeError in request: %s", exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def _install_runtime_openapi(
    fastapi_app: FastAPI, service: PipelineDeploymentService
) -> None:
    """Inject request/response schemas for the invoke route into OpenAPI.

    This function decorates `fastapi_app.openapi` to include custom schemas
    based on the service-provided request/response schemas. It is a best-effort
    enhancement and will not raise if schemas are unavailable.

    Args:
        fastapi_app: The FastAPI application whose OpenAPI schema is updated.
        service: The serving service providing schema information.
    """
    original_openapi = fastapi_app.openapi

    def custom_openapi() -> Dict[str, Any]:
        schema = original_openapi()
        try:
            if (
                "paths" in schema
                and "/invoke" in schema["paths"]
                and "post" in schema["paths"]["/invoke"]
            ):
                post_op = schema["paths"]["/invoke"]["post"]

                # Request body schema
                req_schema: Optional[Dict[str, Any]] = getattr(
                    service, "request_schema", None
                )
                if req_schema:
                    rb_content = (
                        post_op.setdefault("requestBody", {})
                        .setdefault("content", {})
                        .setdefault("application/json", {})
                    )
                    # Use the precise parameters schema for the 'parameters' field
                    rb_content["schema"] = {
                        "type": "object",
                        "properties": {
                            "parameters": req_schema,
                            "run_name": {"type": "string"},
                            "timeout": {"type": "integer"},
                            "use_in_memory": {"type": "boolean"},
                        },
                        "required": ["parameters"],
                    }

                # Response schema for 200
                resp_schema: Optional[Dict[str, Any]] = service.output_schema
                if resp_schema:
                    responses = post_op.setdefault("responses", {})
                    ok = (
                        responses.setdefault("200", {})
                        .setdefault("content", {})
                        .setdefault("application/json", {})
                    )
                    # Use the full response schema as compiled
                    ok["schema"] = resp_schema
        except Exception:
            # Never break OpenAPI generation
            pass
        return schema

    fastapi_app.openapi = custom_openapi  # type: ignore[method-assign]


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot_id",
        default=os.getenv("ZENML_SNAPSHOT_ID"),
        help="Pipeline snapshot ID",
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
        "--auth_key", default=os.getenv("ZENML_DEPLOYMENT_AUTH_KEY", "")
    )
    args = parser.parse_args()

    if args.snapshot_id:
        os.environ["ZENML_SNAPSHOT_ID"] = args.snapshot_id
    if args.auth_key:
        os.environ["ZENML_DEPLOYMENT_AUTH_KEY"] = args.auth_key

    logger.info(f"Starting FastAPI server on {args.host}:{args.port}")

    uvicorn.run(
        "zenml.deployers.server.app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
        reload=False,
    )
