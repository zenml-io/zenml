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
"""Implementation of the Run:AI deployer."""

import re
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Tuple, Type, cast
from uuid import UUID

from pydantic import BaseModel
from runai.models.annotation import Annotation
from runai.models.auto_scaling import AutoScaling
from runai.models.environment_variable import EnvironmentVariable
from runai.models.image_pull_policy import ImagePullPolicy
from runai.models.image_pull_secret import ImagePullSecret
from runai.models.inference_creation_request import InferenceCreationRequest
from runai.models.inference_spec_spec import InferenceSpecSpec
from runai.models.label import Label
from runai.models.serving_port import ServingPort
from runai.models.serving_port_protocol import ServingPortProtocol
from runai.models.superset_spec_all_of_compute import SupersetSpecAllOfCompute

from zenml.config.base_settings import BaseSettings
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.deployers.server.entrypoint_configuration import (
    DEPLOYMENT_ID_OPTION,
    DeploymentEntrypointConfiguration,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.integrations.runai.client.runai_client import (
    RunAIClient,
    RunAIClientError,
    RunAICluster,
    RunAIProject,
    RunAIWorkloadNotFoundError,
)
from zenml.integrations.runai.constants import (
    MAX_WORKLOAD_NAME_LENGTH,
    map_runai_inference_status_to_deployment_status,
)
from zenml.integrations.runai.flavors.runai_deployer_flavor import (
    RunAIDeployerConfig,
    RunAIDeployerSettings,
)
from zenml.logger import get_logger
from zenml.models import DeploymentOperationalState, DeploymentResponse
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)


class RunAIDeploymentMetadata(BaseModel):
    """Metadata for a Run:AI inference deployment."""

    workload_id: Optional[str] = None
    workload_name: Optional[str] = None
    endpoint_url: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    cluster_id: Optional[str] = None
    cluster_name: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    cpu: Optional[float] = None
    memory: Optional[str] = None
    gpu_devices: Optional[int] = None
    gpu_portion: Optional[float] = None

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "RunAIDeploymentMetadata":
        """Create metadata from a deployment.

        Args:
            deployment: The deployment to get the metadata for.

        Returns:
            The metadata for the deployment.
        """
        return cls.model_validate(deployment.deployment_metadata)


