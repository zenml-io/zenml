#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Vertex orchestrator flavor."""

from typing import TYPE_CHECKING, Dict, Optional, Tuple, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp import (
    GCP_RESOURCE_TYPE,
    GCP_VERTEX_ORCHESTRATOR_FLAVOR,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.integrations.gcp.vertex_custom_job_parameters import (
    VertexCustomJobParameters,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.gcp.orchestrators import VertexOrchestrator


class VertexOrchestratorSettings(BaseSettings):
    """Settings for the Vertex orchestrator."""

    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to assign to the pipeline job. "
        "Example: {'environment': 'production', 'team': 'ml-ops'}",
    )
    synchronous: bool = Field(
        True,
        description="If `True`, the client running a pipeline using this "
        "orchestrator waits until all steps finish running. If `False`, "
        "the client returns immediately and the pipeline is executed "
        "asynchronously.",
    )
    node_selector_constraint: Optional[Tuple[str, str]] = Field(
        None,
        description="Each constraint is a key-value pair label. For the container "
        "to be eligible to run on a node, the node must have each of the "
        "constraints appeared as labels. For example, a GPU type can be provided "
        "by ('cloud.google.com/gke-accelerator', 'NVIDIA_TESLA_T4')."
        "Hint: the selected region (location) must provide the requested accelerator"
        "(see https://cloud.google.com/compute/docs/gpus/gpu-regions-zones).",
    )
    pod_settings: Optional[KubernetesPodSettings] = Field(
        None,
        description="Pod settings to apply to the orchestrator and step pods.",
    )

    custom_job_parameters: Optional[VertexCustomJobParameters] = Field(
        None, description="Custom parameters for the Vertex AI custom job."
    )

    _node_selector_deprecation = (
        deprecation_utils.deprecate_pydantic_attributes(
            "node_selector_constraint"
        )
    )


class VertexOrchestratorConfig(
    BaseOrchestratorConfig,
    GoogleCredentialsConfigMixin,
    VertexOrchestratorSettings,
):
    """Configuration for the Vertex orchestrator."""

    location: str = Field(
        ...,
        description="Name of GCP region where the pipeline job will be executed. "
        "Vertex AI Pipelines is available in specific regions: "
        "https://cloud.google.com/vertex-ai/docs/general/locations#feature-availability",
    )
    pipeline_root: Optional[str] = Field(
        None,
        description="A Cloud Storage URI that will be used by the Vertex AI Pipelines. "
        "If not provided but the artifact store in the stack is a GCPArtifactStore, "
        "then a subdirectory of the artifact store will be used.",
    )
    encryption_spec_key_name: Optional[str] = Field(
        None,
        description="The Cloud KMS resource identifier of the customer managed "
        "encryption key used to protect the job. Has the form: "
        "projects/<PROJECT>/locations/<REGION>/keyRings/<KR>/cryptoKeys/<KEY>. "
        "The key needs to be in the same region as where the compute resource is created.",
    )
    workload_service_account: Optional[str] = Field(
        None,
        description="The service account for workload run-as account. Users submitting "
        "jobs must have act-as permission on this run-as account. If not provided, "
        "the Compute Engine default service account for the GCP project is used.",
    )
    network: Optional[str] = Field(
        None,
        description="The full name of the Compute Engine Network to which the job "
        "should be peered. For example, 'projects/12345/global/networks/myVPC'. "
        "If not provided, the job will not be peered with any network.",
    )
    private_service_connect: Optional[str] = Field(
        None,
        description="The full name of a Private Service Connect endpoint to which "
        "the job should be peered. For example, "
        "'projects/12345/regions/us-central1/networkAttachments/NETWORK_ATTACHMENT_NAME'. "
        "If not provided, the job will not be peered with any private service connect endpoint.",
    )

    # Deprecated
    cpu_limit: Optional[str] = Field(
        None,
        description="DEPRECATED: The maximum CPU limit for this operator. "
        "Use custom_job_parameters or pod_settings instead.",
    )
    memory_limit: Optional[str] = Field(
        None,
        description="DEPRECATED: The maximum memory limit for this operator. "
        "Use custom_job_parameters or pod_settings instead.",
    )
    gpu_limit: Optional[int] = Field(
        None,
        description="DEPRECATED: The GPU limit for the operator. "
        "Use custom_job_parameters or pod_settings instead.",
    )
    function_service_account: Optional[str] = Field(
        None,
        description="DEPRECATED: The service account for cloud function run-as account, "
        "for scheduled pipelines. This functionality is no longer supported.",
    )
    scheduler_service_account: Optional[str] = Field(
        None,
        description="DEPRECATED: The service account used by the Google Cloud Scheduler "
        "to trigger and authenticate to the pipeline Cloud Function on a schedule. "
        "This functionality is no longer supported.",
    )

    _resource_deprecation = deprecation_utils.deprecate_pydantic_attributes(
        "cpu_limit",
        "memory_limit",
        "gpu_limit",
        "function_service_account",
        "scheduler_service_account",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return self.synchronous

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return True


class VertexOrchestratorFlavor(BaseOrchestratorFlavor):
    """Vertex Orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return GCP_VERTEX_ORCHESTRATOR_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(
            resource_type=GCP_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/vertexai.png"

    @property
    def config_class(self) -> Type[VertexOrchestratorConfig]:
        """Returns VertexOrchestratorConfig config class.

        Returns:
                The config class.
        """
        return VertexOrchestratorConfig

    @property
    def implementation_class(self) -> Type["VertexOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.gcp.orchestrators import VertexOrchestrator

        return VertexOrchestrator
