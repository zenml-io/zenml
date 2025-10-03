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
from typing import AsyncGenerator, Callable, List, Literal, Optional

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
from pydantic import BaseModel, Field

from zenml.deployers.server.models import (
    ExecutionMetrics,
    ServiceInfo,
    get_pipeline_invoke_models,
)
from zenml.deployers.server.service import PipelineDeploymentService
from zenml.logger import get_logger

logger = get_logger(__name__)

# Callables that construct a PipelineDeploymentService given a deployment ID.
ServiceFactory = Callable[[str], PipelineDeploymentService]


class DeploymentAppConfig(BaseModel):
    """Configuration for a single FastAPI deployment app instance.

    This is intentionally a Pydantic model to make it easy to validate and
    serialize configuration in deployment scenarios and tests.
    """

    # Deployment identity and docs metadata
    deployment_id: Optional[str] = None
    title: str = Field(
        default_factory=lambda: f"ZenML Pipeline Deployment {os.getenv('ZENML_DEPLOYMENT_ID', '')}".strip()
        or "ZenML Pipeline Deployment"
    )
    description: str = "deploy ZenML pipelines as FastAPI endpoints"
    version: str = "0.2.0"
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"

    # CORS and runtime flags
    cors_origins: Optional[List[str]] = None  # Defaults to ['*'] if None
    test_mode: Optional[bool] = None

    # Authentication
    auth_key: Optional[str] = None


def _build_auth_dependency(
    auth_key: Optional[str],
) -> tuple[HTTPBearer, Callable[..., None]]:
    """Build a per-instance auth dependency and HTTPBearer security scheme.

    The explicit `auth_key` parameter takes precedence over the
    ZENML_DEPLOYMENT_AUTH_KEY environment variable. When the resolved key is
    empty, authentication is effectively disabled and the dependency no-ops.

    Args:
        auth_key: Optional explicit key to enforce for bearer auth.

    Returns:
        A tuple containing:
        - HTTPBearer security object with auto_error=False
        - A verify_token dependency closure that enforces the key when present
    """
    effective_key = (
        auth_key or os.getenv("ZENML_DEPLOYMENT_AUTH_KEY", "")
    ).strip()

    security = HTTPBearer(
        scheme_name="Bearer Token",
        description="Enter your API key as a Bearer token",
        auto_error=False,  # Manual error handling to reuse headers and messages
    )

    def verify_token_dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            security
        ),
    ) -> None:
        # When no key is configured, auth is disabled and all requests are allowed.
        if not effective_key:
            return

        # Require Authorization header when a key is configured.
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Enforce exact match with configured key.
        if credentials.credentials != effective_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return

    return security, verify_token_dep