class RunAIDeployer(ContainerizedDeployer):
    """Deployer responsible for Run:AI inference workloads."""

    _client: Optional[RunAIClient] = None

    @property
    def config(self) -> RunAIDeployerConfig:
        """Returns the `RunAIDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(RunAIDeployerConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Run:AI deployer.

        Returns:
            The settings class.
        """
        return RunAIDeployerSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is an image builder and container registry in the stack.

        Returns:
            A `StackValidator` instance.
        """
        return StackValidator(
            required_components={
                StackComponentType.IMAGE_BUILDER,
                StackComponentType.CONTAINER_REGISTRY,
            }
        )

    @property
    def client(self) -> RunAIClient:
        """Get or create the Run:AI client.

        Returns:
            The Run:AI client.
        """
        if self._client is None:
            self._client = RunAIClient(
                client_id=self.config.client_id.get_secret_value(),
                client_secret=self.config.client_secret.get_secret_value(),
                runai_base_url=self.config.runai_base_url,
            )
        return self._client

    def _resolve_project_and_cluster(self) -> Tuple[RunAIProject, RunAICluster]:
        """Resolve the Run:AI project and cluster for workload submission.

        Returns:
            Tuple of (project, cluster).

        Raises:
            DeployerError: If project or cluster lookup fails.
        """
        try:
            project = self.client.get_project_by_name(self.config.project_name)
        except RunAIClientError as exc:
            raise DeployerError(
                f"Failed to find Run:AI project '{self.config.project_name}': {exc}"
            ) from exc

        cluster_id = project.cluster_id
        cluster: Optional[RunAICluster] = None

        if cluster_id:
            cluster = self.client.get_cluster_by_id(cluster_id)
            if not cluster:
                raise DeployerError(
                    f"Project cluster ID '{cluster_id}' not found"
                )
            if (
                self.config.cluster_name
                and cluster.name != self.config.cluster_name
            ):
                logger.warning(
                    "Configured cluster '%s' does not match project's cluster '%s'. "
                    "Using the project's cluster.",
                    self.config.cluster_name,
                    cluster.name,
                )
            return project, cluster

        try:
            if self.config.cluster_name:
                cluster = self.client.get_cluster_by_name(
                    self.config.cluster_name
                )
            else:
                cluster = self.client.get_first_cluster()
        except RunAIClientError as exc:
            raise DeployerError(
                f"Failed to find a Run:AI cluster: {exc}"
            ) from exc

        return project, cluster

    def _sanitize_workload_name(
        self,
        name: str,
        suffix: str,
        max_length: int = MAX_WORKLOAD_NAME_LENGTH,
    ) -> str:
        """Sanitize a name to comply with Run:AI/Kubernetes naming requirements.

        Args:
            name: The raw name to sanitize.
            suffix: A suffix to add to the name for uniqueness.
            max_length: The maximum length of the name.

        Returns:
            A sanitized name that complies with naming requirements.

        Raises:
            ValueError: If the name is invalid.
        """
        sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
        sanitized = re.sub(r"-+", "-", sanitized)
        sanitized = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", sanitized)

        max_base_length = max_length - len(suffix) - 1
        if len(sanitized) > max_base_length:
            sanitized = sanitized[:max_base_length]

        sanitized = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", sanitized)

        if not sanitized:
            raise ValueError(
                f"Invalid name: {name}. Must contain at least one alphanumeric character."
            )

        return f"{sanitized}-{suffix}"

    def _get_workload_name(
        self,
        deployment_name: str,
        deployment_id: UUID,
        prefix: str,
    ) -> str:
        """Get the Run:AI workload name for a deployment.

        Args:
            deployment_name: The deployment name.
            deployment_id: The deployment ID.
            prefix: The prefix to use for the workload name.

        Returns:
            The Run:AI workload name.
        """
        deployment_id_short = str(deployment_id)[:8]
        raw_name = f"{prefix}{deployment_name}"

        return self._sanitize_workload_name(raw_name, deployment_id_short)

    def _build_command_and_args(
        self, entrypoint_command: List[str]
    ) -> Tuple[str, Optional[str]]:
        """Build the command and arguments for Run:AI.

        Run:AI expects the command and args as strings (not lists). We keep
        the interpreter/module invocation intact for the command and join
        remaining tokens as the args string.

        Args:
            entrypoint_command: The full entrypoint command list.

        Returns:
            Tuple of (command, args) as strings. The args value is None when
            there are no extra tokens.

        Raises:
            ValueError: If entrypoint_command format is invalid.
        """
        if len(entrypoint_command) < 3:
            raise ValueError(
                "Expected entrypoint command with at least 3 elements "
                f"(e.g., ['python', '-m', 'module_name']), but got "
                f"{len(entrypoint_command)} elements: {entrypoint_command}"
            )

        command = " ".join(entrypoint_command[:3])
        args = " ".join(entrypoint_command[3:]) or None
        return command, args

    def get_labels(
        self, deployment: DeploymentResponse, settings: RunAIDeployerSettings
    ) -> Dict[str, str]:
        """Get the labels for a deployment.

        Args:
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            The labels for the deployment.
        """
        return {
            **settings.labels,
            "zenml-deployment-id": str(deployment.id),
            "zenml-deployment-name": deployment.name,
            "zenml-deployer-name": str(self.name),
            "zenml-deployer-id": str(self.id),
            "managed-by": "zenml",
        }

    def _build_autoscaling_config(
        self,
        settings: RunAIDeployerSettings,
    ) -> AutoScaling:
        """Build autoscaling configuration for the inference workload.

        Args:
            settings: The deployer settings.

        Returns:
            AutoScaling configuration object.
        """
        autoscaling_kwargs: Dict[str, object] = {
            "min_replicas": settings.min_replicas,
            "max_replicas": settings.max_replicas,
        }

        if settings.min_replicas < settings.max_replicas:
            autoscaling_kwargs["metric"] = settings.autoscaling_metric
            autoscaling_kwargs["metric_threshold"] = (
                settings.autoscaling_metric_threshold
            )

        return AutoScaling(**autoscaling_kwargs)

    def _build_inference_request(
        self,
        deployment: DeploymentResponse,
        settings: RunAIDeployerSettings,
        project: RunAIProject,
        cluster: RunAICluster,
        image: str,
        workload_name: str,
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> InferenceCreationRequest:
        """Build a Run:AI inference creation request.

        Args:
            deployment: The deployment.
            settings: The deployer settings.
            project: The Run:AI project.
            cluster: The Run:AI cluster.
            image: The Docker image to use.
            workload_name: The workload name.
            environment: Environment variables.
            secrets: Secret environment variables.

        Returns:
            The inference creation request.
        """
        entrypoint = DeploymentEntrypointConfiguration.get_entrypoint_command()
        arguments = DeploymentEntrypointConfiguration.get_entrypoint_arguments(
            **{
                DEPLOYMENT_ID_OPTION: deployment.id,
            }
        )
        command, args = self._build_command_and_args(
            entrypoint + arguments
        )

        merged_env = {
            **settings.environment_variables,
            **environment,
            **secrets,
        }
        env_vars = [
            EnvironmentVariable(name=key, value=value)
            for key, value in merged_env.items()
        ]

        assert deployment.snapshot, "Pipeline snapshot not found"
        container_port = (
            deployment.snapshot.pipeline_configuration.deployment_settings.uvicorn_port
        )

        compute_spec = SupersetSpecAllOfCompute(
            cpu_core_request=settings.cpu_core_request,
            cpu_memory_request=settings.cpu_memory_request,
            gpu_devices_request=settings.gpu_devices_request,
            gpu_request_type=settings.gpu_request_type,
            gpu_portion_request=settings.gpu_portion_request,
            gpu_memory_request=settings.gpu_memory_request,
        )

        labels = [
            Label(name=key, value=value)
            for key, value in self.get_labels(deployment, settings).items()
        ]
        annotations = (
            [
                Annotation(name=key, value=value)
                for key, value in settings.annotations.items()
            ]
            if settings.annotations
            else None
        )

        spec = InferenceSpecSpec(
            compute=compute_spec,
            image=image,
            command=command,
            args=args,
            environment_variables=env_vars,
            image_pull_policy=ImagePullPolicy.ALWAYS,
            serving_port=ServingPort(
                container=container_port,
                protocol=ServingPortProtocol.HTTP,
            ),
            autoscaling=self._build_autoscaling_config(settings),
            labels=labels,
            annotations=annotations,
            node_pools=settings.node_pools,
            node_type=settings.node_type,
        )

        if self.config.image_pull_secret_name:
            spec.image_pull_secrets = [
                ImagePullSecret(name=self.config.image_pull_secret_name)
            ]

        return InferenceCreationRequest(
            name=workload_name,
            project_id=project.id,
            cluster_id=cluster.id,
            spec=spec,
        )

    def _get_existing_workload(
        self, deployment: DeploymentResponse
    ) -> Optional[str]:
        """Get an existing Run:AI workload name for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The workload name, or None if not found.
        """
        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if not existing_metadata.workload_id:
            return None

        try:
            workload = self.client.get_inference_workload(
                existing_metadata.workload_id
            )
        except RunAIClientError:
            return None

        return workload.name

    def _get_workload_operational_state(
        self,
        workload_id: str,
        workload_name: str,
        project: RunAIProject,
        cluster: RunAICluster,
        settings: RunAIDeployerSettings,
    ) -> DeploymentOperationalState:
        """Get the operational state of a Run:AI inference workload.

        Args:
            workload_id: The workload ID.
            workload_name: The workload name.
            project: The Run:AI project.
            cluster: The Run:AI cluster.
            settings: The deployer settings.

        Returns:
            The operational state of the workload.
        """
        status_str = self.client.get_inference_workload_status(workload_id)
        status = map_runai_inference_status_to_deployment_status(
            status_str or ""
        )
        endpoint_url = self.client.get_inference_endpoint_url(workload_id)

        metadata = RunAIDeploymentMetadata(
            workload_id=workload_id,
            workload_name=workload_name,
            endpoint_url=endpoint_url,
            project_id=project.id,
            project_name=project.name,
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            min_replicas=settings.min_replicas,
            max_replicas=settings.max_replicas,
            cpu=settings.cpu_core_request,
            memory=settings.cpu_memory_request,
            gpu_devices=settings.gpu_devices_request,
            gpu_portion=settings.gpu_portion_request,
        )

        state = DeploymentOperationalState(
            status=status,
            metadata=metadata.model_dump(exclude_none=True),
        )

        if status == DeploymentStatus.RUNNING and endpoint_url:
            state.url = endpoint_url

        return state

    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Deploy a pipeline as a Run:AI inference workload.

        Args:
            deployment: The deployment to serve.
            stack: The stack the pipeline will be deployed on.
            environment: Environment variables to set.
            secrets: Secret environment variables to set.
            timeout: The maximum time in seconds to wait for provisioning.

        Returns:
            The operational state of the provisioned deployment.

        Raises:
            DeploymentProvisionError: If the deployment fails.
            DeployerError: If an unexpected error occurs.
        """
        snapshot = deployment.snapshot
        assert snapshot, "Pipeline snapshot not found"

        settings = cast(RunAIDeployerSettings, self.get_settings(snapshot))

        project, cluster = self._resolve_project_and_cluster()
        image = self.get_image(snapshot)
        workload_name = self._get_workload_name(
            deployment.name, deployment.id, settings.workload_name_prefix
        )

        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)
        if existing_metadata.workload_id:
            existing_name = self._get_existing_workload(deployment)
            if existing_name:
                logger.debug(
                    "Deleting existing workload %s (name: %s) before redeploy.",
                    existing_metadata.workload_id,
                    existing_name,
                )
                try:
                    self.client.delete_inference_workload(
                        existing_metadata.workload_id
                    )
                except RunAIClientError as exc:
                    logger.warning(
                        "Failed to delete existing workload %s: %s",
                        existing_metadata.workload_id,
                        exc,
                    )

        request = self._build_inference_request(
            deployment=deployment,
            settings=settings,
            project=project,
            cluster=cluster,
            image=image,
            workload_name=workload_name,
            environment=environment,
            secrets=secrets,
        )

        try:
            result = self.client.create_inference_workload(request)

            logger.info(
                "Created Run:AI inference workload '%s' with ID: %s",
                workload_name,
                result.workload_id,
            )

            return self._get_workload_operational_state(
                workload_id=result.workload_id,
                workload_name=workload_name,
                project=project,
                cluster=cluster,
                settings=settings,
            )
        except RunAIClientError as exc:
            raise DeploymentProvisionError(
                f"Failed to create Run:AI inference workload for deployment "
                f"'{deployment.name}': {exc}"
            ) from exc
        except Exception as exc:
            raise DeployerError(
                f"Unexpected error while provisioning deployment "
                f"'{deployment.name}': {exc}"
            ) from exc

    def do_get_deployment_state(
        self,
        deployment: DeploymentResponse,
    ) -> DeploymentOperationalState:
        """Get information about a Run:AI inference deployment.

        Args:
            deployment: The deployment to get information about.

        Returns:
            The operational state of the deployment.

        Raises:
            DeploymentNotFoundError: If the deployment is not found.
        """
        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if not existing_metadata.workload_id:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found "
                "(no workload ID in metadata)"
            )

        try:
            workload = self.client.get_inference_workload(
                existing_metadata.workload_id
            )
        except RunAIWorkloadNotFoundError as exc:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found: {exc}"
            ) from exc
        except RunAIClientError as exc:
            raise DeployerError(
                f"Failed to query Run:AI workload for deployment "
                f"'{deployment.name}': {exc}"
            ) from exc

        status_str = workload.actual_phase or workload.status or ""
        status = map_runai_inference_status_to_deployment_status(status_str)

        endpoint_url = workload.endpoint_url
        if not endpoint_url:
            extra = getattr(workload, "model_extra", None) or {}
            endpoint_url = (
                extra.get("endpointUrl")
                or extra.get("endpoint_url")
                or extra.get("url")
            )

        metadata = RunAIDeploymentMetadata(
            workload_id=existing_metadata.workload_id,
            workload_name=existing_metadata.workload_name or workload.name,
            endpoint_url=endpoint_url,
            project_id=existing_metadata.project_id,
            project_name=existing_metadata.project_name,
            cluster_id=existing_metadata.cluster_id,
            cluster_name=existing_metadata.cluster_name,
            min_replicas=existing_metadata.min_replicas,
            max_replicas=existing_metadata.max_replicas,
            cpu=existing_metadata.cpu,
            memory=existing_metadata.memory,
            gpu_devices=existing_metadata.gpu_devices,
            gpu_portion=existing_metadata.gpu_portion,
        )

        state = DeploymentOperationalState(
            status=status,
            metadata=metadata.model_dump(exclude_none=True),
        )

        if status == DeploymentStatus.RUNNING and endpoint_url:
            state.url = endpoint_url

        return state

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Run:AI inference deployment.

        Run:AI does not provide a direct API for fetching workload logs.
        Users should access logs through the Run:AI UI.

        Args:
            deployment: The deployment to get the logs of.
            follow: If True, stream logs as they are written.
            tail: Only retrieve the last NUM lines of log output.

        Yields:
            Instructions for accessing logs in Run:AI UI.
        """
        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if existing_metadata.workload_id:
            yield (
                "Run:AI does not provide a direct API for fetching workload logs.\n"
                f"Please access logs for workload '{existing_metadata.workload_name}' "
                f"(ID: {existing_metadata.workload_id}) through the Run:AI UI:\n"
                f"  {self.config.runai_base_url}/workloads/{existing_metadata.workload_id}"
            )
        else:
            yield (
                "No workload ID found in deployment metadata. "
                "The deployment may not have been provisioned yet."
            )

    def do_deprovision_deployment(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision a Run:AI inference deployment.

        Args:
            deployment: The deployment to deprovision.
            timeout: The maximum time in seconds to wait for deprovisioning.

        Returns:
            The operational state of the deprovisioned deployment, or None if
            deletion is completed immediately.

        Raises:
            DeploymentNotFoundError: If the deployment is not found.
            DeploymentDeprovisionError: If the deprovision fails.
            DeployerError: If an unexpected error occurs.
        """
        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if not existing_metadata.workload_id:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found "
                "(no workload ID in metadata)"
            )

        try:
            self.client.delete_inference_workload(existing_metadata.workload_id)
            logger.info(
                "Deleted Run:AI inference workload '%s' (ID: %s)",
                existing_metadata.workload_name,
                existing_metadata.workload_id,
            )
            return None
        except RunAIWorkloadNotFoundError as exc:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found"
            ) from exc
        except RunAIClientError as exc:
            raise DeploymentDeprovisionError(
                f"Failed to delete Run:AI workload for deployment "
                f"'{deployment.name}': {exc}"
            ) from exc
        except Exception as exc:
            raise DeployerError(
                f"Unexpected error while deleting deployment "
                f"'{deployment.name}': {exc}"
            ) from exc
