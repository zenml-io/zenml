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

import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from zenml.logger import get_logger
from zenml.serving.concurrency import (
    ServingExecutionManager,
    TooManyRequestsError,
)
from zenml.serving.dependencies import (
    RequestContext,
    get_execution_manager,
    get_job_registry,
    get_pipeline_service,
    get_request_context,
    get_stream_manager,
    initialize_container,
    shutdown_container,
)
from zenml.serving.jobs import JobRegistry, JobStatus
from zenml.serving.models import (
    DeploymentInfo,
    ExecutionMetrics,
    HealthResponse,
    InfoResponse,
    PipelineInfo,
    PipelineRequest,
    PipelineResponse,
    ServiceStatus,
)
from zenml.serving.service import PipelineServingService
from zenml.serving.streams import StreamManager

logger = get_logger(__name__)

# Track service start time
service_start_time: Optional[float] = None


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
        await initialize_container(deployment_id)
        logger.info("✅ Pipeline serving service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down ZenML Pipeline Serving service...")
    await shutdown_container()


# Create FastAPI application
app = FastAPI(
    title="ZenML Pipeline Serving",
    description="Serve ZenML pipelines as FastAPI endpoints",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

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
    request: PipelineRequest,
    mode: str = Query("sync", description="Execution mode: 'sync' or 'async'"),
    service: PipelineServingService = Depends(get_pipeline_service),
    context: RequestContext = Depends(get_request_context),
) -> PipelineResponse:
    """Execute pipeline with dependency injection."""
    logger.info(
        f"[{context.request_id}] Pipeline execution request (mode={mode})"
    )

    try:
        if mode.lower() == "async":
            result = await service.submit_pipeline(
                parameters=request.parameters,
                run_name=request.run_name,
                timeout=request.timeout,
                capture_override=request.capture_override,
            )
        else:
            result = await service.execute_pipeline(
                parameters=request.parameters,
                run_name=request.run_name,
                timeout=request.timeout,
                capture_override=request.capture_override,
            )
        return PipelineResponse(**result)

    except TooManyRequestsError as e:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": "60"},
        )
    except Exception as e:
        logger.error(f"[{context.request_id}] Pipeline execution failed: {e}")
        return PipelineResponse(
            success=False, error=f"Internal server error: {str(e)}"
        )


