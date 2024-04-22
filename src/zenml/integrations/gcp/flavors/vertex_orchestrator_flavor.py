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

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp import (
    GCP_RESOURCE_TYPE,
    GCP_VERTEX_ORCHESTRATOR_FLAVOR,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.gcp.orchestrators import VertexOrchestrator


class VertexOrchestratorSettings(BaseSettings):
    """Settings for the Vertex orchestrator.

    Attributes:
        synchronous: If `True`, the client running a pipeline using this
            orchestrator waits until all steps finish running. If `False`,
            the client returns immediately and the pipeline is executed
            asynchronously. Defaults to `True`.
        labels: Labels to assign to the pipeline job.
        node_selector_constraint: Each constraint is a key-value pair label.
            For the container to be eligible to run on a node, the node must have
            each of the constraints appeared as labels.
            For example a GPU type can be providing by one of the following tuples:
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_A100")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_K80")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_P4")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_P100")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_T4")
                - ("cloud.google.com/gke-accelerator", "NVIDIA_TESLA_V100")
            Hint: the selected region (location) must provide the requested accelerator
            (see https://cloud.google.com/compute/docs/gpus/gpu-regions-zones).
        pod_settings: Pod settings to apply.
    """

    labels: Dict[str, str] = {}
    synchronous: bool = True
    node_selector_constraint: Optional[Tuple[str, str]] = None
    pod_settings: Optional[KubernetesPodSettings] = None

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
    """Configuration for the Vertex orchestrator.

    Attributes:
        location: Name of GCP region where the pipeline job will be executed.
            Vertex AI Pipelines is available in the following regions:
            https://cloud.google.com/vertex-ai/docs/general/locations#feature-availability
        pipeline_root: a Cloud Storage URI that will be used by the Vertex AI
            Pipelines. If not provided but the artifact store in the stack used
            to execute the pipeline is a
            `zenml.integrations.gcp.artifact_stores.GCPArtifactStore`,
            then a subdirectory of the artifact store will be used.
        encryption_spec_key_name: The Cloud KMS resource identifier of the
            customer managed encryption key used to protect the job. Has the form:
            `projects/<PRJCT>/locations/<REGION>/keyRings/<KR>/cryptoKeys/<KEY>`
            . The key needs to be in the same region as where the compute
            resource is created.
        workload_service_account: the service account for workload run-as
            account. Users submitting jobs must have act-as permission on this
            run-as account. If not provided, the Compute Engine default service
            account for the GCP project in which the pipeline is running is
            used.
        function_service_account: the service account for cloud function run-as
            account, for scheduled pipelines. This service account must have
            the act-as permission on the workload_service_account.
            If not provided, the Compute Engine default service account for the
            GCP project in which the pipeline is running is used.
        scheduler_service_account: the service account used by the Google Cloud
            Scheduler to trigger and authenticate to the pipeline Cloud Function
            on a schedule. If not provided, the Compute Engine default service
            account for the GCP project in which the pipeline is running is
            used.
        network: the full name of the Compute Engine Network to which the job
            should be peered. For example, `projects/12345/global/networks/myVPC`
            If not provided, the job will not be peered with any network.
        cpu_limit: The maximum CPU limit for this operator. This string value
            can be a number (integer value for number of CPUs) as string,
            or a number followed by "m", which means 1/1000. You can specify
            at most 96 CPUs.
            (see. https://cloud.google.com/vertex-ai/docs/pipelines/machine-types)
        memory_limit: The maximum memory limit for this operator. This string
            value can be a number, or a number followed by "K" (kilobyte),
            "M" (megabyte), or "G" (gigabyte). At most 624GB is supported.
        gpu_limit: The GPU limit (positive number) for the operator.
            For more information about GPU resources, see:
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#specifying_gpus
    """

    location: str
    pipeline_root: Optional[str] = None
    encryption_spec_key_name: Optional[str] = None
    workload_service_account: Optional[str] = None
    function_service_account: Optional[str] = None
    scheduler_service_account: Optional[str] = None
    network: Optional[str] = None

    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    gpu_limit: Optional[int] = None

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
