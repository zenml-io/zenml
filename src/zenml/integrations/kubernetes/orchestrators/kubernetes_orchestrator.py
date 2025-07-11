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
from zenml.constants import (
    METADATA_ORCHESTRATOR_RUN_ID,
)
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
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import (
        PipelineDeploymentBase,
        PipelineDeploymentResponse,
        PipelineRunResponse,
    )
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_KUBERNETES_RUN_ID = "ZENML_KUBERNETES_RUN_ID"
KUBERNETES_SECRET_TOKEN_KEY_NAME = "zenml_api_token"


class KubernetesOrchestrator(ContainerizedOrchestrator):
    """Orchestrator for running ZenML pipelines using native Kubernetes."""

    _k8s_client: Optional[k8s_client.ApiClient] = None

    def should_build_pipeline_image(
        self, deployment: "PipelineDeploymentBase"
    ) -> bool:
        """Whether to always build the pipeline image.

        Args:
            deployment: The pipeline deployment.

        Returns:
            Whether to always build the pipeline image.
        """
        settings = cast(
            KubernetesOrchestratorSettings, self.get_settings(deployment)
        )
        return settings.always_build_pipeline_image

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

    def submit_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to the orchestrator.

        This method should only submit the pipeline and not wait for it to
        complete. If the orchestrator is configured to wait for the pipeline run
        to complete, a function that waits for the pipeline run to complete can
        be passed as part of the submission result.

        Args:
            deployment: The pipeline deployment to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment. These don't need to be set if running locally.
            placeholder_run: An optional placeholder run for the deployment.

        Raises:
            RuntimeError: If a schedule without cron expression is given.

        Returns:
            Optional submission result.
        """
        for step_name, step in deployment.step_configurations.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not yet supported for "
                    "the Kubernetes orchestrator, ignoring resource "
                    "configuration for step %s.",
                    step_name,
                )

            if retry_config := step.config.retry:
                if retry_config.delay or retry_config.backoff:
                    logger.warning(
                        "Specifying retry delay or backoff is not supported "
                        "for the Kubernetes orchestrator."
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
            deployment_id=deployment.id,
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

        orchestrator_pod_labels = {
            "pipeline": kube_utils.sanitize_label(pipeline_name),
        }

        if placeholder_run:
            orchestrator_pod_labels["run_id"] = kube_utils.sanitize_label(
                str(placeholder_run.id)
            )
            orchestrator_pod_labels["run_name"] = kube_utils.sanitize_label(
                str(placeholder_run.name)
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
                pod_name=pod_name,
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
                termination_grace_period_seconds=settings.pod_stop_grace_period,
                labels=orchestrator_pod_labels,
            )

            self._k8s_batch_api.create_namespaced_cron_job(
                body=cron_job_manifest,
                namespace=self.config.kubernetes_namespace,
            )
            logger.info(
                f"Scheduling Kubernetes run `{pod_name}` with CRON expression "
                f'`"{cron_expression}"`.'
            )
            return None
        else:
            # Create and run the orchestrator pod.
            pod_manifest = build_pod_manifest(
                pod_name=pod_name,
                image_name=image,
                command=command,
                args=args,
                privileged=False,
                pod_settings=orchestrator_pod_settings,
                service_account_name=service_account_name,
                env=environment,
                labels=orchestrator_pod_labels,
                mount_local_stores=self.config.is_local,
                termination_grace_period_seconds=settings.pod_stop_grace_period,
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

            metadata: Dict[str, MetadataType] = {
                METADATA_ORCHESTRATOR_RUN_ID: pod_name,
            }

            # Wait for the orchestrator pod to finish and stream logs.
            if settings.synchronous:

                def _wait_for_run_to_finish() -> None:
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

                return SubmissionResult(
                    metadata=metadata,
                    wait_for_completion=_wait_for_run_to_finish,
                )
            else:
                logger.info(
                    f"Orchestration started asynchronously in pod "
                    f"`{self.config.kubernetes_namespace}:{pod_name}`. "
                    f"Run the following command to inspect the logs: "
                    f"`kubectl logs {pod_name} -n {self.config.kubernetes_namespace}`."
                )
                return SubmissionResult(
                    metadata=metadata,
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
                If False, stops all running step jobs.

        Raises:
            RuntimeError: If we fail to stop the run.
        """
        # If graceful, do nothing and let the orchestrator handle the stop naturally
        if graceful:
            logger.info(
                "Graceful stop requested - the orchestrator pod will handle "
                "stopping naturally"
            )
            return

        jobs_stopped = []
        errors = []

        # Find all jobs running steps of the pipeline
        label_selector = f"run_id={kube_utils.sanitize_label(str(run.id))}"
        try:
            jobs = self._k8s_batch_api.list_namespaced_job(
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to list step jobs with run ID {run.id}: {e}"
            )

        for job in jobs.items:
            if job.status.conditions:
                # Don't delete completed/failed jobs
                for condition in job.status.conditions:
                    if (
                        condition.type == "Complete"
                        and condition.status == "True"
                    ):
                        continue
                    if (
                        condition.type == "Failed"
                        and condition.status == "True"
                    ):
                        continue

            try:
                self._k8s_batch_api.delete_namespaced_job(
                    name=job.metadata.name,
                    namespace=self.config.kubernetes_namespace,
                    propagation_policy="Foreground",
                )
                jobs_stopped.append(f"step job: {job.metadata.name}")
                logger.debug(
                    f"Successfully initiated graceful stop of step job: {job.metadata.name}"
                )
            except Exception as e:
                error_msg = f"Failed to stop step job {job.metadata.name}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Summary logging
        settings = cast(KubernetesOrchestratorSettings, self.get_settings(run))
        grace_period_seconds = settings.pod_stop_grace_period
        if jobs_stopped:
            logger.debug(
                f"Successfully initiated graceful termination of: {', '.join(jobs_stopped)}. "
                f"Pods will terminate within {grace_period_seconds} seconds."
            )

        if errors:
            error_summary = "; ".join(errors)
            if not jobs_stopped:
                # If nothing was stopped successfully, raise an error
                raise RuntimeError(
                    f"Failed to stop pipeline run: {error_summary}"
                )
            else:
                # If some things were stopped but others failed, raise an error
                raise RuntimeError(
                    f"Partial stop operation completed with errors: {error_summary}"
                )

        if not jobs_stopped and not errors:
            logger.info(
                f"No running step jobs found for pipeline run with ID: {run.id}"
            )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[
        Optional[ExecutionStatus], Optional[Dict[str, ExecutionStatus]]
    ]:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: The run that was executed by this orchestrator.
            include_steps: If True, also fetch the status of individual steps.

        Returns:
            A tuple of (pipeline_status, step_statuses).
            If include_steps is False, step_statuses will be None.
            If include_steps is True, step_statuses will be a dict (possibly empty).

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

        # Check the orchestrator pod status (only if run is not finished)
        if not run.status.is_finished:
            orchestrator_pod_phase = self._check_pod_status(
                pod_name=orchestrator_run_id,
            )
            pipeline_status = self._map_pod_phase_to_execution_status(
                orchestrator_pod_phase
            )
        else:
            # Run is already finished, don't change status
            pipeline_status = None

        step_statuses = None
        if include_steps:
            step_statuses = self._fetch_step_statuses(run)

        return pipeline_status, step_statuses

    def _check_pod_status(
        self,
        pod_name: str,
    ) -> kube_utils.PodPhase:
        """Check pod status and handle deletion scenarios for both orchestrator and step pods.

        This method should only be called for non-finished pipeline runs/steps.

        Args:
            pod_name: The name of the pod to check.

        Returns:
            The pod phase if the pod exists, or PodPhase.FAILED if pod was deleted.
        """
        pod = kube_utils.get_pod(
            core_api=self._k8s_core_api,
            pod_name=pod_name,
            namespace=self.config.kubernetes_namespace,
        )

        if pod and pod.status and pod.status.phase:
            try:
                return kube_utils.PodPhase(pod.status.phase)
            except ValueError:
                # Handle unknown pod phases
                logger.warning(
                    f"Unknown pod phase for pod {pod_name}: {pod.status.phase}"
                )
                return kube_utils.PodPhase.UNKNOWN
        else:
            logger.warning(
                f"Can't fetch the status of pod {pod_name} "
                f"in namespace {self.config.kubernetes_namespace}."
            )
            return kube_utils.PodPhase.UNKNOWN

    def _map_pod_phase_to_execution_status(
        self, pod_phase: kube_utils.PodPhase
    ) -> Optional[ExecutionStatus]:
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
        else:  # UNKNOWN - no update
            return None

    def _map_job_status_to_execution_status(
        self, job: k8s_client.V1Job
    ) -> Optional[ExecutionStatus]:
        """Map Kubernetes job status to ZenML execution status.

        Args:
            job: The Kubernetes job.

        Returns:
            The corresponding ZenML execution status, or None if no clear status.
        """
        # Check job conditions first
        if job.status and job.status.conditions:
            for condition in job.status.conditions:
                if condition.type == "Complete" and condition.status == "True":
                    return ExecutionStatus.COMPLETED
                elif condition.type == "Failed" and condition.status == "True":
                    return ExecutionStatus.FAILED

        # Return None if no clear status - don't update
        return None

    def _fetch_step_statuses(
        self, run: "PipelineRunResponse"
    ) -> Dict[str, ExecutionStatus]:
        """Fetch the statuses of individual pipeline steps.

        Args:
            run: The pipeline run response.

        Returns:
            A dictionary mapping step names to their execution statuses.
        """
        step_statuses = {}

        # Query all jobs for this run and match them to steps
        label_selector = f"run_id={kube_utils.sanitize_label(str(run.id))}"

        try:
            jobs = self._k8s_batch_api.list_namespaced_job(
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
            )
        except Exception as e:
            logger.warning(f"Failed to list jobs for run {run.id}: {e}")
            return {}

        # Fetch the steps from the run response
        steps_dict = run.steps

        for job in jobs.items:
            # Extract step name from job labels
            if not job.metadata or not job.metadata.labels:
                continue

            step_name = job.metadata.labels.get("step_name")
            if not step_name:
                continue

            # Check if this step is already finished
            step_response = steps_dict.get(step_name, None)

            # If the step is not in the run response yet, skip, we can't update
            if step_response is None:
                continue

            # If the step is already in a finished state, skip
            if step_response and step_response.status.is_finished:
                continue

            # Check job status and map to execution status
            execution_status = self._map_job_status_to_execution_status(job)
            if execution_status is not None:
                step_statuses[step_name] = execution_status

        return step_statuses

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        return {
            METADATA_ORCHESTRATOR_RUN_ID: self.get_orchestrator_run_id(),
        }