def create_app(
    *,
    config: Optional[DeploymentAppConfig] = None,
    service_factory: Optional[ServiceFactory] = None,
) -> FastAPI:
    """Create a fresh FastAPI application instance for a deployment.

    This factory:
    - Resolves test mode and deployment ID (config overrides env),
    - Instantiates a PipelineDeploymentService via the provided factory or default,
    - Wires a per-instance authentication dependency into the /invoke router,
    - Registers CORS, routes, and exception handlers, and
    - Stores the service and verify_token closure on app.state.

    Args:
        config: Optional DeploymentAppConfig; if omitted, sensible defaults are used.
        service_factory: Optional factory to construct the service; defaults to
            PipelineDeploymentService.

    Returns:
        A configured FastAPI application instance.
    """
    cfg = config or DeploymentAppConfig()

    # Resolve test mode with config taking precedence over the environment variable.
    env_test_mode = (
        os.getenv("ZENML_DEPLOYMENT_TEST_MODE", "false").lower() == "true"
    )
    test_mode = cfg.test_mode if cfg.test_mode is not None else env_test_mode

    # Resolve deployment ID with config taking precedence.
    resolved_deployment_id = cfg.deployment_id or os.getenv(
        "ZENML_DEPLOYMENT_ID"
    )

    # Create per-app security + dependency
    instance_security, instance_verify_token = _build_auth_dependency(
        cfg.auth_key
    )

    @asynccontextmanager
    async def _instance_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Short-circuit startup / shutdown for isolated tests
        if test_mode:
            logger.info("🧪 Running in test mode - skipping initialization")
            app.state.service = None
            app.state.verify_token = instance_verify_token
            yield
            return

        # Startup
        logger.info("🚀 Starting ZenML Pipeline Serving service...")

        if not resolved_deployment_id:
            raise ValueError(
                "ZENML_DEPLOYMENT_ID environment variable is required"
            )

        # Initialize service and register invoke router
        factory = service_factory or PipelineDeploymentService
        service = factory(resolved_deployment_id)
        try:
            service.initialize()
            app.state.service = service
            app.state.verify_token = instance_verify_token
            router = _build_invoke_router(
                service, auth_dep=instance_verify_token
            )
            app.include_router(router)
            logger.info(
                "✅ Pipeline deployment service initialized successfully"
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            # Ensure partial state does not leak across lifespan cycles
            app.state.service = None
            app.state.verify_token = instance_verify_token
            raise

        yield

        # Shutdown
        logger.info("🛑 Shutting down ZenML Pipeline Deployment service...")
        try:
            if getattr(app.state, "service", None):
                app.state.service.cleanup()
                logger.info(
                    "✅ Pipeline deployment service cleaned up successfully"
                )
        except Exception as e:
            logger.error(f"❌ Error during service cleanup: {e}")
        finally:
            # Avoid stale references across reloads
            app.state.service = None

    # Build the FastAPI instance
    fastapi_app = FastAPI(
        title=cfg.title,
        description=cfg.description,
        version=cfg.version,
        lifespan=_instance_lifespan,
        docs_url=cfg.docs_url,
        redoc_url=cfg.redoc_url,
    )

    # CORS middleware mirrors module-level configuration, using per-config origins.
    allow_origins = cfg.cors_origins or ["*"]
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Reuse existing route callables to avoid duplicating logic.
    fastapi_app.add_api_route("/", root, response_class=HTMLResponse)
    fastapi_app.add_api_route("/health", health_check)
    fastapi_app.add_api_route("/info", info)
    fastapi_app.add_api_route("/metrics", execution_metrics)

    # Exception handlers mirroring module-level registrations.
    fastapi_app.add_exception_handler(ValueError, value_error_handler)
    fastapi_app.add_exception_handler(RuntimeError, runtime_error_handler)

    # Expose for debugging / tests
    fastapi_app.state.verify_token = instance_verify_token
    fastapi_app.state.security = instance_security

    return fastapi_app


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
app.state.security = security  # Keep module-level app parity with create_app by exposing security on state


def _build_invoke_router(
    service: PipelineDeploymentService,
    auth_dep: Optional[Callable[..., None]] = None,
) -> APIRouter:
    """Create an idiomatic APIRouter that exposes /invoke.

    Args:
        service: The deployment service used to execute pipeline runs.
        auth_dep: Optional dependency to verify authentication. Falls back to
            the module-level verify_token when not provided, to preserve legacy behavior.

    Returns:
        A router exposing the `/invoke` endpoint wired to the service.
    """
    router = APIRouter()

    PipelineInvokeRequest, PipelineInvokeResponse = get_pipeline_invoke_models(
        service
    )
    verify_dependency = auth_dep or verify_token

    @router.post(
        "/invoke",
        name="invoke_pipeline",
        summary="Invoke the pipeline with validated parameters",
        response_model=PipelineInvokeResponse,
    )
    def _(
        request: PipelineInvokeRequest,  # type: ignore[valid-type]
        _: None = Depends(verify_dependency),
    ) -> PipelineInvokeResponse:  # type: ignore[valid-type]
        return service.execute_pipeline(request)

    return router


def get_pipeline_service(request: Request) -> PipelineDeploymentService:
    """Resolve the active PipelineDeploymentService instance.

    This is designed to be used as a FastAPI dependency. It expects the
    Request object to be provided by FastAPI, and it prefers resolving the
    service from the current application's state (request.app.state.service).
    If no per-app service is available, it falls back to the legacy module-
    level singleton service for backward compatibility.

    Args:
        request: The current HTTP request (injected by FastAPI).

    Returns:
        The initialized pipeline deployment service instance.
    """
    app_obj = getattr(request, "app", None)
    state = getattr(app_obj, "state", None)
    if state is not None and getattr(state, "service", None) is not None:
        return state.service  # type: ignore[return-value]

    # Legacy path: use module-level singleton service.
    assert _service is not None
    return _service


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> None:
    """Verify the provided Bearer token for authentication.

    NOTE: This dependency is used by the module-level singleton app defined in
    this module. For new, programmatic instances, prefer using
    `_build_auth_dependency(...)/create_app(...)` to construct a per-app
    dependency and security scheme.

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


# Make the authentication dependency available on the module-level app state
app.state.verify_token = verify_token


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
            <p>Pipeline: <strong>{info.pipeline.name}</strong></p>
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


# Explicit public API surface for importers
__all__ = [
    "app",
    "create_app",
    "DeploymentAppConfig",
    "_build_invoke_router",
    "get_pipeline_service",
    "verify_token",
    "lifespan",
]


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
