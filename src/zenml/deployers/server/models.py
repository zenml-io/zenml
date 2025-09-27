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
"""FastAPI application models."""

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Dict, Optional, Tuple, Type
from uuid import UUID

from pydantic import BaseModel, Field, WithJsonSchema

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.deployers.server.service import PipelineDeploymentService


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


class SnapshotInfo(BaseModel):
    """Snapshot info model."""

    id: UUID = Field(title="The ID of the snapshot.")
    name: Optional[str] = Field(
        default=None, title="The name of the snapshot."
    )


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


def get_pipeline_invoke_models(
    service: "PipelineDeploymentService",
) -> Tuple[Type[BaseModel], Type[BaseModel]]:
    """Generate the request and response models for the pipeline invoke endpoint.

    Args:
        service: The pipeline deployment service.

    Returns:
        A tuple containing the request and response models.
    """
    if TYPE_CHECKING:
        # mypy has a difficult time with dynamic models, so we return something
        # static for mypy to use
        return BaseModel, BaseModel

    else:

        class PipelineInvokeRequest(BaseDeploymentInvocationRequest):
            parameters: Annotated[
                service.input_model,
                WithJsonSchema(service.input_schema, mode="validation"),
            ]

        class PipelineInvokeResponse(BaseDeploymentInvocationResponse):
            outputs: Annotated[
                Optional[Dict[str, Any]],
                WithJsonSchema(service.output_schema, mode="serialization"),
            ]

        return PipelineInvokeRequest, PipelineInvokeResponse
