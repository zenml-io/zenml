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
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from zenml.logger import get_logger
from zenml.serving.concurrency import (
    TooManyRequestsError,
    get_execution_manager,
    shutdown_execution_manager,
)
from zenml.serving.jobs import (
    JobStatus,
    get_job_registry,
    shutdown_job_registry,
)
from zenml.serving.models import (
    ExecutionMetrics,
    HealthResponse,
    InfoResponse,
    PipelineRequest,
    PipelineResponse,
    ServiceStatus,
)
from zenml.serving.service import PipelineServingService
from zenml.serving.streams import get_stream_manager, shutdown_stream_manager

logger = get_logger(__name__)

# Global service instance
# TODO: Improve global state management
# Issue: Using global variables for service state is not ideal for production
# Solutions:
# 1. Use FastAPI dependency injection with a singleton pattern
# 2. Store state in app.state which is the FastAPI recommended approach
# 3. Consider using contextvars for request-scoped state
pipeline_service: Optional[PipelineServingService] = None
service_start_time: Optional[float] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan - startup and shutdown."""
    global pipeline_service, service_start_time

    # Startup
    logger.info("🚀 Starting ZenML Pipeline Serving service...")
    service_start_time = time.time()

    # Get deployment ID from environment variable
    deployment_id = os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID")
    if not deployment_id:
        raise ValueError(
            "ZENML_PIPELINE_DEPLOYMENT_ID environment variable is required. "
            "Please set it to the UUID of your pipeline deployment."
        )

    try:
        # Initialize the pipeline service
        pipeline_service = PipelineServingService(deployment_id)
        await pipeline_service.initialize()

        # Set up job status change callback to close streams on job completion
        job_registry = get_job_registry()
        stream_manager = await get_stream_manager()

        def close_stream_on_job_completion(
            job_id: str, status: JobStatus
        ) -> None:
            """Close job stream when job reaches final state."""
            try:
                # Use thread-safe method to close stream (works from any thread)
                stream_manager.close_stream_threadsafe(job_id)
                logger.debug(
                    f"Scheduled stream closure for job {job_id} (status: {status.value})"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to schedule stream closure for job {job_id}: {e}"
                )

        job_registry.set_status_change_callback(close_stream_on_job_completion)

        logger.info("✅ Pipeline serving service initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize pipeline service: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down ZenML Pipeline Serving service...")

    # Shutdown all services
    await shutdown_execution_manager()
    await shutdown_job_registry()
    await shutdown_stream_manager()

    pipeline_service = None


# Create FastAPI application
app = FastAPI(
    title="ZenML Pipeline Serving",
    description="Serve ZenML pipelines as FastAPI endpoints for real-time execution",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


def get_service() -> PipelineServingService:
    """Get the global pipeline service instance.

    Returns:
        The initialized pipeline service

    Raises:
        HTTPException: If service is not initialized
    """
    if not pipeline_service:
        raise HTTPException(
            status_code=503,
            detail="Pipeline service not initialized. Check service startup logs.",
        )
    return pipeline_service


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Root endpoint with service information and documentation links."""
    service = get_service()
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
            .code {{ background: #f3f4f6; padding: 10px; border-radius: 4px; }}
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
            <h2>Available Endpoints</h2>
            <ul>
                <li><strong>POST /invoke</strong> - Execute pipeline synchronously</li>
                <li><strong>WebSocket /stream</strong> - Execute pipeline with streaming updates</li>
                <li><strong>GET /health</strong> - Health check</li>
                <li><strong>GET /info</strong> - Pipeline information and schema</li>
                <li><strong>GET /metrics</strong> - Execution metrics</li>
                <li><strong>GET /status</strong> - Detailed service status</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Quick Start</h2>
            <p>Execute your pipeline:</p>
            <div class="code">
curl -X POST "http://localhost:8000/invoke" \\<br>
&nbsp;&nbsp;-H "Content-Type: application/json" \\<br>
&nbsp;&nbsp;-d '{{"parameters": {{"your_param": "value"}}}}'
            </div>
        </div>
        
        <div class="section">
            <h2>Documentation</h2>
            <p><a href="/docs">📖 Interactive API Documentation</a></p>
            <p><a href="/redoc">📋 ReDoc Documentation</a></p>
        </div>
    </body>
    </html>
    """
    return html_content


@app.post("/invoke")
async def invoke_pipeline(
    request: PipelineRequest,
    mode: str = Query("sync", description="Execution mode: 'sync' or 'async'"),
) -> PipelineResponse:
    """Execute pipeline synchronously or asynchronously.

    This endpoint executes the configured ZenML pipeline with the provided
    parameters. In sync mode, it waits for completion and returns results.
    In async mode, it returns immediately with a job ID for polling.

    Args:
        request: Pipeline execution request containing parameters and options
        mode: Execution mode - 'sync' for synchronous, 'async' for asynchronous

    Returns:
        Pipeline execution response with results (sync) or job info (async)
    """
    service = get_service()

    logger.info(
        f"Received pipeline execution request (mode={mode}): {request.model_dump()}"
    )

    try:
        if mode.lower() == "async":
            # Async mode - submit execution and return immediately
            result = await service.submit_pipeline(
                parameters=request.parameters,
                run_name=request.run_name,
                timeout=request.timeout,
            )

            # Return 202 Accepted with job information
            return PipelineResponse(
                success=result.get("success", True),
                job_id=result.get("job_id"),
                message=result.get("message", "Pipeline execution submitted"),
                metadata=result.get("metadata", {}),
            )
        else:
            # Sync mode - wait for completion
            result = await service.execute_pipeline(
                parameters=request.parameters,
                run_name=request.run_name,
                timeout=request.timeout,
            )

            return PipelineResponse(**result)

    except TooManyRequestsError as e:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": "60"},
        )
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        return PipelineResponse(
            success=False, error=f"Internal server error: {str(e)}"
        )


@app.websocket("/stream")
async def stream_pipeline(websocket: WebSocket) -> None:
    """Execute pipeline with streaming updates via WebSocket.

    This endpoint provides real-time updates during pipeline execution,
    including step-by-step progress and final results.

    TODO: Improve WebSocket implementation
    Issues:
    - No reconnection handling
    - No heartbeat/ping-pong mechanism
    - No message queuing for disconnected clients

    Solutions:
    1. Implement reconnection logic with session IDs
    2. Add ping/pong frames for connection health monitoring
    3. Use Redis or similar for message persistence during disconnections
    4. Implement exponential backoff for client reconnections
    """
    await websocket.accept()
    service = get_service()

    try:
        # Receive execution request
        data = await websocket.receive_json()
        request = PipelineRequest(**data)

        logger.info(
            f"Received streaming pipeline request: {request.model_dump()}"
        )

        # Execute pipeline with streaming updates
        async for event in service.execute_pipeline_streaming(
            parameters=request.parameters, run_name=request.run_name
        ):
            await websocket.send_json(event.model_dump())

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Streaming execution failed: {str(e)}")
        try:
            await websocket.send_json(
                {
                    "event": "error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            pass  # Connection might be closed
    finally:
        try:
            await websocket.close()
        except Exception:
            pass  # Connection might already be closed


# New async job management endpoints


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status and results of a specific job.

    Args:
        job_id: Job ID to get status for

    Returns:
        Job status information including results if completed
    """
    try:
        job_registry = get_job_registry()
        job = job_registry.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=404, detail=f"Job {job_id} not found"
            )

        return job.to_dict()

    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str, reason: Optional[str] = None
) -> Dict[str, Any]:
    """Cancel a running job.

    Args:
        job_id: Job ID to cancel
        reason: Optional reason for cancellation

    Returns:
        Cancellation confirmation
    """
    try:
        job_registry = get_job_registry()
        cancelled = job_registry.cancel_job(job_id, reason=reason)

        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} could not be cancelled (not found or already completed)",
            )

        return {
            "message": f"Job {job_id} cancelled successfully",
            "cancelled": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(100, description="Maximum number of jobs to return"),
) -> Dict[str, Any]:
    """List jobs with optional filtering.

    Args:
        status: Optional status filter (pending, running, completed, failed, canceled)
        limit: Maximum number of jobs to return

    Returns:
        List of jobs matching the criteria
    """
    try:
        job_registry = get_job_registry()

        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{status}'. Must be one of: pending, running, completed, failed, canceled",
                )

        jobs = job_registry.list_jobs(status_filter=status_filter, limit=limit)
        return {"jobs": jobs, "total": len(jobs)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream/{job_id}")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Stream events for a specific job using Server-Sent Events.

    Args:
        job_id: Job ID to stream events for

    Returns:
        SSE stream of job events
    """
    try:
        # Check if job exists
        job_registry = get_job_registry()
        job = job_registry.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=404, detail=f"Job {job_id} not found"
            )

        # Create SSE stream with proper formatting and heartbeats
        async def event_stream() -> AsyncGenerator[str, None]:
            try:
                stream_manager = await get_stream_manager()

                # SSE retry interval (5 seconds)
                yield "retry: 5000\n\n"

                # Send initial connection event with correct SSE formatting
                initial_data = {
                    "job_id": job_id,
                    "status": job.status.value,
                    "message": "Connected to job event stream",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: connected\ndata: {json.dumps(initial_data)}\n\n"

                # Track last activity for heartbeat timing
                import time

                last_activity = time.time()
                heartbeat_interval = 30  # Send heartbeat every 30 seconds

                # Stream events with timeout for heartbeats
                async for event in stream_manager.subscribe_to_job(job_id):
                    current_time = time.time()

                    # Send heartbeat if too much time has passed
                    if current_time - last_activity > heartbeat_interval:
                        heartbeat_data = {
                            "type": "heartbeat",
                            "timestamp": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "job_id": job_id,
                        }
                        yield f"event: heartbeat\ndata: {json.dumps(heartbeat_data)}\n\n"
                        last_activity = current_time

                    # Send actual event with proper SSE formatting
                    event_data = event.to_dict()
                    yield f"event: {event.event_type.value}\ndata: {json.dumps(event_data)}\n\n"
                    last_activity = current_time

                    # Break on final events
                    if event.event_type.value in [
                        "pipeline_completed",
                        "pipeline_failed",
                        "cancellation_requested",
                    ]:
                        break

                # Send final completion message
                final_data = {
                    "type": "stream_closed",
                    "message": "Event stream completed",
                    "job_id": job_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: stream_closed\ndata: {json.dumps(final_data)}\n\n"

            except Exception as e:
                logger.error(f"Error in SSE stream for job {job_id}: {e}")
                error_data = {
                    "error": str(e),
                    "job_id": job_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create SSE stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concurrency/stats")
async def concurrency_stats() -> Dict[str, Any]:
    """Get current concurrency and execution statistics.

    Returns:
        Dictionary with concurrency statistics
    """
    try:
        execution_manager = get_execution_manager()
        job_registry = get_job_registry()
        stream_manager = await get_stream_manager()

        return {
            "execution": execution_manager.get_stats(),
            "jobs": job_registry.get_stats(),
            "streams": stream_manager.get_stats(),
        }

    except Exception as e:
        logger.error(f"Failed to get concurrency stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health check endpoint.

    Returns current service health status, uptime, and basic information
    about the served pipeline.
    """
    service = get_service()

    if not service.is_healthy():
        raise HTTPException(
            status_code=503,
            detail="Service is unhealthy - deployment not loaded",
        )

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
async def pipeline_info() -> InfoResponse:
    """Get detailed pipeline information and parameter schema.

    Returns comprehensive information about the served pipeline including
    step definitions, parameter schema, and deployment details.
    """
    service = get_service()
    info = service.get_service_info()

    return InfoResponse(
        pipeline={
            "name": info["pipeline"]["name"],
            "steps": info["pipeline"]["steps"],
            "parameters": info["pipeline"]["parameters"],
        },
        deployment={
            "id": info["deployment"]["id"],
            "created_at": info["deployment"]["created_at"],
            "stack": info["deployment"]["stack"],
        },
    )


@app.get("/metrics", response_model=ExecutionMetrics)
async def execution_metrics() -> ExecutionMetrics:
    """Get pipeline execution metrics and statistics.

    Returns detailed metrics about pipeline executions including success rates,
    execution times, and recent activity.
    """
    service = get_service()
    metrics = service.get_execution_metrics()

    return ExecutionMetrics(**metrics)


@app.get("/status", response_model=ServiceStatus)
async def service_status() -> ServiceStatus:
    """Get detailed service status information.

    Returns comprehensive status including service configuration, deployment
    information, and runtime details.
    """
    service = get_service()
    info = service.get_service_info()

    return ServiceStatus(
        service_name="ZenML Pipeline Serving",
        version="0.1.0",
        deployment_id=info["service"]["deployment_id"],
        status="running" if service.is_healthy() else "unhealthy",
        started_at=datetime.fromtimestamp(service_start_time, tz=timezone.utc)
        if service_start_time
        else datetime.now(timezone.utc),
        configuration={
            "deployment_id": os.getenv("ZENML_PIPELINE_DEPLOYMENT_ID"),
            "host": os.getenv("ZENML_SERVICE_HOST", "0.0.0.0"),
            "port": int(os.getenv("ZENML_SERVICE_PORT", "8000")),
            "log_level": os.getenv("ZENML_LOG_LEVEL", "INFO"),
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
    port = int(os.getenv("ZENML_SERVICE_PORT", "8000"))
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
