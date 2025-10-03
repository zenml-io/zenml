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
"""Kubernetes orchestrator flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import (
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
)

from zenml.config.base_settings import BaseSettings
from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
from zenml.integrations.kubernetes import KUBERNETES_ORCHESTRATOR_FLAVOR
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import ServiceConnectorRequirements
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.orchestrators import (
        KubernetesOrchestrator,
    )


class KubernetesOrchestratorSettings(BaseSettings):
    """Settings for the Kubernetes orchestrator.

    Configuration options for how pipelines are executed on Kubernetes clusters.
    Field descriptions are defined inline using Field() descriptors.
    """

    synchronous: bool = Field(
        default=True,
        description="Whether to wait for all pipeline steps to complete. "
        "When `False`, the client returns immediately and execution continues asynchronously.",
    )
    service_account_name: Optional[str] = Field(
        default=None,
        description="Kubernetes service account for the orchestrator pod. "
        "If not specified, creates a new account with 'edit' permissions.",
    )
    step_pod_service_account_name: Optional[str] = Field(
        default=None,
        description="Kubernetes service account for step execution pods. "
        "Uses the default service account if not specified.",
    )
    privileged: bool = Field(
        default=False,
        description="Whether to run containers in privileged mode with extended permissions.",
    )
    pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod configuration for step execution containers.",
    )
    orchestrator_pod_settings: Optional[KubernetesPodSettings] = Field(
        default=None,
        description="Pod configuration for the orchestrator container that launches step pods.",
    )
    job_name_prefix: Optional[str] = Field(
        default=None,
        description="Prefix for the job name.",
    )
    max_parallelism: Optional[PositiveInt] = Field(
        default=None,
        description="Maximum number of step pods to run concurrently. No limit if not specified.",
    )
    successful_jobs_history_limit: Optional[NonNegativeInt] = Field(
        default=None,
        description="Number of successful scheduled jobs to retain in history.",
    )
    failed_jobs_history_limit: Optional[NonNegativeInt] = Field(
        default=None,
        description="Number of failed scheduled jobs to retain in history.",
    )
    ttl_seconds_after_finished: Optional[NonNegativeInt] = Field(
        default=None,
        description="Seconds to keep finished jobs before automatic cleanup.",
    )
    active_deadline_seconds: Optional[NonNegativeInt] = Field(
        default=None,
        description="Job deadline in seconds. If the job doesn't finish "
        "within this time, it will be terminated.",
    )
    backoff_limit_margin: NonNegativeInt = Field(
        default=0,
        description="The value to add to the backoff limit in addition "
        "to the step retries. The retry configuration defined on the step "
        "defines the maximum number of retries that the server will accept "
        "for a step. For this orchestrator, this controls how often the "
        "job running the step will try to start the step pod. There are some "
        "circumstances however where the job will start the pod, but the pod "
        "doesn't actually get to the point of running the step. That means "
        "the server will not receive the maximum amount of retry requests, "
        "which in turn causes other inconsistencies like wrong step statuses. "
        "To mitigate this, this attribute allows to add a margin to the "
        "backoff limit. This means that the job will retry the pod startup "
        "for the configured amount of times plus the margin, which increases "
        "the chance of the server receiving the maximum amount of retry "
        "requests.",
    )
    orchestrator_job_backoff_limit: NonNegativeInt = Field(
        default=3,
        description="The backoff limit for the orchestrator job.",
    )
    fail_on_container_waiting_reasons: Optional[List[str]] = Field(
        default=[
            "InvalidImageName",
            "ErrImagePull",
            "ImagePullBackOff",
            "CreateContainerConfigError",
        ],
        description="List of container waiting reasons that should cause the "
        "job to fail immediately. This should be set to a list of "
        "nonrecoverable reasons, which if found in any "
        "`pod.status.containerStatuses[*].state.waiting.reason` of a job pod, "
        "should cause the job to fail immediately.",
    )
    job_monitoring_interval: PositiveFloat = Field(
        default=3,
        description="The interval in seconds to monitor the job. Each interval "
        "is used to check for container issues for the job pods.",
    )
    job_monitoring_delay: PositiveFloat = Field(
        default=0.0,
        description="The delay in seconds to wait between monitoring active "
        "step jobs. This can be used to reduce load on the Kubernetes API "
        "server.",
    )
    interrupt_check_interval: PositiveFloat = Field(
        default=1.0,
        description="The interval in seconds to check for run interruptions.",
        ge=0.5,
    )
    pod_failure_policy: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The pod failure policy to use for the job that is "
        "executing the step.",
    )
    prevent_orchestrator_pod_caching: bool = Field(
        default=False,
        description="Whether to disable caching optimization in the orchestrator pod.",
    )
    always_build_pipeline_image: bool = Field(
        default=False,
        description="If `True`, the orchestrator will always build the pipeline image, "
        "even if all steps have a custom build.",
    )
    pod_stop_grace_period: PositiveInt = Field(
        default=30,
        description="When stopping a pipeline run, the amount of seconds to wait for a step pod to shutdown gracefully.",
    )

    # Deprecated fields
    timeout: Optional[int] = Field(
        default=None,
        deprecated=True,
        description="DEPRECATED/UNUSED.",
    )
    stream_step_logs: Optional[bool] = Field(
        default=None,
        deprecated=True,
        description="DEPRECATED/UNUSED.",
    )
    pod_startup_timeout: Optional[int] = Field(
        default=None,
        description="DEPRECATED/UNUSED.",
        deprecated=True,
    )
    pod_failure_max_retries: Optional[int] = Field(
        default=None,
        description="DEPRECATED/UNUSED.",
        deprecated=True,
    )
    pod_failure_retry_delay: Optional[int] = Field(
        default=None,
        description="DEPRECATED/UNUSED.",
        deprecated=True,
    )
    pod_failure_backoff: Optional[float] = Field(
        default=None,
        description="DEPRECATED/UNUSED.",
        deprecated=True,
    )
    pod_name_prefix: Optional[str] = Field(
        default=None,
        deprecated=True,
        description="DEPRECATED/UNUSED.",
    )

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        "timeout",
        "stream_step_logs",
        "pod_startup_timeout",
        "pod_failure_max_retries",
        "pod_failure_retry_delay",
        "pod_failure_backoff",
        ("pod_name_prefix", "job_name_prefix"),
    )

    @field_validator("pod_failure_policy", mode="before")
    @classmethod
    def _convert_pod_failure_policy(cls, value: Any) -> Any:
        """Converts Kubernetes pod failure policy to a dict.

        Args:
            value: The pod failure policy value.

        Returns:
            The converted value.
        """
        from kubernetes.client.models import V1PodFailurePolicy

        from zenml.integrations.kubernetes import serialization_utils

        if isinstance(value, V1PodFailurePolicy):
            return serialization_utils.serialize_kubernetes_model(value)
        else:
            return value


class KubernetesOrchestratorConfig(
    BaseOrchestratorConfig, KubernetesOrchestratorSettings
):
    """Configuration for the Kubernetes orchestrator."""

    incluster: bool = Field(
        False,
        description="If `True`, the orchestrator will run the pipeline inside the "
        "same cluster in which it itself is running. This requires the client "
        "to run in a Kubernetes pod itself. If set, the `kubernetes_context` "
        "config option is ignored. If the stack component is linked to a "
        "Kubernetes service connector, this field is ignored.",
    )
    kubernetes_context: Optional[str] = Field(
        None,
        description="Name of a Kubernetes context to run pipelines in. "
        "If the stack component is linked to a Kubernetes service connector, "
        "this field is ignored. Otherwise, it is mandatory.",
    )
    kubernetes_namespace: str = Field(
        "zenml",
        description="Name of the Kubernetes namespace to be used. "
        "If not provided, `zenml` namespace will be used.",
    )
    local: bool = Field(
        False,
        description="If `True`, the orchestrator will assume it is connected to a "
        "local kubernetes cluster and will perform additional validations and "
        "operations to allow using the orchestrator in combination with other "
        "local stack components that store data in the local filesystem "
        "(i.e. it will mount the local stores directory into the pipeline containers).",
    )
    skip_local_validations: bool = Field(
        False, description="If `True`, the local validations will be skipped."
    )
    parallel_step_startup_waiting_period: Optional[float] = Field(
        None,
        description="How long to wait in between starting parallel steps. "
        "This can be used to distribute server load when running pipelines "
        "with a huge amount of parallel steps.",
    )
    pass_zenml_token_as_secret: bool = Field(
        False,
        description="If `True`, the ZenML token will be passed as a Kubernetes secret "
        "to the pods. For this to work, the Kubernetes client must have permissions "
        "to create secrets in the namespace.",
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
        return not self.local

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return self.local

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

    @property
    def supports_client_side_caching(self) -> bool:
        """Whether the orchestrator supports client side caching.

        Returns:
            Whether the orchestrator supports client side caching.
        """
        # The Kubernetes orchestrator starts step pods from a pipeline pod.
        # This is currently not supported when using client-side caching.
        return False

    @property
    def handles_step_retries(self) -> bool:
        """Whether the orchestrator handles step retries.

        Returns:
            Whether the orchestrator handles step retries.
        """
        return True


class KubernetesOrchestratorFlavor(BaseOrchestratorFlavor):
    """Kubernetes orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return KUBERNETES_ORCHESTRATOR_FLAVOR

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
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png"

    @property
    def config_class(self) -> Type[KubernetesOrchestratorConfig]:
        """Returns `KubernetesOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return KubernetesOrchestratorConfig

    @property
    def implementation_class(self) -> Type["KubernetesOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kubernetes.orchestrators import (
            KubernetesOrchestrator,
        )

        return KubernetesOrchestrator
