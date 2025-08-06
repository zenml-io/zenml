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
import random
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
from zenml.integrations.kubernetes.constants import (
    ENV_ZENML_KUBERNETES_RUN_ID,
    KUBERNETES_CRON_JOB_METADATA_KEY,
    KUBERNETES_SECRET_TOKEN_KEY_NAME,
    ORCHESTRATOR_ANNOTATION_KEY,
    STEP_NAME_ANNOTATION_KEY,
)
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
    build_job_manifest,
    build_pod_manifest,
    job_template_manifest_from_job,
    pod_template_manifest_from_pod,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.core.schedule import ScheduleUpdate
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.models import (
        PipelineDeploymentBase,
        PipelineDeploymentResponse,
        PipelineRunResponse,
        ScheduleResponse,
    )
    from zenml.stack import Stack

logger = get_logger(__name__)


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
            Exception: If the orchestrator pod fails to start.

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
        orchestrator_pod_settings = kube_utils.apply_default_resource_requests(
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
                placeholder_run.name
            )

        pod_manifest = build_pod_manifest(
            pod_name=None,
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

        pod_failure_policy = settings.pod_failure_policy or {
            # These rules are applied sequentially. This means any failure in
            # the main container will count towards the max retries. Any other
            # disruption will not count towards the max retries.
            "rules": [
                # If the main container fails, we count it towards the max
                # retries.
                {
                    "action": "Count",
                    "onExitCodes": {
                        "containerName": "main",
                        "operator": "NotIn",
                        "values": [0],
                    },
                },
                # If the pod is interrupted at any other time, we don't count
                # it as a retry
                {
                    "action": "Ignore",
                    "onPodConditions": [
                        {
                            "type": "DisruptionTarget",
                            "status": "True",
                        }
                    ],
                },
            ]
        }

        job_name = settings.job_name_prefix or ""
        random_prefix = "".join(random.choices("0123456789abcdef", k=8))
        job_name += (
            f"-{random_prefix}-{deployment.pipeline_configuration.name}"
        )
        # The job name will be used as a label on the pods, so we need to make
        # sure it doesn't exceed the label length limit
        job_name = kube_utils.sanitize_label(job_name)

        job_manifest = build_job_manifest(
            job_name=job_name,
            pod_template=pod_template_manifest_from_pod(pod_manifest),
            backoff_limit=settings.orchestrator_job_backoff_limit,
            ttl_seconds_after_finished=settings.ttl_seconds_after_finished,
            active_deadline_seconds=settings.active_deadline_seconds,
            pod_failure_policy=pod_failure_policy,
            labels=orchestrator_pod_labels,
            annotations={
                ORCHESTRATOR_ANNOTATION_KEY: str(self.id),
            },
        )

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
                job_template=job_template_manifest_from_job(job_manifest),
                successful_jobs_history_limit=settings.successful_jobs_history_limit,
                failed_jobs_history_limit=settings.failed_jobs_history_limit,
            )

            cron_job = self._k8s_batch_api.create_namespaced_cron_job(
                body=cron_job_manifest,
                namespace=self.config.kubernetes_namespace,
            )
            logger.info(
                f"Created Kubernetes CronJob `{cron_job.metadata.name}` "
                f"with CRON expression `{cron_expression}`."
            )
            return SubmissionResult(
                metadata={
                    KUBERNETES_CRON_JOB_METADATA_KEY: cron_job.metadata.name,
                }
            )
        else:
            try:
                kube_utils.create_job(
                    batch_api=self._k8s_batch_api,
                    namespace=self.config.kubernetes_namespace,
                    job_manifest=job_manifest,
                )
            except Exception as e:
                if self.config.pass_zenml_token_as_secret:
                    secret_name = self.get_token_secret_name(deployment.id)
                    try:
                        kube_utils.delete_secret(
                            core_api=self._k8s_core_api,
                            namespace=self.config.kubernetes_namespace,
                            secret_name=secret_name,
                        )
                    except Exception as cleanup_error:
                        logger.error(
                            "Error cleaning up secret %s: %s",
                            secret_name,
                            cleanup_error,
                        )
                raise e

            if settings.synchronous:

                def _wait_for_run_to_finish() -> None:
                    logger.info("Waiting for orchestrator job to finish...")
                    kube_utils.wait_for_job_to_finish(
                        batch_api=self._k8s_batch_api,
                        core_api=self._k8s_core_api,
                        namespace=self.config.kubernetes_namespace,
                        job_name=job_name,
                        backoff_interval=settings.job_monitoring_interval,
                        fail_on_container_waiting_reasons=settings.fail_on_container_waiting_reasons,
                        stream_logs=True,
                    )

                return SubmissionResult(
                    wait_for_completion=_wait_for_run_to_finish,
                )
            else:
                logger.info(
                    f"Orchestrator job `{job_name}` started. "
                    f"Run the following command to inspect the logs: "
                    f"`kubectl -n {self.config.kubernetes_namespace} logs "
                    f"job/{job_name}`"
                )
                return None

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
            job_list = kube_utils.list_jobs(
                batch_api=self._k8s_batch_api,
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to list step jobs with run ID {run.id}: {e}"
            )

        for job in job_list.items:
            if not kube_utils.is_step_job(job):
                # This is the orchestrator job which stops by itself
                continue

            if job.status and job.status.conditions:
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
        """
        pipeline_status = None
        include_run_status = not run.status.is_finished

        label_selector = f"run_id={kube_utils.sanitize_label(str(run.id))}"
        try:
            job_list = kube_utils.list_jobs(
                batch_api=self._k8s_batch_api,
                namespace=self.config.kubernetes_namespace,
                label_selector=label_selector,
            )
        except Exception as e:
            logger.warning(f"Failed to list jobs for run {run.id}: {e}")
            return None, None

        step_statuses = {}
        # Only fetch steps if we really need them
        steps_dict = run.steps if include_steps else {}

        for job in job_list.items:
            if not job.metadata or not job.metadata.annotations:
                continue

            is_orchestrator_job = (
                ORCHESTRATOR_ANNOTATION_KEY in job.metadata.annotations
            )
            if is_orchestrator_job:
                if include_run_status:
                    pipeline_status = self._map_job_status_to_execution_status(
                        job
                    )
                continue

            step_name = job.metadata.annotations.get(
                STEP_NAME_ANNOTATION_KEY, None
            )
            if not include_steps or not step_name:
                continue

            step_response = steps_dict.get(step_name, None)

            if step_response is None:
                continue

            # If the step is already in a finished state, skip
            if step_response and step_response.status.is_finished:
                continue

            execution_status = self._map_job_status_to_execution_status(job)
            if execution_status is not None:
                step_statuses[step_name] = execution_status

        return pipeline_status, step_statuses

    def _map_job_status_to_execution_status(
        self, job: k8s_client.V1Job
    ) -> Optional[ExecutionStatus]:
        """Map Kubernetes job status to ZenML execution status.

        Args:
            job: The Kubernetes job.

        Returns:
            The corresponding ZenML execution status, or None if no clear status.
        """
        if job.status and job.status.conditions:
            for condition in job.status.conditions:
                if condition.type == "Complete" and condition.status == "True":
                    return ExecutionStatus.COMPLETED
                elif condition.type == "Failed" and condition.status == "True":
                    return ExecutionStatus.FAILED

        # Return None if no clear status - don't update
        return None

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

    def update_schedule(
        self, schedule: "ScheduleResponse", update: ScheduleUpdate
    ) -> None:
        """Updates a schedule.

        Args:
            schedule: The schedule to update.
            update: The update to apply to the schedule.

        Raises:
            RuntimeError: If the cron job name is not found.
        """
        cron_job_name = schedule.run_metadata.get(
            KUBERNETES_CRON_JOB_METADATA_KEY
        )
        if not cron_job_name:
            raise RuntimeError("Unable to find cron job name for schedule.")

        if update.cron_expression:
            self._k8s_batch_api.patch_namespaced_cron_job(
                name=cron_job_name,
                namespace=self.config.kubernetes_namespace,
                body={"spec": {"schedule": update.cron_expression}},
            )

    def delete_schedule(self, schedule: "ScheduleResponse") -> None:
        """Deletes a schedule.

        Args:
            schedule: The schedule to delete.

        Raises:
            RuntimeError: If the cron job name is not found.
        """
        cron_job_name = schedule.run_metadata.get(
            KUBERNETES_CRON_JOB_METADATA_KEY
        )
        if not cron_job_name:
            raise RuntimeError("Unable to find cron job name for schedule.")

        self._k8s_batch_api.delete_namespaced_cron_job(
            name=cron_job_name,
            namespace=self.config.kubernetes_namespace,
        )
