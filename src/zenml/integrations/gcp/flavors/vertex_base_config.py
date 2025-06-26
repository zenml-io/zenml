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
"""Shared configuration classes for Vertex AI components."""

from typing import Any, Dict, Optional, Sequence

from pydantic import BaseModel, Field

from zenml.config.base_settings import BaseSettings


class VertexAIContainerSpec(BaseModel):
    """Container specification for Vertex AI models and endpoints."""

    image_uri: Optional[str] = Field(
        None, description="Docker image URI for model serving"
    )
    command: Optional[Sequence[str]] = Field(
        None, description="Container command to run"
    )
    args: Optional[Sequence[str]] = Field(
        None, description="Container command arguments"
    )
    env: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    ports: Optional[Sequence[int]] = Field(
        None, description="Container ports to expose"
    )
    predict_route: Optional[str] = Field(
        None, description="HTTP path for prediction requests"
    )
    health_route: Optional[str] = Field(
        None, description="HTTP path for health check requests"
    )


class VertexAIResourceSpec(BaseModel):
    """Resource specification for Vertex AI deployments."""

    machine_type: Optional[str] = Field(
        None, description="Compute instance machine type"
    )
    accelerator_type: Optional[str] = Field(
        None, description="Hardware accelerator type"
    )
    accelerator_count: Optional[int] = Field(
        None, description="Number of accelerators"
    )
    min_replica_count: Optional[int] = Field(
        1, description="Minimum number of replicas"
    )
    max_replica_count: Optional[int] = Field(
        1, description="Maximum number of replicas"
    )


class VertexAIExplanationSpec(BaseModel):
    """Explanation configuration for Vertex AI models."""

    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Explanation metadata"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Explanation parameters"
    )


class VertexAIBaseConfig(BaseModel):
    """Base configuration shared by Vertex AI components.

    Reference:
    - https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.models
    - https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.endpoints
    """

    # Basic settings
    location: str = Field(
        "us-central1", description="GCP region for Vertex AI resources"
    )
    project_id: Optional[str] = Field(
        None, description="Optional project ID override"
    )

    # Container configuration
    container: Optional[VertexAIContainerSpec] = Field(
        None, description="Container configuration"
    )

    # Resource configuration
    resources: Optional[VertexAIResourceSpec] = Field(
        None, description="Resource configuration"
    )

    # Service configuration
    service_account: Optional[str] = Field(
        None, description="Service account email"
    )
    network: Optional[str] = Field(None, description="VPC network")

    # Security
    encryption_spec_key_name: Optional[str] = Field(
        None, description="Customer-managed encryption key"
    )

    # Monitoring and logging
    enable_access_logging: Optional[bool] = Field(
        None, description="Enable access logging"
    )
    disable_container_logging: Optional[bool] = Field(
        None, description="Disable container logging"
    )

    # Model explanation
    explanation: Optional[VertexAIExplanationSpec] = Field(
        None, description="Model explanation configuration"
    )

    # Labels and metadata
    labels: Optional[Dict[str, str]] = Field(
        None, description="Resource labels"
    )
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Custom metadata"
    )


class VertexAIModelConfig(VertexAIBaseConfig):
    """Configuration specific to Vertex AI Models."""

    # Model metadata
    display_name: Optional[str] = None
    description: Optional[str] = None
    version_description: Optional[str] = None
    version_aliases: Optional[Sequence[str]] = None

    # Model artifacts
    artifact_uri: Optional[str] = None
    model_source_spec: Optional[Dict[str, Any]] = None

    # Model versioning
    is_default_version: Optional[bool] = None

    # Model formats
    supported_deployment_resources_types: Optional[Sequence[str]] = None
    supported_input_storage_formats: Optional[Sequence[str]] = None
    supported_output_storage_formats: Optional[Sequence[str]] = None

    # Training metadata
    training_pipeline_display_name: Optional[str] = None
    training_pipeline_id: Optional[str] = None

    # Model optimization
    model_source_info: Optional[Dict[str, str]] = None
    original_model_info: Optional[Dict[str, str]] = None
    containerized_model_optimization: Optional[Dict[str, Any]] = None


class VertexAIEndpointConfig(VertexAIBaseConfig):
    """Configuration specific to Vertex AI Endpoints."""

    # Endpoint metadata
    display_name: Optional[str] = None
    description: Optional[str] = None

    # Traffic configuration
    traffic_split: Optional[Dict[str, int]] = None
    traffic_percentage: Optional[int] = 0

    # Autoscaling
    autoscaling_target_cpu_utilization: Optional[float] = None
    autoscaling_target_accelerator_duty_cycle: Optional[float] = None

    # Deployment
    sync: Optional[bool] = False
    deploy_request_timeout: Optional[int] = None
    existing_endpoint: Optional[str] = None


class VertexAIBaseSettings(BaseSettings):
    """Base settings for Vertex AI components."""

    location: str = Field(
        "us-central1", description="Default GCP region for Vertex AI resources"
    )
    project_id: Optional[str] = Field(
        None, description="Optional project ID override"
    )
