# Copyright 2022 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
#
# Parts of the `prepare_or_run_pipeline()` method of this file are
# inspired by the Kubernetes dag runner implementation of tfx
"""Kubernetes-native orchestrator."""

import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from zenml.config.base_settings import BaseSettings
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorConfig,
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator_entrypoint_configuration import (
    KubernetesOrchestratorEntrypointConfiguration,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_cron_job_manifest,
    build_pod_manifest,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_KUBERNETES_RUN_ID = "ZENML_KUBERNETES_RUN_ID"
KUBERNETES_SECRET_TOKEN_KEY_NAME = "zenml_api_token"


class KubernetesOrchestrator(ContainerizedOrchestrator):
    """Orchestrator for running ZenML pipelines using native Kubernetes."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def get_kube_client(
        self, incluster: Optional[bool] = None
    ) -> k8s_client.ApiClient:
        """Getter for the Kubernetes API client.

        Args:
            incluster: Whether to use the in-cluster config or not. Overrides
                the `incluster` setting in the config.

        Returns:
            The Kubernetes API client.

        Raises:
            RuntimeError: if the Kubernetes connector behaves unexpectedly.
        """
        if incluster is None:
            incluster = self.config.incluster

        if incluster:
            kube_utils.load_kube_config(
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
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
                incluster=incluster,
                context=self.config.kubernetes_context,
            )
            self._k8s_client = k8s_client.ApiClient()

        return self._k8s_client

    @property
    def _k8s_core_api(self) -> k8s_client.CoreV1Api:
        """Getter for the Kubernetes Core API client.

        Returns:
            The Kubernetes Core API client.
        """
        return k8s_client.CoreV1Api(self.get_kube_client())

    @property
    def _k8s_batch_api(self) -> k8s_client.BatchV1Api:
        """Getter for the Kubernetes Batch API client.

        Returns:
            The Kubernetes Batch API client.
        """
        return k8s_client.BatchV1Api(self.get_kube_client())

    @property
    def _k8s_rbac_api(self) -> k8s_client.RbacAuthorizationV1Api:
        """Getter for the Kubernetes RBAC API client.

        Returns:
            The Kubernetes RBAC API client.
        """
        return k8s_client.RbacAuthorizationV1Api(self.get_kube_client())

    @property
    def config(self) -> KubernetesOrchestratorConfig:
        """Returns the `KubernetesOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubernetes orchestrator.

        Returns:
            The settings class.
        """
        return KubernetesOrchestratorSettings

    @property
    def supports_cancellation(self) -> bool:
        """Whether this orchestrator supports stopping pipeline runs.

        Returns:
            True since the Kubernetes orchestrator supports cancellation.
        """
        return True

    def get_kubernetes_contexts(self) -> Tuple[List[str], str]:
        """Get list of configured Kubernetes contexts and the active context.

        Raises:
            RuntimeError: if the Kubernetes configuration cannot be loaded.

        Returns:
            context_name: List of configured Kubernetes contexts
            active_context_name: Name of the active Kubernetes context.
        """
        try:
            contexts, active_context = k8s_config.list_kube_config_contexts()
        except k8s_config.config_exception.ConfigException as e:
            raise RuntimeError(
                "Could not load the Kubernetes configuration"
            ) from e

        context_names = [c["name"] for c in contexts]
        active_context_name = active_context["name"]
        return context_names, active_context_name

    @property
    def validator(self) -> Optional[StackValidator]:
        """Defines the validator that checks whether the stack is valid.

        Returns:
            Stack validator.
        """

        def _validate_local_requirements(stack: "Stack") -> Tuple[bool, str]:
            """Validates that the stack contains no local components.

            Args:
                stack: The stack.

            Returns:
                Whether the stack is valid or not.
                An explanation why the stack is invalid, if applicable.
            """
            container_registry = stack.container_registry

            # should not happen, because the stack validation takes care of
            # this, but just in case
            assert container_registry is not None

            kubernetes_context = self.config.kubernetes_context
            msg = f"'{self.name}' Kubernetes orchestrator error: "

            if not self.connector:
                if kubernetes_context:
                    contexts, active_context = self.get_kubernetes_contexts()

                    if kubernetes_context not in contexts:
                        return False, (
                            f"{msg}could not find a Kubernetes context named "
                            f"'{kubernetes_context}' in the local "
                            "Kubernetes configuration. Please make sure that "
                            "the Kubernetes cluster is running and that the "
                            "kubeconfig file is configured correctly. To list "
                            "all configured contexts, run:\n\n"
                            "  `kubectl config get-contexts`\n"
                        )
                    if kubernetes_context != active_context:
                        logger.warning(
                            f"{msg}the Kubernetes context "  # nosec
                            f"'{kubernetes_context}' configured for the "
                            f"Kubernetes orchestrator is not the same as the "
                            f"active context in the local Kubernetes "
                            f"configuration. If this is not deliberate, you "
                            f"should update the orchestrator's "
                            f"`kubernetes_context` field by running:\n\n"
                            f"  `zenml orchestrator update {self.name} "
                            f"--kubernetes_context={active_context}`\n"
                            f"To list all configured contexts, run:\n\n"
                            f"  `kubectl config get-contexts`\n"
                            f"To set the active context to be the same as the "
                            f"one configured in the Kubernetes orchestrator "
                            f"and silence this warning, run:\n\n"
                            f"  `kubectl config use-context "
                            f"{kubernetes_context}`\n"
                        )
                elif self.config.incluster:
                    # No service connector or kubernetes_context is needed when
                    # the orchestrator is being used from within a Kubernetes
                    # cluster.
                    pass
                else:
                    return False, (
                        f"{msg}you must either link this orchestrator to a "
                        "Kubernetes service connector (see the 'zenml "
                        "orchestrator connect' CLI command), explicitly set "
                        "the `kubernetes_context` attribute to the name of the "
                        "Kubernetes config context pointing to the cluster "
                        "where you would like to run pipelines, or set the "
                        "`incluster` attribute to `True`."
                    )

            silence_local_validations_msg = (
                f"To silence this warning, set the "
                f"`skip_local_validations` attribute to True in the "
                f"orchestrator configuration by running:\n\n"
                f"  'zenml orchestrator update {self.name} "
                f"--skip_local_validations=True'\n"
            )

            if (
                not self.config.skip_local_validations
                and not self.config.is_local
            ):
                # if the orchestrator is not running in a local k3d cluster,
                # we cannot have any other local components in our stack,
                # because we cannot mount the local path into the container.
                # This may result in problems when running the pipeline, because
                # the local components will not be available inside the
                # kubernetes containers.

                # go through all stack components and identify those that
                # advertise a local path where they persist information that
                # they need to be available when running pipelines.
                for stack_comp in stack.components.values():
                    if stack_comp.local_path is None:
                        continue
                    return False, (
                        f"{msg}the Kubernetes orchestrator is configured to "
                        f"run pipelines in a remote Kubernetes cluster but the "
                        f"'{stack_comp.name}' {stack_comp.type.value} "
                        f"is a local stack component "
                        f"and will not be available in the Kubernetes pipeline "
                        f"step.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Kubernetes orchestrator, "
                        f"otherwise you may run into pipeline execution "
                        f"problems. You should use a flavor of "
                        f"{stack_comp.type.value} other than "
                        f"'{stack_comp.flavor}'.\n"
                        + silence_local_validations_msg
                    )

                # if the orchestrator is remote, the container registry must
                # also be remote.
                if container_registry.config.is_local:
                    return False, (
                        f"{msg}the Kubernetes orchestrator is configured to "
                        "run pipelines in a remote Kubernetes cluster but the "
                        f"'{container_registry.name}' container registry URI "
                        f"'{container_registry.config.uri}' "
                        f"points to a local container registry. Please ensure "
                        f"that you always use non-local stack components with "
                        f"a remote Kubernetes orchestrator, otherwise you will "
                        f"run into problems. You should use a flavor of "
                        f"container registry other than "
                        f"'{container_registry.flavor}'.\n"
                        + silence_local_validations_msg
                    )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_local_requirements,
        )

    @classmethod
    def apply_default_resource_requests(
        cls,
        memory: str,
        cpu: Optional[str] = None,
        pod_settings: Optional[KubernetesPodSettings] = None,
    ) -> KubernetesPodSettings:
        """Applies default resource requests to a pod settings object.

        Args:
            memory: The memory resource request.
            cpu: The CPU resource request.
            pod_settings: The pod settings to update. A new one will be created
                if not provided.

        Returns:
            The new or updated pod settings.
        """
        resources = {
            "requests": {"memory": memory},
        }
        if cpu:
            resources["requests"]["cpu"] = cpu
        if not pod_settings:
            pod_settings = KubernetesPodSettings(resources=resources)
        elif not pod_settings.resources:
            # We can't update the pod settings in place (because it's a frozen
            # pydantic model), so we have to create a new one.
            pod_settings = KubernetesPodSettings(
                **pod_settings.model_dump(exclude_unset=True),
                resources=resources,
            )
        else:
            set_requests = pod_settings.resources.get("requests", {})
            resources["requests"].update(set_requests)
            pod_settings.resources["requests"] = resources["requests"]

        return pod_settings

    def get_token_secret_name(self, deployment_id: UUID) -> str:
        """Returns the name of the secret that contains the ZenML token.

        Args:
            deployment_id: The ID of the deployment.

        Returns:
            The name of the secret that contains the ZenML token.
        """
        return f"zenml-token-{deployment_id}"

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Any:
        """Runs the pipeline in Kubernetes.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment.

        Raises:
            RuntimeError: If the Kubernetes orchestrator is not configured.
        """
        for step_name, step in deployment.step_configurations.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not yet supported for "
                    "the Kubernetes orchestrator, ignoring resource "
                    "configuration for step %s.",
                    step_name,
                )

        pipeline_name = deployment.pipeline_configuration.name
        settings = cast(
            KubernetesOrchestratorSettings, self.get_settings(deployment)
        )

        # We already make sure the orchestrator run name has the correct length
        # to make sure we don't cut off the randomized suffix later when
        # sanitizing the pod name. This avoids any pod naming collisions.
        max_length = kube_utils.calculate_max_pod_name_length_for_namespace(
            namespace=self.config.kubernetes_namespace
        )
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name, max_length=max_length
        )

        if settings.pod_name_prefix:
            pod_name = get_orchestrator_run_name(
                settings.pod_name_prefix, max_length=max_length
            )
        else:
            pod_name = orchestrator_run_name

        pod_name = kube_utils.sanitize_pod_name(
            pod_name, namespace=self.config.kubernetes_namespace
        )

        assert stack.container_registry

        # Get Docker image for the orchestrator pod
        try:
            image = self.get_image(deployment=deployment)
        except KeyError:
            # If no generic pipeline image exists (which means all steps have
            # custom builds) we use a random step image as all of them include
            # dependencies for the active stack
            pipeline_step_name = next(iter(deployment.step_configurations))
            image = self.get_image(
                deployment=deployment, step_name=pipeline_step_name
            )

        # Build entrypoint command and args for the orchestrator pod.
        # This will internally also build the command/args for all step pods.
        command = KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_command()
        args = KubernetesOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
            run_name=orchestrator_run_name,
            deployment_id=deployment.id,
            kubernetes_namespace=self.config.kubernetes_namespace,
            run_id=placeholder_run.id if placeholder_run else None,
        )

        # Authorize pod to run Kubernetes commands inside the cluster.
        service_account_name = self._get_service_account_name(settings)

        # We set some default minimum resource requests for the orchestrator pod
        # here if the user has not specified any, because the orchestrator pod
        # takes up some memory resources itself and, if not specified, the pod
        # will be scheduled on any node regardless of available memory and risk
        # negatively impacting or even crashing the node due to memory pressure.
        orchestrator_pod_settings = self.apply_default_resource_requests(
            memory="400Mi",
            cpu="100m",
            pod_settings=settings.orchestrator_pod_settings,
        )

        if self.config.pass_zenml_token_as_secret:
            secret_name = self.get_token_secret_name(deployment.id)
            token = environment.pop("ZENML_STORE_API_TOKEN")
            kube_utils.create_or_update_secret(
                core_api=self._k8s_core_api,
                namespace=self.config.kubernetes_namespace,
                secret_name=secret_name,
                data={KUBERNETES_SECRET_TOKEN_KEY_NAME: token},
            )
            orchestrator_pod_settings.env.append(
                {
                    "name": "ZENML_STORE_API_TOKEN",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": secret_name,
                            "key": KUBERNETES_SECRET_TOKEN_KEY_NAME,
                        }
                    },
                }
            )

        # Schedule as CRON job if CRON schedule is given.
        if deployment.schedule:
            if not deployment.schedule.cron_expression:
                raise RuntimeError(
                    "The Kubernetes orchestrator only supports scheduling via "
                    "CRON jobs, but the run was configured with a manual "
                    "schedule. Use `Schedule(cron_expression=...)` instead."
                )
            cron_expression = deployment.schedule.cron_expression
            cron_job_manifest = build_cron_job_manifest(
                cron_expression=cron_expression,
                run_name=orchestrator_run_name,
                pod_name=pod_name,
                pipeline_name=pipeline_name,
                image_name=image,
                command=command,
                args=args,
                service_account_name=service_account_name,
                privileged=False,
                pod_settings=orchestrator_pod_settings,
                env=environment,
                mount_local_stores=self.config.is_local,
                successful_jobs_history_limit=settings.successful_jobs_history_limit,
                failed_jobs_history_limit=settings.failed_jobs_history_limit,
                ttl_seconds_after_finished=settings.ttl_seconds_after_finished,
            )

            self._k8s_batch_api.create_namespaced_cron_job(
                body=cron_job_manifest,
                namespace=self.config.kubernetes_namespace,
            )
            logger.info(
                f"Scheduling Kubernetes run `{pod_name}` with CRON expression "
                f'`"{cron_expression}"`.'
            )
            return
        else:
            # Create and run the orchestrator pod.
            pod_manifest = build_pod_manifest(
                run_name=orchestrator_run_name,
                pod_name=pod_name,
                pipeline_name=pipeline_name,
                image_name=image,
                command=command,
                args=args,
                privileged=False,
                pod_settings=orchestrator_pod_settings,
                service_account_name=service_account_name,
                env=environment,
                mount_local_stores=self.config.is_local,
            )

            kube_utils.create_and_wait_for_pod_to_start(
                core_api=self._k8s_core_api,
                pod_display_name="Kubernetes orchestrator pod",
                pod_name=pod_name,
                pod_manifest=pod_manifest,
                namespace=self.config.kubernetes_namespace,
                startup_max_retries=settings.pod_failure_max_retries,
                startup_failure_delay=settings.pod_failure_retry_delay,
                startup_failure_backoff=settings.pod_failure_backoff,
                startup_timeout=settings.pod_startup_timeout,
            )

            # Wait for the orchestrator pod to finish and stream logs.
            if settings.synchronous:
                logger.info(
                    "Waiting for Kubernetes orchestrator pod to finish..."
                )
                kube_utils.wait_pod(
                    kube_client_fn=self.get_kube_client,
                    pod_name=pod_name,
                    namespace=self.config.kubernetes_namespace,
                    exit_condition_lambda=kube_utils.pod_is_done,
                    timeout_sec=settings.timeout,
                    stream_logs=True,
                )
            else:
                logger.info(
                    f"Orchestration started asynchronously in pod "
                    f"`{self.config.kubernetes_namespace}:{pod_name}`. "
                    f"Run the following command to inspect the logs: "
                    f"`kubectl logs {pod_name} -n {self.config.kubernetes_namespace}`."
                )

    def _get_service_account_name(
        self, settings: KubernetesOrchestratorSettings
    ) -> str:
        """Returns the service account name to use for the orchestrator pod.

        If the user has not specified a service account name in the settings,
        we create a new service account with the required permissions.

        Args:
            settings: The orchestrator settings.

        Returns:
            The service account name.
        """
        if settings.service_account_name:
            return settings.service_account_name
        else:
            service_account_name = "zenml-service-account"
            kube_utils.create_edit_service_account(
                core_api=self._k8s_core_api,
                rbac_api=self._k8s_rbac_api,
                service_account_name=service_account_name,
                namespace=self.config.kubernetes_namespace,
            )
            return service_account_name

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_KUBERNETES_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_KUBERNETES_RUN_ID}."
            )

    def _stop_run(
        self, run: "PipelineRunResponse", graceful: bool = True
    ) -> None:
        """Stops a specific pipeline run by terminating step pods.

        Args:
            run: The run that was executed by this orchestrator.
            graceful: If True, does nothing (lets the orchestrator and steps finish naturally).
                If False, stops all running step pods.

        Raises:
            ValueError: If the orchestrator run ID cannot be found.
        """
        # If graceful, do nothing and let the orchestrator handle the stop naturally
        if graceful:
            logger.info(
                "Graceful stop requested - the orchestrator pod will handle "
                "stopping naturally"
            )
            return

        # Get the orchestrator run ID which corresponds to the orchestrator pod name
        orchestrator_run_id = run.orchestrator_run_id
        if not orchestrator_run_id:
            raise ValueError(
                "Cannot determine orchestrator run ID for the run. "
                "Unable to stop the pipeline."
            )

        pods_stopped = []
        errors = []

        # Configure graceful termination settings
        grace_period_seconds = (
            30  # Give pods 30 seconds to gracefully shutdown
        )

        try:
            # Find all pods with the orchestrator run ID label
            label_selector = f"zenml-orchestrator-run-id={orchestrator_run_id}"
            pods = self._k8s_core_api.list_namespaced_pod(
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
            )

            # Filter to only include running or pending pods
            for pod in pods.items:
                if pod.status.phase not in ["Running", "Pending"]:
                    logger.debug(
                        f"Skipping pod {pod.metadata.name} with status {pod.status.phase}"
                    )
                    continue

                try:
                    self._k8s_core_api.delete_namespaced_pod(
                        name=pod.metadata.name,
                        namespace=self.config.kubernetes_namespace,
                        grace_period_seconds=grace_period_seconds,
                    )
                    pods_stopped.append(f"step pod: {pod.metadata.name}")
                    logger.debug(
                        f"Successfully initiated graceful stop of step pod: {pod.metadata.name}"
                    )
                except Exception as e:
                    error_msg = (
                        f"Failed to stop step pod {pod.metadata.name}: {e}"
                    )
                    logger.warning(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            error_msg = (
                f"Failed to list step pods for run {orchestrator_run_id}: {e}"
            )
            logger.warning(error_msg)
            errors.append(error_msg)

        # Summary logging
        if pods_stopped:
            logger.debug(
                f"Successfully initiated graceful termination of: {', '.join(pods_stopped)}. "
                f"Pods will terminate within {grace_period_seconds} seconds."
            )

        if errors:
            error_summary = "; ".join(errors)
            if not pods_stopped:
                # If nothing was stopped successfully, raise an error
                raise RuntimeError(
                    f"Failed to stop pipeline run: {error_summary}"
                )
            else:
                # If some things were stopped but others failed, raise an error
                raise RuntimeError(
                    f"Partial stop operation completed with errors: {error_summary}"
                )

        # If no step pods were found and no errors occurred
        if not pods_stopped and not errors:
            logger.info(
                f"No running step pods found for pipeline run {orchestrator_run_id}"
            )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[ExecutionStatus, Optional[Dict[str, ExecutionStatus]]]:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: The run that was executed by this orchestrator.
            include_steps: If True, also fetch the status of individual steps.

        Returns:
            A tuple of (pipeline_status, step_statuses_dict).
            If include_steps is False, step_statuses_dict will be None.
            If include_steps is True, step_statuses_dict will be a dict (possibly empty).

        Raises:
            ValueError: If the orchestrator run ID cannot be found or if the
                stack components are not accessible.
        """
        # Get the orchestrator run ID which corresponds to the orchestrator pod name
        orchestrator_run_id = run.orchestrator_run_id
        if not orchestrator_run_id:
            raise ValueError(
                "Cannot determine orchestrator run ID for the run. "
                "Unable to fetch the status."
            )

        # Check the orchestrator pod status
        orchestrator_pod = kube_utils.get_pod(
            core_api=self._k8s_core_api,
            pod_name=orchestrator_run_id,
            namespace=self.config.kubernetes_namespace,
        )

        if (
            orchestrator_pod
            and orchestrator_pod.status
            and orchestrator_pod.status.phase
        ):
            try:
                pod_phase = kube_utils.PodPhase(orchestrator_pod.status.phase)
                pipeline_status = self._map_pod_phase_to_execution_status(
                    pod_phase
                )
            except ValueError:
                # Handle unknown pod phases
                pipeline_status = ExecutionStatus.FAILED

        step_status = None
        if include_steps:
            step_status = self._fetch_step_status(run, orchestrator_run_id)

        return pipeline_status, step_status

    def _map_pod_phase_to_execution_status(
        self, pod_phase: kube_utils.PodPhase
    ) -> ExecutionStatus:
        """Map Kubernetes pod phase to ZenML execution status.

        Args:
            pod_phase: The Kubernetes pod phase.

        Returns:
            The corresponding ZenML execution status.
        """
        if pod_phase == kube_utils.PodPhase.PENDING:
            return ExecutionStatus.INITIALIZING
        elif pod_phase == kube_utils.PodPhase.RUNNING:
            return ExecutionStatus.RUNNING
        elif pod_phase == kube_utils.PodPhase.SUCCEEDED:
            return ExecutionStatus.COMPLETED
        elif pod_phase == kube_utils.PodPhase.FAILED:
            return ExecutionStatus.FAILED
        else:  # UNKNOWN
            return ExecutionStatus.FAILED

    def _fetch_step_status(
        self, run: "PipelineRunResponse", orchestrator_run_id: str
    ) -> Dict[str, ExecutionStatus]:
        """Fetch the statuses of individual pipeline steps.

        Args:
            run: The pipeline run response.
            orchestrator_run_id: The orchestrator run ID.

        Returns:
            A dictionary mapping step names to their execution statuses.
        """
        # Get step pod statuses
        step_statuses = {}

        for step_name, step_response in run.steps.items():
            if step_response.status.is_finished:
                continue

            settings = step_response.config.settings.get(
                "orchestrator.kubernetes", None
            )
            settings = KubernetesOrchestratorSettings.model_validate(
                settings.model_dump() if settings else {}
            )
            pod_name = kube_utils.compute_step_pod_name(
                step_name=step_name,
                orchestrator_pod_name=orchestrator_run_id,
                namespace=self.config.kubernetes_namespace,
                settings=settings,
            )
            pod = kube_utils.get_pod(
                core_api=self._k8s_core_api,
                pod_name=pod_name,
                namespace=self.config.kubernetes_namespace,
            )

            if pod and pod.status and pod.status.phase:
                try:
                    step_statuses[step_name] = kube_utils.PodPhase(
                        pod.status.phase
                    )
                except ValueError:
                    # Handle unknown pod phases
                    step_statuses[step_name] = kube_utils.PodPhase.UNKNOWN
            else:
                step_statuses[step_name] = kube_utils.PodPhase.UNKNOWN

        # Convert pod statuses to execution statuses
        for step_name, pod_phase in step_statuses.items():
            new_status = self._map_pod_phase_to_execution_status(pod_phase)
            step_statuses[step_name] = new_status

        return step_statuses
