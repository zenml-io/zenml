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
"""Kubeflow Training step operator implementation."""

import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type, cast

from kubernetes import client as k8s_client

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.kubeflow.flavors.kubeflow_training_step_operator_flavor import (
    KubeflowTrainingStepOperatorConfig,
    KubeflowTrainingStepOperatorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

KUBEFLOW_TRAINING_STEP_OPERATOR_DOCKER_IMAGE_KEY = (
    "kubeflow_training_step_operator"
)

# Supported training job types for Kubeflow Training API v1alpha1
SUPPORTED_JOB_TYPES = {
    "PyTorch": {
        "api_version": "trainer.kubeflow.org/v1alpha1",
        "kind": "TrainJob",
        "framework": "pytorch",
    },
    "TensorFlow": {
        "api_version": "trainer.kubeflow.org/v1alpha1",
        "kind": "TrainJob",
        "framework": "tensorflow",
    },
    "JAX": {
        "api_version": "trainer.kubeflow.org/v1alpha1",
        "kind": "TrainJob",
        "framework": "jax",
    },
    "MPI": {
        "api_version": "trainer.kubeflow.org/v1alpha1",
        "kind": "TrainJob",
        "framework": "mpi",
    },
}


class KubeflowTrainingStepOperator(BaseStepOperator):
    """Step operator to run training jobs on Kubeflow Training Operator."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    @property
    def config(self) -> KubeflowTrainingStepOperatorConfig:
        """Returns the `KubeflowTrainingStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubeflowTrainingStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubeflow Training step operator.

        Returns:
            The settings class.
        """
        return KubeflowTrainingStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Kubeflow Training step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Kubeflow "
                    "Training step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Kubeflow Training step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Kubeflow Training step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        builds = []
        for step_name, step in deployment.step_configurations.items():
            if step.config.step_operator == self.name:
                build = BuildConfiguration(
                    key=KUBEFLOW_TRAINING_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def get_kube_client(self) -> k8s_client.ApiClient:
        """Get the Kubernetes API client.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: If the service connector returns an unexpected client.
        """
        if self.config.incluster:
            kube_utils.load_kube_config(incluster=True)
            self._k8s_client = k8s_client.ApiClient()
            return self._k8s_client

        # Refresh the client also if the connector has expired
        if self._k8s_client and not self.connector_has_expired():
            return self._k8s_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, k8s_client.ApiClient):
                raise RuntimeError(
                    f"Expected a k8s_client.ApiClient while trying to use the "
                    f"linked connector, but got {type(client)}."
                )
            self._k8s_client = client
        else:
            kube_utils.load_kube_config(
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def _k8s_custom_objects_api(self) -> k8s_client.CustomObjectsApi:
        """Getter for the Kubernetes Custom Objects API client.

        Returns:
            The Kubernetes Custom Objects API client.
        """
        return k8s_client.CustomObjectsApi(self.get_kube_client())

    def _build_training_job_manifest(
        self,
        job_name: str,
        image: str,
        command: List[str],
        environment: Dict[str, str],
        settings: KubeflowTrainingStepOperatorSettings,
    ) -> Dict[str, any]:
        """Build the Kubeflow Training Job manifest for API v1alpha1.

        Args:
            job_name: Name of the training job.
            image: Docker image to use for training.
            command: Command to execute for training.
            environment: Environment variables to set.
            settings: Step operator settings.

        Returns:
            The training job manifest as a dictionary.

        Raises:
            ValueError: If the training job type is not supported.
        """
        # Map old job type names to new ones for backwards compatibility
        job_type_mapping = {
            "PyTorchJob": "PyTorch",
            "TFJob": "TensorFlow",
            "MPIJob": "MPI",
            "XGBoostJob": "XGBoost",  # if we add XGBoost support later
        }

        training_job_type = job_type_mapping.get(
            settings.training_job_type, settings.training_job_type
        )

        if training_job_type not in SUPPORTED_JOB_TYPES:
            raise ValueError(
                f"Unsupported training job type: {settings.training_job_type}. "
                f"Supported types: {list(SUPPORTED_JOB_TYPES.keys())}"
            )

        # Build the TrainJob spec for Kubeflow Training API v1alpha1
        job_spec = SUPPORTED_JOB_TYPES[training_job_type]

        # Map framework to runtime name
        runtime_mapping = {
            "pytorch": "torch-distributed",
            "tensorflow": "torch-distributed",  # fallback to torch
            "jax": "torch-distributed",  # fallback to torch
            "mpi": "mpi-distributed",
        }

        runtime_name = runtime_mapping.get(
            job_spec["framework"], "torch-distributed"
        )

        train_spec = {
            "runtimeRef": {
                "name": runtime_name,
            },
            "trainer": {
                "image": image,
                "command": command,
                "env": [
                    {"name": k, "value": v} for k, v in environment.items()
                ],
            },
        }

        # Add resource requirements if specified
        if (
            settings.worker_pod_settings
            and settings.worker_pod_settings.resources
        ):
            train_spec["trainer"]["resources"] = (
                settings.worker_pod_settings.resources
            )

        # Build the complete manifest for TrainJob
        manifest = {
            "apiVersion": job_spec["api_version"],
            "kind": job_spec["kind"],
            "metadata": {
                "name": job_name,
                "namespace": self.config.kubeflow_namespace,
            },
            "spec": train_spec,
        }

        # Add optional fields
        if settings.ttl_seconds_after_finished is not None:
            manifest["spec"]["ttlSecondsAfterFinished"] = (
                settings.ttl_seconds_after_finished
            )

        return manifest

    def _wait_for_training_job_completion(
        self,
        job_name: str,
        timeout: int,
    ) -> bool:
        """Wait for a training job to complete.

        Args:
            job_name: Name of the training job.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if job completed successfully, False if failed.

        Raises:
            TimeoutError: If job doesn't complete within timeout.
        """
        api = self._k8s_custom_objects_api
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = api.get_namespaced_custom_object(
                    group="trainer.kubeflow.org",
                    version="v1alpha1",
                    namespace=self.config.kubeflow_namespace,
                    plural="trainjobs",
                    name=job_name,
                )

                status = response.get("status", {})
                conditions = status.get("conditions", [])

                for condition in conditions:
                    if (
                        condition.get("type") == "Succeeded"
                        and condition.get("status") == "True"
                    ):
                        logger.info(
                            f"Training job {job_name} completed successfully"
                        )
                        return True
                    elif (
                        condition.get("type") == "Failed"
                        and condition.get("status") == "True"
                    ):
                        logger.error(
                            f"Training job {job_name} failed: {condition.get('reason', 'Unknown')}"
                        )
                        return False

                logger.info(f"Training job {job_name} is still running...")
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.warning(f"Error checking job status: {e}")
                time.sleep(30)

        raise TimeoutError(
            f"Training job {job_name} did not complete within {timeout} seconds"
        )

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a training job on Kubeflow Training Operator.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        settings = cast(
            KubeflowTrainingStepOperatorSettings, self.get_settings(info)
        )
        image_name = info.get_image(
            key=KUBEFLOW_TRAINING_STEP_OPERATOR_DOCKER_IMAGE_KEY
        )

        # Create a shorter job name to avoid 63-character limit
        # Format: {pipeline_name}-{step_name}-{short_run_id}
        run_id_short = info.run_name.split('-')[-1][:8]  # Last 8 chars of run ID
        job_name = f"{info.pipeline.name}-{info.pipeline_step_name}-{run_id_short}"
        job_name = kube_utils.sanitize_pod_name(
            job_name, namespace=self.config.kubeflow_namespace
        )

        logger.info(
            f"Launching Kubeflow {settings.training_job_type} training job: {job_name}"
        )

        # Build training job manifest
        manifest = self._build_training_job_manifest(
            job_name=job_name,
            image=image_name,
            command=entrypoint_command,
            environment=environment,
            settings=settings,
        )

        # Submit the training job
        api = self._k8s_custom_objects_api

        try:
            api.create_namespaced_custom_object(
                group="trainer.kubeflow.org",
                version="v1alpha1",
                namespace=self.config.kubeflow_namespace,
                plural="trainjobs",
                body=manifest,
            )
            logger.info(f"Successfully created training job {job_name}")

        except Exception as e:
            logger.error(f"Failed to create training job {job_name}: {e}")
            raise

        # Wait for job completion
        try:
            success = self._wait_for_training_job_completion(
                job_name=job_name,
                timeout=settings.job_completion_timeout,
            )

            if not success:
                raise RuntimeError(f"Training job {job_name} failed")

        except TimeoutError:
            logger.warning(
                f"Training job {job_name} did not complete within timeout"
            )
            raise
        except Exception as e:
            logger.error(f"Error waiting for training job completion: {e}")
            raise
        finally:
            # Cleanup job if configured to do so
            if settings.ttl_seconds_after_finished is None:
                try:
                    api.delete_namespaced_custom_object(
                        group="trainer.kubeflow.org",
                        version="v1alpha1",
                        namespace=self.config.kubeflow_namespace,
                        plural="trainjobs",
                        name=job_name,
                    )
                    logger.info(f"Cleaned up training job {job_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup training job {job_name}: {e}"
                    )
