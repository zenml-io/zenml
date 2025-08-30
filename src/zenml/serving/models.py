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
"""Pydantic models for pipeline serving API."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PipelineRequest(BaseModel):
    """Request model for pipeline execution."""

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the pipeline execution. These will be "
        "merged with deployment parameters, with request parameters taking priority.",
    )
    run_name: Optional[str] = Field(
        default=None,
        description="Optional custom name for this pipeline run. If not provided, "
        "a name will be auto-generated based on timestamp.",
    )
    timeout: Optional[int] = Field(
        default=300,
        description="Maximum execution time in seconds. Pipeline will be terminated "
        "if it exceeds this timeout. Default is 300 seconds (5 minutes).",
        ge=1,
        le=3600,  # Max 1 hour
    )
    capture_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override capture policy for this specific request. Can specify "
        "'mode', 'artifacts', 'sample_rate', 'max_bytes', or 'redact' to override "
        "endpoint defaults. Takes highest precedence in policy resolution.",
    )


class PipelineResponse(BaseModel):
    """Response model for pipeline execution."""

    success: bool = Field(
        description="Whether the pipeline execution was successful"
    )
    job_id: Optional[str] = Field(
        default=None,
        description="Job ID for tracking execution status and streaming events",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="UUID of the pipeline run if execution was initiated",
    )
    results: Optional[Any] = Field(
        default=None,
        description="Pipeline execution results including final outputs",
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    execution_time: Optional[float] = Field(
        default=None, description="Total execution time in seconds"
    )
    message: Optional[str] = Field(
        default=None, description="Human-readable status message"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional execution metadata including step count, "
        "artifacts created, etc.",
    )


class StreamEvent(BaseModel):
    """Model for streaming pipeline execution events."""

    event: str = Field(
        description="Event type: 'step_started', 'step_completed', 'pipeline_completed', 'error'"
    )
    step_name: Optional[str] = Field(
        default=None, description="Name of the step if event is step-related"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Event-specific data such as step outputs or progress",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred",
    )
    error: Optional[str] = Field(
        default=None, description="Error message if event represents a failure"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(
        description="Health status: 'healthy', 'unhealthy', 'degraded'"
    )
    deployment_id: str = Field(
        description="ID of the pipeline deployment being served"
    )
    pipeline_name: str = Field(description="Name of the pipeline")
    uptime: float = Field(description="Service uptime in seconds")
    last_execution: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last successful pipeline execution",
    )


class PipelineInfo(BaseModel):
    """Model for pipeline information."""

    name: str = Field(description="Pipeline name")
    steps: list[str] = Field(
        description="List of step names in execution order"
    )
    parameters: Dict[str, Any] = Field(
        description="Parameter schema with types and defaults"
    )


class DeploymentInfo(BaseModel):
    """Model for deployment information."""

    id: str = Field(description="Deployment UUID")
    created_at: datetime = Field(description="When the deployment was created")
    stack: str = Field(description="Stack name used for this deployment")


class InfoResponse(BaseModel):
    """Response model for pipeline info endpoint."""

    pipeline: PipelineInfo = Field(description="Pipeline information")
    deployment: DeploymentInfo = Field(description="Deployment information")


class ExecutionMetrics(BaseModel):
    """Model for execution metrics and statistics."""

    total_executions: int = Field(
        description="Total number of pipeline executions attempted"
    )
    successful_executions: int = Field(
        description="Number of successful pipeline executions"
    )
    failed_executions: int = Field(
        description="Number of failed pipeline executions"
    )
    success_rate: float = Field(
        description="Success rate as a percentage (0.0 to 1.0)"
    )
    average_execution_time: float = Field(
        description="Average execution time in seconds"
    )
    last_24h_executions: Optional[int] = Field(
        default=None, description="Number of executions in the last 24 hours"
    )


class ServiceStatus(BaseModel):
    """Model for service status information."""

    service_name: str = Field(description="Name of the serving service")
    version: str = Field(description="Service version")
    deployment_id: str = Field(description="Pipeline deployment ID")
    status: str = Field(description="Service status")
    started_at: datetime = Field(description="When the service was started")
    configuration: Dict[str, Any] = Field(
        description="Service configuration parameters"
    )
