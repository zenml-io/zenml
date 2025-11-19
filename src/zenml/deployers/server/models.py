#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""FastAPI application models."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.logger import get_logger

logger = get_logger(__name__)


class DeploymentInvocationResponseMetadata(BaseModel):
    """Pipeline invoke response metadata model."""

    deployment_id: UUID = Field(title="The ID of the deployment.")
    deployment_name: str = Field(title="The name of the deployment.")
    snapshot_id: UUID = Field(title="The ID of the snapshot.")
    snapshot_name: Optional[str] = Field(
        default=None, title="The name of the snapshot."
    )
    pipeline_name: str = Field(title="The name of the pipeline.")
    run_id: Optional[UUID] = Field(
        default=None, title="The ID of the pipeline run."
    )
    run_name: Optional[str] = Field(
        default=None, title="The name of the pipeline run."
    )
    parameters_used: Dict[str, Any] = Field(
        title="The parameters used for the pipeline execution."
    )


class BaseDeploymentInvocationRequest(BaseModel):
    """Base pipeline invoke request model."""

    parameters: BaseModel = Field(
        title="The parameters for the pipeline execution."
    )
    run_name: Optional[str] = Field(
        default=None, title="Custom name for the pipeline run."
    )
    timeout: int = Field(
        default=300, title="The timeout for the pipeline execution."
    )
    skip_artifact_materialization: bool = Field(
        default=False,
        title="Whether to keep outputs in memory for fast access instead of "
        "storing them as artifacts.",
    )


class BaseDeploymentInvocationResponse(BaseModel):
    """Base pipeline invoke response model."""

    success: bool = Field(
        title="Whether the pipeline execution was successful."
    )
    outputs: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The outputs of the pipeline execution, if the pipeline execution "
        "was successful.",
    )
    execution_time: float = Field(
        title="The time taken to execute the pipeline."
    )
    metadata: DeploymentInvocationResponseMetadata = Field(
        title="The metadata of the pipeline execution."
    )
    error: Optional[str] = Field(
        default=None,
        title="The error that occurred, if the pipeline invocation failed.",
    )


class PipelineInfo(BaseModel):
    """Pipeline info model."""

    name: str = Field(title="The name of the pipeline.")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, title="The parameters of the pipeline."
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, title="The input schema of the pipeline."
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, title="The output schema of the pipeline."
    )


class DeploymentInfo(BaseModel):
    """Deployment info model."""

    id: UUID = Field(title="The ID of the deployment.")
    name: str = Field(title="The name of the deployment.")
    auth_enabled: bool = Field(
        title="Whether the deployment is authenticated."
    )


class SnapshotInfo(BaseModel):
    """Snapshot info model."""

    id: UUID = Field(title="The ID of the snapshot.")
    name: Optional[str] = Field(
        default=None, title="The name of the snapshot."
    )


class AppInfo(BaseModel):
    """App info model."""

    app_runner_flavor: str
    docs_url_path: str
    redoc_url_path: str
    invoke_url_path: str
    health_url_path: str
    info_url_path: str
    metrics_url_path: str


class ServiceInfo(BaseModel):
    """Service info model."""

    deployment: DeploymentInfo = Field(
        title="The deployment of the pipeline service."
    )
    snapshot: SnapshotInfo = Field(
        title="The snapshot of the pipeline service."
    )
    pipeline: PipelineInfo = Field(
        title="The pipeline of the pipeline service."
    )
    app: AppInfo = Field(title="The deployment application")
    total_executions: int = Field(
        title="The total number of pipeline executions."
    )
    last_execution_time: Optional[datetime] = Field(
        default=None, title="The time of the last pipeline execution."
    )
    status: str = Field(title="The status of the pipeline service.")
    uptime: float = Field(title="The uptime of the pipeline service.")


class ExecutionMetrics(BaseModel):
    """Execution metrics model."""

    total_executions: int = Field(
        title="The total number of pipeline executions."
    )
    last_execution_time: Optional[datetime] = Field(
        default=None, title="The time of the last pipeline execution."
    )