@app.websocket("/stream")
async def stream_pipeline(
    websocket: WebSocket,
    service: PipelineServingService = Depends(get_pipeline_service),
) -> None:
    """Execute pipeline with streaming updates via WebSocket."""
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        request = PipelineRequest(**data)

        logger.info(
            f"Received streaming pipeline request: {request.model_dump()}"
        )

        async for event in service.execute_pipeline_streaming(
            parameters=request.parameters, run_name=request.run_name
        ):
            await websocket.send_json(event.model_dump())

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Streaming execution failed: {e}")
        try:
            await websocket.send_json(
                {
                    "event": "error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    job_registry: JobRegistry = Depends(get_job_registry),
    context: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Get status and results of a specific job."""
    try:
        job = job_registry.get_job(job_id)
        if not job:
            raise HTTPException(404, f"Job {job_id} not found")
        return job.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{context.request_id}] Failed to get job status: {e}")
        raise HTTPException(500, str(e))


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    reason: Optional[str] = None,
    job_registry: JobRegistry = Depends(get_job_registry),
    context: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Cancel a running job."""
    try:
        cancelled = job_registry.cancel_job(job_id, reason=reason)
        if not cancelled:
            raise HTTPException(400, f"Job {job_id} could not be cancelled")
        return {
            "message": f"Job {job_id} cancelled successfully",
            "cancelled": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{context.request_id}] Failed to cancel job: {e}")
        raise HTTPException(500, str(e))


@app.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(100, description="Maximum number of jobs to return"),
    job_registry: JobRegistry = Depends(get_job_registry),
    context: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """List jobs with optional filtering."""
    try:
        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status.lower())
            except ValueError:
                raise HTTPException(400, f"Invalid status '{status}'")

        jobs = job_registry.list_jobs(status_filter=status_filter, limit=limit)
        return {"jobs": jobs, "total": len(jobs)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{context.request_id}] Failed to list jobs: {e}")
        raise HTTPException(500, str(e))


@app.get("/stream/{job_id}")
async def stream_job_events(
    job_id: str,
    job_registry: JobRegistry = Depends(get_job_registry),
    stream_manager: StreamManager = Depends(get_stream_manager),
) -> StreamingResponse:
    """Stream events for a specific job using Server-Sent Events."""
    try:
        job = job_registry.get_job(job_id)
        if not job:
            raise HTTPException(404, f"Job {job_id} not found")

        async def event_stream() -> AsyncGenerator[str, None]:
            try:
                yield "retry: 5000\n\n"

                initial_data = {
                    "job_id": job_id,
                    "status": job.status.value,
                    "message": "Connected to job event stream",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: connected\ndata: {json.dumps(initial_data)}\n\n"

                async for event in stream_manager.subscribe_to_job(job_id):
                    event_data = event.to_dict()
                    yield f"event: {event.event_type.value}\ndata: {json.dumps(event_data)}\n\n"

                    if event.event_type.value in [
                        "pipeline_completed",
                        "pipeline_failed",
                        "cancellation_requested",
                    ]:
                        break

            except Exception as e:
                logger.error(f"Error in SSE stream for job {job_id}: {e}")
                error_data = {"error": str(e), "job_id": job_id}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create SSE stream: {e}")
        raise HTTPException(500, str(e))


@app.get("/concurrency/stats")
async def concurrency_stats(
    execution_manager: ServingExecutionManager = Depends(
        get_execution_manager
    ),
    job_registry: JobRegistry = Depends(get_job_registry),
    stream_manager: StreamManager = Depends(get_stream_manager),
) -> Dict[str, Any]:
    """Get current concurrency and execution statistics."""
    try:
        return {
            "execution": execution_manager.get_stats(),
            "jobs": job_registry.get_stats(),
            "streams": await stream_manager.get_stats(),
        }
    except Exception as e:
        logger.error(f"Failed to get concurrency stats: {e}")
        raise HTTPException(500, str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> HealthResponse:
    """Service health check endpoint."""
    if not service.is_healthy():
        raise HTTPException(503, "Service is unhealthy")

    info = service.get_service_info()
    uptime = time.time() - service_start_time if service_start_time else 0

    return HealthResponse(
        status="healthy",
        deployment_id=info["service"]["deployment_id"],
        pipeline_name=info["pipeline"]["name"],
        uptime=uptime,
        last_execution=service.last_execution_time,
    )


@app.get("/info", response_model=InfoResponse)
async def pipeline_info(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> InfoResponse:
    """Get detailed pipeline information and parameter schema."""
    info = service.get_service_info()

    return InfoResponse(
        pipeline=PipelineInfo(
            name=info["pipeline"]["name"],
            steps=info["pipeline"]["steps"],
            parameters=info["pipeline"]["parameters"],
        ),
        deployment=DeploymentInfo(
            id=info["deployment"]["id"],
            created_at=info["deployment"]["created_at"],
            stack=info["deployment"]["stack"],
        ),
    )


@app.get("/metrics", response_model=ExecutionMetrics)
async def execution_metrics(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> ExecutionMetrics:
    """Get pipeline execution metrics and statistics."""
    metrics = service.get_execution_metrics()
    return ExecutionMetrics(**metrics)


@app.get("/status", response_model=ServiceStatus)
async def service_status(
    service: PipelineServingService = Depends(get_pipeline_service),
) -> ServiceStatus:
    """Get detailed service status information."""
    info = service.get_service_info()

    return ServiceStatus(
        service_name="ZenML Pipeline Serving",
        version="0.2.0",
        deployment_id=info["service"]["deployment_id"],
        status="running" if service.is_healthy() else "unhealthy",
        started_at=datetime.fromtimestamp(service_start_time, tz=timezone.utc)
        if service_start_time
        else datetime.now(timezone.utc),
        configuration={
            "deployment_id": os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID"),
            "host": os.getenv("ZENML_SERVICE_HOST", "0.0.0.0"),
            "port": int(os.getenv("ZENML_SERVICE_PORT", "8001")),
        },
    )


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
    import uvicorn

    # Configuration from environment variables
    host = os.getenv("ZENML_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("ZENML_SERVICE_PORT", "8001"))
    workers = int(os.getenv("ZENML_SERVICE_WORKERS", "1"))
    log_level = os.getenv("ZENML_LOG_LEVEL", "info").lower()

    logger.info(f"Starting FastAPI server on {host}:{port}")

    uvicorn.run(
        "zenml.serving.app:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        reload=False,  # Disable reload in production
    )
