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
"""Entrypoint of the Kubernetes master/orchestrator pod."""

import argparse
import random
import socket
import threading
import time
from typing import List, Optional, Tuple, cast
from uuid import UUID

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import ExecutionStatus
from zenml.exceptions import AuthorizationException
from zenml.integrations.kubernetes.constants import (
    ENV_ZENML_KUBERNETES_RUN_ID,
    KUBERNETES_SECRET_TOKEN_KEY_NAME,
    ORCHESTRATOR_RUN_ID_ANNOTATION_KEY,
    RUN_ID_ANNOTATION_KEY,
    STEP_NAME_ANNOTATION_KEY,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator import (
    KubernetesOrchestrator,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_job_manifest,
    build_pod_manifest,
    pod_template_manifest_from_pod,
)
from zenml.logger import get_logger
from zenml.logging.step_logging import setup_orchestrator_logging
from zenml.models import PipelineDeploymentResponse, PipelineRunResponse
from zenml.orchestrators import publish_utils
from zenml.orchestrators.step_run_utils import (
    StepRunRequestFactory,
    fetch_step_runs_by_names,
    publish_cached_step_run,
)
from zenml.orchestrators.utils import (
    get_config_environment_vars,
)
from zenml.pipelines.run_utils import create_placeholder_run

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def _get_orchestrator_job_state(
    batch_api: k8s_client.BatchV1Api, namespace: str, job_name: str
) -> Tuple[Optional[UUID], Optional[str]]:
    """Get the existing status of the orchestrator job.

    Args:
        batch_api: The batch api.
        namespace: The namespace.
        job_name: The name of the orchestrator job.

    Returns:
        The run id and orchestrator run id.
    """
    run_id = None
    orchestrator_run_id = None

    job = kube_utils.get_job(
        batch_api=batch_api,
        namespace=namespace,
        job_name=job_name,
    )

    if job.metadata and job.metadata.annotations:
        annotations = job.metadata.annotations

        run_id = annotations.get(RUN_ID_ANNOTATION_KEY, None)
        orchestrator_run_id = annotations.get(
            ORCHESTRATOR_RUN_ID_ANNOTATION_KEY, None
        )

    return UUID(run_id) if run_id else None, orchestrator_run_id


def _reconstruct_nodes(
    deployment: PipelineDeploymentResponse,
    pipeline_run: PipelineRunResponse,
    namespace: str,
    batch_api: k8s_client.BatchV1Api,
) -> List[Node]:
    """Reconstruct the nodes from the pipeline run.

    Args:
        deployment: The deployment.
        pipeline_run: The pipeline run.
        namespace: The namespace.
        batch_api: The batch api.

    Returns:
        The reconstructed nodes.
    """
    nodes = {
        step_name: Node(id=step_name, upstream_nodes=step.spec.upstream_steps)
        for step_name, step in deployment.step_configurations.items()
    }

    for step_name, existing_step_run in pipeline_run.steps.items():
        node = nodes[step_name]
        if existing_step_run.status.is_successful:
            node.status = NodeStatus.COMPLETED
        elif existing_step_run.status.is_finished:
            node.status = NodeStatus.FAILED

    job_list = kube_utils.list_jobs(
        batch_api=batch_api,
        namespace=namespace,
        label_selector=f"run_id={pipeline_run.id}",
    )
    for job in job_list.items:
        annotations = job.metadata.annotations or {}
        if step_name := annotations.get(STEP_NAME_ANNOTATION_KEY, None):
            node = nodes[step_name]
            node.metadata["job_name"] = job.metadata.name

            if node.status == NodeStatus.NOT_READY:
                # The step is not finished in the ZenML database, so we base it
                # on the job status.
                node_status = NodeStatus.RUNNING
                if job.status.conditions:
                    for condition in job.status.conditions:
                        if (
                            condition.type == "Complete"
                            and condition.status == "True"
                        ):
                            node_status = NodeStatus.COMPLETED
                            break
                        elif (
                            condition.type == "Failed"
                            and condition.status == "True"
                        ):
                            node_status = NodeStatus.FAILED
                            break

                node.status = node_status
                logger.debug(
                    "Existing job for step `%s` status: %s.",
                    step_name,
                    node_status,
                )

    return list(nodes.values())


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod.

    Raises:
        RuntimeError: If the orchestrator pod is not associated with a job.
    """
    logger.info("Orchestrator pod started.")

    args = parse_args()

    orchestrator_pod_name = socket.gethostname()

    client = Client()
    deployment = client.get_deployment(args.deployment_id)
    active_stack = client.active_stack
    orchestrator = active_stack.orchestrator
    assert isinstance(orchestrator, KubernetesOrchestrator)
    namespace = orchestrator.config.kubernetes_namespace

    pipeline_settings = cast(
        KubernetesOrchestratorSettings,
        orchestrator.get_settings(deployment),
    )

    # Get a Kubernetes client from the active Kubernetes orchestrator, but
    # override the `incluster` setting to `True` since we are running inside
    # the Kubernetes cluster.
    api_client_config = orchestrator.get_kube_client(
        incluster=True
    ).configuration
    api_client_config.connection_pool_maxsize = (
        pipeline_settings.max_parallelism
    )
    kube_client = k8s_client.ApiClient(api_client_config)
    core_api = k8s_client.CoreV1Api(kube_client)
    batch_api = k8s_client.BatchV1Api(kube_client)

    job_name = kube_utils.get_parent_job_name(
        core_api=core_api,
        pod_name=orchestrator_pod_name,
        namespace=namespace,
    )
    if not job_name:
        raise RuntimeError("Failed to fetch job name for orchestrator pod.")

    run_id, orchestrator_run_id = _get_orchestrator_job_state(
        batch_api=batch_api,
        namespace=namespace,
        job_name=job_name,
    )
    existing_logs_response = None

    if run_id and orchestrator_run_id:
        logger.info("Continuing existing run `%s`.", run_id)
        pipeline_run = client.get_pipeline_run(run_id)
        nodes = _reconstruct_nodes(
            deployment=deployment,
            pipeline_run=pipeline_run,
            namespace=namespace,
            batch_api=batch_api,
        )
        logger.debug("Reconstructed nodes: %s", nodes)

        # Continue logging to the same log file if it exists
        for log_response in pipeline_run.log_collection or []:
            if log_response.source == "orchestrator":
                existing_logs_response = log_response
                break
    else:
        orchestrator_run_id = orchestrator_pod_name
        if args.run_id:
            pipeline_run = client.get_pipeline_run(args.run_id)
        else:
            pipeline_run = create_placeholder_run(
                deployment=deployment,
                orchestrator_run_id=orchestrator_run_id,
            )

        # Store in the job annotations so we can continue the run if the pod
        # is restarted
        kube_utils.update_job(
            batch_api=batch_api,
            namespace=namespace,
            job_name=job_name,
            annotations={
                RUN_ID_ANNOTATION_KEY: str(pipeline_run.id),
                ORCHESTRATOR_RUN_ID_ANNOTATION_KEY: orchestrator_run_id,
            },
        )
        nodes = [
            Node(id=step_name, upstream_nodes=step.spec.upstream_steps)
            for step_name, step in deployment.step_configurations.items()
        ]

    logs_context = setup_orchestrator_logging(
        run_id=pipeline_run.id,
        deployment=deployment,
        logs_response=existing_logs_response,
    )

    with logs_context:
        step_command = StepEntrypointConfiguration.get_entrypoint_command()
        mount_local_stores = active_stack.orchestrator.config.is_local

        env = get_config_environment_vars()
        env[ENV_ZENML_KUBERNETES_RUN_ID] = orchestrator_run_id

        try:
            owner_references = kube_utils.get_pod_owner_references(
                core_api=core_api,
                pod_name=orchestrator_pod_name,
                namespace=namespace,
            )
        except Exception as e:
            logger.warning(f"Failed to get pod owner references: {str(e)}")
            owner_references = []
        else:
            # Make sure None of the owner references are marked as controllers of
            # the created pod, which messes with the garbage collection logic.
            for owner_reference in owner_references:
                owner_reference.controller = False

        step_run_request_factory = StepRunRequestFactory(
            deployment=deployment,
            pipeline_run=pipeline_run,
            stack=active_stack,
        )
        step_runs = {}

        base_labels = {
            "run_id": kube_utils.sanitize_label(str(pipeline_run.id)),
            "run_name": kube_utils.sanitize_label(str(pipeline_run.name)),
            "pipeline": kube_utils.sanitize_label(
                deployment.pipeline_configuration.name
            ),
        }

        def _cache_step_run_if_possible(step_name: str) -> bool:
            if not step_run_request_factory.has_caching_enabled(step_name):
                return False

            step_run_request = step_run_request_factory.create_request(
                step_name
            )
            try:
                step_run_request_factory.populate_request(step_run_request)
            except Exception as e:
                logger.error(
                    f"Failed to populate step run request for step {step_name}: {e}"
                )
                return False

            if step_run_request.status == ExecutionStatus.CACHED:
                step_run = publish_cached_step_run(
                    step_run_request, pipeline_run
                )
                step_runs[step_name] = step_run
                logger.info("Using cached version of step `%s`.", step_name)
                return True

            return False

        startup_lock = threading.Lock()
        last_startup_time: float = 0.0

        def start_step_job(node: Node) -> NodeStatus:
            """Run a pipeline step in a separate Kubernetes pod.

            Args:
                node: The node to start.

            Returns:
                The status of the node.
            """
            step_name = node.id
            step_config = deployment.step_configurations[step_name].config
            settings = step_config.settings.get(
                "orchestrator.kubernetes", None
            )
            settings = KubernetesOrchestratorSettings.model_validate(
                settings.model_dump() if settings else {}
            )
            if not pipeline_settings.prevent_orchestrator_pod_caching:
                if _cache_step_run_if_possible(step_name):
                    return NodeStatus.COMPLETED

            step_labels = base_labels.copy()
            step_labels["step_name"] = kube_utils.sanitize_label(step_name)
            step_annotations = {
                STEP_NAME_ANNOTATION_KEY: step_name,
            }

            image = KubernetesOrchestrator.get_image(
                deployment=deployment, step_name=step_name
            )
            step_args = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, deployment_id=deployment.id
            )

            # We set some default minimum memory resource requests for the step pod
            # here if the user has not specified any, because the step pod takes up
            # some memory resources itself and, if not specified, the pod will be
            # scheduled on any node regardless of available memory and risk
            # negatively impacting or even crashing the node due to memory pressure.
            pod_settings = kube_utils.apply_default_resource_requests(
                memory="400Mi",
                pod_settings=settings.pod_settings,
            )

            if orchestrator.config.pass_zenml_token_as_secret:
                env.pop("ZENML_STORE_API_TOKEN", None)
                secret_name = orchestrator.get_token_secret_name(deployment.id)
                pod_settings.env.append(
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

            pod_manifest = build_pod_manifest(
                pod_name=None,
                image_name=image,
                command=step_command,
                args=step_args,
                env=env,
                privileged=settings.privileged,
                pod_settings=pod_settings,
                service_account_name=settings.step_pod_service_account_name
                or settings.service_account_name,
                mount_local_stores=mount_local_stores,
                termination_grace_period_seconds=settings.pod_stop_grace_period,
                labels=step_labels,
            )

            retry_config = step_config.retry
            backoff_limit = (
                retry_config.max_retries if retry_config else 0
            ) + settings.backoff_limit_margin

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
                            }
                        ],
                    },
                ]
            }

            job_name = settings.job_name_prefix or ""
            random_prefix = "".join(random.choices("0123456789abcdef", k=8))
            job_name += f"-{random_prefix}-{step_name}-{deployment.pipeline_configuration.name}"
            # The job name will be used as a label on the pods, so we need to make
            # sure it doesn't exceed the label length limit
            job_name = kube_utils.sanitize_label(job_name)

            job_manifest = build_job_manifest(
                job_name=job_name,
                pod_template=pod_template_manifest_from_pod(pod_manifest),
                backoff_limit=backoff_limit,
                ttl_seconds_after_finished=settings.ttl_seconds_after_finished,
                active_deadline_seconds=settings.active_deadline_seconds,
                pod_failure_policy=pod_failure_policy,
                owner_references=owner_references,
                labels=step_labels,
                annotations=step_annotations,
            )

            if (
                startup_interval
                := orchestrator.config.parallel_step_startup_waiting_period
            ):
                nonlocal last_startup_time

                with startup_lock:
                    now = time.time()
                    time_since_last_startup = now - last_startup_time
                    sleep_time = startup_interval - time_since_last_startup
                    if sleep_time > 0:
                        logger.debug(
                            f"Sleeping for {sleep_time} seconds before "
                            f"starting job for step {step_name}."
                        )
                        time.sleep(sleep_time)
                    last_startup_time = now

            kube_utils.create_job(
                batch_api=batch_api,
                namespace=namespace,
                job_manifest=job_manifest,
            )

            node.metadata["job_name"] = job_name

            return NodeStatus.RUNNING

        def check_job_status(node: Node) -> NodeStatus:
            """Check the status of a job.

            Args:
                node: The node to check.

            Returns:
                The status of the node.
            """
            step_name = node.id
            job_name = node.metadata.get("job_name", None)
            if not job_name:
                logger.error(
                    "Missing job name to monitor step `%s`.", step_name
                )
                return NodeStatus.FAILED

            step_config = deployment.step_configurations[step_name].config
            settings = step_config.settings.get(
                "orchestrator.kubernetes", None
            )
            settings = KubernetesOrchestratorSettings.model_validate(
                settings.model_dump() if settings else {}
            )
            status, error_message = kube_utils.check_job_status(
                batch_api=batch_api,
                core_api=core_api,
                namespace=namespace,
                job_name=job_name,
                fail_on_container_waiting_reasons=settings.fail_on_container_waiting_reasons,
            )
            if status == kube_utils.JobStatus.SUCCEEDED:
                return NodeStatus.COMPLETED
            elif status == kube_utils.JobStatus.FAILED:
                logger.error(
                    "Job for step `%s` failed: %s",
                    step_name,
                    error_message,
                )
                return NodeStatus.FAILED
            else:
                return NodeStatus.RUNNING

        def should_interrupt_execution() -> Optional[InterruptMode]:
            """Check if the DAG execution should be interrupted.

            Returns:
                If the DAG execution should be interrupted.
            """
            try:
                run = client.get_pipeline_run(
                    name_id_or_prefix=pipeline_run.id,
                    project=pipeline_run.project_id,
                    hydrate=False,  # We only need status, not full hydration
                )

                if run.status in [
                    ExecutionStatus.STOPPING,
                    ExecutionStatus.STOPPED,
                ]:
                    logger.info(
                        "Stopping DAG execution because pipeline run is in "
                        "`%s` state.",
                        run.status,
                    )
                    return InterruptMode.GRACEFUL
            except Exception as e:
                logger.warning(
                    "Failed to check pipeline cancellation status: %s", e
                )

            return None

        try:
            nodes_statuses = DagRunner(
                nodes=nodes,
                node_startup_function=start_step_job,
                node_monitoring_function=check_job_status,
                interrupt_function=should_interrupt_execution,
                monitoring_interval=pipeline_settings.job_monitoring_interval,
                monitoring_delay=pipeline_settings.job_monitoring_delay,
                interrupt_check_interval=pipeline_settings.interrupt_check_interval,
                max_parallelism=pipeline_settings.max_parallelism,
            ).run()
        finally:
            if (
                orchestrator.config.pass_zenml_token_as_secret
                and deployment.schedule is None
            ):
                secret_name = orchestrator.get_token_secret_name(deployment.id)
                try:
                    kube_utils.delete_secret(
                        core_api=core_api,
                        namespace=namespace,
                        secret_name=secret_name,
                    )
                except ApiException as e:
                    logger.error(
                        f"Error cleaning up secret {secret_name}: {e}"
                    )

        try:
            pipeline_failed = False
            failed_step_names = [
                step_name
                for step_name, node_state in nodes_statuses.items()
                if node_state == NodeStatus.FAILED
            ]
            skipped_step_names = [
                step_name
                for step_name, node_state in nodes_statuses.items()
                if node_state == NodeStatus.SKIPPED
            ]

            if failed_step_names:
                logger.error(
                    "The following steps failed: %s",
                    ", ".join(failed_step_names),
                )
            if skipped_step_names:
                logger.error(
                    "The following steps were skipped because some of their "
                    "upstream steps failed: %s",
                    ", ".join(skipped_step_names),
                )

            step_runs = fetch_step_runs_by_names(
                step_run_names=failed_step_names, pipeline_run=pipeline_run
            )

            for step_name, node_state in nodes_statuses.items():
                if node_state != NodeStatus.FAILED:
                    continue

                pipeline_failed = True

                if step_run := step_runs.get(step_name, None):
                    # Try to update the step run status, if it exists and is in
                    # a transient state.
                    if step_run and step_run.status in {
                        ExecutionStatus.INITIALIZING,
                        ExecutionStatus.RUNNING,
                    }:
                        publish_utils.publish_failed_step_run(step_run.id)

            # If any steps failed and the pipeline run is still in a transient
            # state, we need to mark it as failed.
            if pipeline_failed and pipeline_run.status in {
                ExecutionStatus.INITIALIZING,
                ExecutionStatus.RUNNING,
            }:
                publish_utils.publish_failed_pipeline_run(pipeline_run.id)
        except AuthorizationException:
            # If a step of the pipeline failed or all of them completed
            # successfully, the pipeline run will be finished and the API token
            # will be invalidated. We catch this exception and do nothing here,
            # as the pipeline run status will already have been published.
            pass

        logger.info("Orchestrator pod finished.")


if __name__ == "__main__":
    main()
