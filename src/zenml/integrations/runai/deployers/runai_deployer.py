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
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

from pydantic import BaseModel

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
from zenml.models import (
    DeploymentOperationalState,
    DeploymentResponse,
)
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
    created_time: Optional[str] = None
    updated_time: Optional[str] = None

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
    """Deployer responsible for deploying pipelines on Run:AI as inference workloads."""

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

    def _get_runai_client(self) -> RunAIClient:
        """Get or create the Run:AI client.

        Returns:
            The Run:AI client.
        """
        if self._client is None:
            self._client = RunAIClient(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret.get_secret_value(),
                runai_base_url=self.config.runai_base_url,
            )
        return self._client

    def _get_project_and_cluster(self) -> Tuple[RunAIProject, RunAICluster]:
        """Get the Run:AI project and cluster for workload submission.

        Returns:
            Tuple of (project, cluster).

        Raises:
            DeployerError: If project or cluster lookup fails.
        """
        client = self._get_runai_client()

        try:
            project = client.get_project_by_name(self.config.project_name)
        except RunAIClientError as e:
            raise DeployerError(
                f"Failed to find Run:AI project '{self.config.project_name}': {e}"
            ) from e

        if self.config.cluster_name:
            try:
                cluster = client.get_cluster_by_name(self.config.cluster_name)
            except RunAIClientError as e:
                raise DeployerError(
                    f"Failed to find Run:AI cluster '{self.config.cluster_name}': {e}"
                ) from e
        elif project.cluster_id:
            cluster_result = client.get_cluster_by_id(project.cluster_id)
            if not cluster_result:
                raise DeployerError(
                    f"Project cluster ID '{project.cluster_id}' not found"
                )
            cluster = cluster_result
        else:
            try:
                cluster = client.get_first_cluster()
            except RunAIClientError as e:
                raise DeployerError(
                    f"Failed to find a Run:AI cluster: {e}"
                ) from e

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
        models: Any,
        settings: RunAIDeployerSettings,
    ) -> Any:
        """Build autoscaling configuration for the inference workload.

        Args:
            models: The Run:AI models module.
            settings: The deployer settings.

        Returns:
            AutoScaling configuration object.
        """
        autoscaling_kwargs: Dict[str, Any] = {
            "min_replicas": settings.min_replicas,
            "max_replicas": settings.max_replicas,
        }

        if settings.min_replicas < settings.max_replicas:
            autoscaling_kwargs["metric"] = settings.autoscaling_metric
            autoscaling_kwargs["metric_threshold"] = (
                settings.autoscaling_metric_threshold
            )

        return models.AutoScaling(**autoscaling_kwargs)

    def _build_inference_request(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        settings: RunAIDeployerSettings,
        project: RunAIProject,
        cluster: RunAICluster,
        image: str,
        workload_name: str,
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> Any:
        """Build a Run:AI inference creation request.

        Args:
            deployment: The deployment.
            stack: The stack.
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
        client = self._get_runai_client()
        models = client.models

        entrypoint = DeploymentEntrypointConfiguration.get_entrypoint_command()
        arguments = DeploymentEntrypointConfiguration.get_entrypoint_arguments(
            **{
                DEPLOYMENT_ID_OPTION: deployment.id,
            }
        )

        merged_env = {
            **settings.environment_variables,
            **environment,
            **secrets,
        }
        env_vars = [
            models.EnvironmentVariable(name=key, value=value)
            for key, value in merged_env.items()
        ]

        assert deployment.snapshot, "Pipeline snapshot not found"
        container_port = deployment.snapshot.pipeline_configuration.deployment_settings.uvicorn_port

        compute_spec = models.SupersetSpecAllOfCompute(
            cpu_core_request=settings.cpu_core_request,
            cpu_memory_request=settings.cpu_memory_request,
            gpu_devices_request=settings.gpu_devices_request,
            gpu_request_type=settings.gpu_request_type,
            gpu_portion_request=settings.gpu_portion_request,
            gpu_memory_request=settings.gpu_memory_request,
        )

        image_pull_policy = models.ImagePullPolicy.ALWAYS

        labels = [
            models.Label(name=key, value=value)
            for key, value in self.get_labels(deployment, settings).items()
        ]
        annotations = (
            [
                models.Annotation(name=key, value=value)
                for key, value in settings.annotations.items()
            ]
            if settings.annotations
            else None
        )

        spec = models.InferenceSpecSpec(
            compute=compute_spec,
            image=image,
            command=" ".join(entrypoint),
            args=" ".join(arguments),
            environment_variables=env_vars,
            image_pull_policy=image_pull_policy,
            serving_port=models.ServingPort(
                container=container_port,
                protocol=models.ServingPortProtocol.HTTP,
            ),
            autoscaling=self._build_autoscaling_config(models, settings),
            labels=labels,
            annotations=annotations,
            node_pools=settings.node_pools,
            node_type=settings.node_type,
        )

        if self.config.image_pull_secret_name:
            spec.image_pull_secrets = [
                models.ImagePullSecret(
                    name=self.config.image_pull_secret_name,
                )
            ]

        return models.InferenceCreationRequest(
            name=workload_name,
            project_id=project.id,
            cluster_id=cluster.id,
            spec=spec,
        )

    def _get_existing_workload(
        self, deployment: DeploymentResponse
    ) -> Optional[Dict[str, Any]]:
        """Get an existing Run:AI workload for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The workload data dictionary, or None if not found.
        """
        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if not existing_metadata.workload_id:
            return None

        try:
            client = self._get_runai_client()
            return client.get_inference_workload(existing_metadata.workload_id)
        except RunAIClientError:
            return None

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
        client = self._get_runai_client()

        status_str = client.get_inference_workload_status(workload_id)
        status = map_runai_inference_status_to_deployment_status(
            status_str or ""
        )
        endpoint_url = client.get_inference_endpoint_url(workload_id)

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

        settings = cast(
            RunAIDeployerSettings,
            self.get_settings(snapshot),
        )

        project, cluster = self._get_project_and_cluster()
        image = self.get_image(snapshot)
        workload_name = self._get_workload_name(
            deployment.name, deployment.id, settings.workload_name_prefix
        )

        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if existing_metadata.workload_id:
            existing_workload = self._get_existing_workload(deployment)

            if existing_workload:
                current_name = existing_workload.get("name")
                if current_name != workload_name:
                    logger.debug(
                        f"Deleting existing workload {existing_metadata.workload_id} "
                        f"(name changed from {current_name} to {workload_name})"
                    )
                    try:
                        client = self._get_runai_client()
                        client.delete_inference_workload(
                            existing_metadata.workload_id
                        )
                    except RunAIClientError as e:
                        logger.warning(
                            f"Failed to delete existing workload: {e}"
                        )
                else:
                    logger.debug(
                        f"Updating existing inference workload: {workload_name}"
                    )
                    try:
                        client = self._get_runai_client()
                        client.delete_inference_workload(
                            existing_metadata.workload_id
                        )
                    except RunAIClientError as e:
                        logger.warning(
                            f"Failed to delete workload for update: {e}"
                        )

        request = self._build_inference_request(
            deployment=deployment,
            stack=stack,
            settings=settings,
            project=project,
            cluster=cluster,
            image=image,
            workload_name=workload_name,
            environment=environment,
            secrets=secrets,
        )

        try:
            client = self._get_runai_client()
            result = client.create_inference_workload(request)

            logger.info(
                f"Created Run:AI inference workload '{workload_name}' "
                f"with ID: {result.workload_id}"
            )

            return self._get_workload_operational_state(
                workload_id=result.workload_id,
                workload_name=workload_name,
                project=project,
                cluster=cluster,
                settings=settings,
            )

        except RunAIClientError as e:
            raise DeploymentProvisionError(
                f"Failed to create Run:AI inference workload for deployment "
                f"'{deployment.name}': {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while provisioning deployment "
                f"'{deployment.name}': {e}"
            ) from e

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
            RuntimeError: If required metadata is missing.
        """
        existing_metadata = RunAIDeploymentMetadata.from_deployment(deployment)

        if not existing_metadata.workload_id:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found "
                "(no workload ID in metadata)"
            )

        client = self._get_runai_client()

        try:
            workload = client.get_inference_workload(
                existing_metadata.workload_id
            )
        except RunAIClientError as e:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found: {e}"
            ) from e

        if not workload:
            raise DeploymentNotFoundError(
                f"Run:AI workload for deployment '{deployment.name}' not found"
            )

        status_str = workload.get("actualPhase") or workload.get("status")
        status = map_runai_inference_status_to_deployment_status(
            status_str or ""
        )

        endpoint_url = (
            workload.get("endpointUrl")
            or workload.get("endpoint_url")
            or workload.get("url")
        )

        metadata = RunAIDeploymentMetadata(
            workload_id=existing_metadata.workload_id,
            workload_name=existing_metadata.workload_name
            or workload.get("name"),
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
                f"Run:AI does not provide a direct API for fetching workload logs.\n"
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
            client = self._get_runai_client()
            client.delete_inference_workload(existing_metadata.workload_id)

            logger.info(
                f"Deleted Run:AI inference workload "
                f"'{existing_metadata.workload_name}' "
                f"(ID: {existing_metadata.workload_id})"
            )

            return None

        except RunAIClientError as e:
            if "not found" in str(e).lower():
                raise DeploymentNotFoundError(
                    f"Run:AI workload for deployment '{deployment.name}' not found"
                ) from e
            raise DeploymentDeprovisionError(
                f"Failed to delete Run:AI workload for deployment "
                f"'{deployment.name}': {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while deleting deployment "
                f"'{deployment.name}': {e}"
            ) from e
