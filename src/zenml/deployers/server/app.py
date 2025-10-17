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
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Literal, Optional

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

from zenml.deployers.server.models import (
    ExecutionMetrics,
    ServiceInfo,
    get_pipeline_invoke_models,
)
from zenml.deployers.server.service import PipelineDeploymentService
from zenml.logger import get_logger

logger = get_logger(__name__)

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
    # Check for test mode
    if os.getenv("ZENML_DEPLOYMENT_TEST_MODE", "false").lower() == "true":
        logger.info("🧪 Running in test mode - skipping initialization")
        yield
        return

    # Startup
    logger.info("🚀 Starting ZenML Pipeline Serving service...")

    deployment_id = os.getenv("ZENML_DEPLOYMENT_ID")
    if not deployment_id:
        raise ValueError(
            "ZENML_DEPLOYMENT_ID environment variable is required"
        )

    try:
        global _service
        _service = PipelineDeploymentService(deployment_id)
        _service.initialize()
        app.include_router(_build_invoke_router(_service))
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


# Create FastAPI application with OpenAPI security scheme
app = FastAPI(
    title=f"ZenML Pipeline Deployment {os.getenv('ZENML_DEPLOYMENT_ID')}",
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
    router = APIRouter()

    PipelineInvokeRequest, PipelineInvokeResponse = get_pipeline_invoke_models(
        service
    )

    @router.post(
        "/invoke",
        name="invoke_pipeline",
        summary="Invoke the pipeline with validated parameters",
        response_model=PipelineInvokeResponse,
    )
    def _(
        request: PipelineInvokeRequest,  # type: ignore[valid-type]
        _: None = Depends(verify_token),
    ) -> PipelineInvokeResponse:  # type: ignore[valid-type]
        return service.execute_pipeline(request)

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
    """Root endpoint with enhanced dashboard interface.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        An HTML page with deployment info and interactive playground.
    """
    import json
    from pathlib import Path

    info = service.get_service_info()
    metrics = service.get_execution_metrics()

    # Prepare data for JavaScript
    info_json = json.dumps(
        {
            "deployment": {
                "id": str(info.deployment.id),
                "name": info.deployment.name,
            },
            "snapshot": {
                "id": str(info.snapshot.id),
                "name": info.snapshot.name,
            },
            "pipeline": {
                "name": info.pipeline.name,
                "input_schema": info.pipeline.input_schema or {},
                "output_schema": info.pipeline.output_schema or {},
            },
            "status": info.status,
            "uptime": info.uptime,
            "total_executions": metrics.total_executions,
            "last_execution_time": (
                metrics.last_execution_time.isoformat()
                if metrics.last_execution_time
                else None
            ),
        }
    )

    # Format uptime for display
    uptime_days = int(info.uptime // 86400)
    uptime_hours = int((info.uptime % 86400) // 3600)
    uptime_str = (
        f"{uptime_days}d {uptime_hours}h"
        if uptime_days > 0
        else f"{uptime_hours}h"
    )

    # Format last execution time
    last_exec_str = "Never"
    if metrics.last_execution_time:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        delta = now - metrics.last_execution_time
        if delta.total_seconds() < 60:
            last_exec_str = "Just now"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            last_exec_str = f"{minutes} min ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            last_exec_str = f"{hours}h ago"
        else:
            days = int(delta.total_seconds() / 86400)
            last_exec_str = f"{days}d ago"

    # Load template from file
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    template = template_path.read_text()

    # Replace template variables
    html_content = template.replace("{{ pipeline_name }}", info.pipeline.name)
    html_content = html_content.replace("{{ status }}", info.status)
    html_content = html_content.replace("{{ uptime_str }}", uptime_str)
    html_content = html_content.replace(
        "{{ total_executions }}", str(metrics.total_executions)
    )
    html_content = html_content.replace("{{ last_exec_str }}", last_exec_str)
    html_content = html_content.replace(
        "{{ deployment_id }}", str(info.deployment.id)
    )
    html_content = html_content.replace(
        "{{ deployment_id_short }}", str(info.deployment.id)[:8]
    )
    html_content = html_content.replace("{{ service_info_json }}", info_json)

    return html_content


@app.get("/health")
async def health_check(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> Literal["OK"]:
    """Service health check endpoint.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        "OK" if the service is healthy, otherwise raises an HTTPException.

    Raises:
        HTTPException: If the service is not healthy.
    """
    if not service.is_healthy():
        raise HTTPException(503, "Service is unhealthy")

    return "OK"


@app.get("/info")
async def info(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> ServiceInfo:
    """Get detailed information about the service, including pipeline metadata and schema.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        Service info.
    """
    return service.get_service_info()


@app.get("/metrics")
async def execution_metrics(
    service: PipelineDeploymentService = Depends(get_pipeline_service),
) -> ExecutionMetrics:
    """Get pipeline execution metrics and statistics.

    Args:
        service: The pipeline serving service dependency.

    Returns:
        Aggregated execution metrics.
    """
    return service.get_execution_metrics()


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
def runtime_error_handler(
    request: Request, exc: RuntimeError
) -> JSONResponse:
    """Handle RuntimeError exceptions (synchronous for unit tests).

    Args:
        request: The request.
        exc: The exception.

    Returns:
        The error response.
    """
    logger.error("RuntimeError in request: %s", exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deployment_id",
        default=os.getenv("ZENML_DEPLOYMENT_ID"),
        help="Pipeline snapshot ID",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("ZENML_SERVICE_HOST", "0.0.0.0"),  # nosec
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

    if args.deployment_id:
        os.environ["ZENML_DEPLOYMENT_ID"] = args.deployment_id
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
