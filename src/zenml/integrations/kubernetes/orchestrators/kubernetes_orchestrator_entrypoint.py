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
from typing import Dict, List, Optional, cast
from uuid import UUID

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
from pydantic import BaseModel

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import ExecutionStatus
from zenml.exceptions import AuthorizationException
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator import (
    ENV_ZENML_KUBERNETES_RUN_ID,
    KUBERNETES_SECRET_TOKEN_KEY_NAME,
    KubernetesOrchestrator,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_job_manifest,
    build_pod_manifest,
    pod_template_manifest_from_pod,
)
from zenml.integrations.kubernetes.orchestrators.new_dag_runner import (
    DagRunner,
    Node,
    NodeStatus,
)
from zenml.logger import get_logger
from zenml.logging.step_logging import setup_orchestrator_logging
from zenml.orchestrators import publish_utils

# from zenml.orchestrators.dag_runner import NodeStatus, ThreadedDagRunner
from zenml.orchestrators.step_run_utils import (
    StepRunRequestFactory,
    fetch_step_runs_by_names,
    publish_cached_step_run,
)
from zenml.orchestrators.utils import (
    get_config_environment_vars,
    get_orchestrator_run_name,
)
from zenml.pipelines.run_utils import create_placeholder_run

logger = get_logger(__name__)


class OrchestratorPodState(BaseModel):
    run_id: UUID
    orchestrator_run_id: str
    nodes: List[Node]


def load_state(
    core_api: k8s_client.CoreV1Api, namespace: str, config_map_name: str
) -> Optional[OrchestratorPodState]:
    """Load the state of the orchestrator.

    Returns:
        The state of the orchestrator.
    """
    try:
        configmap = kube_utils.get_config_map(
            core_api=core_api,
            namespace=namespace,
            name=config_map_name,
        )
    except ApiException:
        return None

    logger.info("Configmap: %s", configmap)
    state = configmap.data["state"]
    return OrchestratorPodState.model_validate_json(state)


def store_state(
    state: OrchestratorPodState,
    core_api: k8s_client.CoreV1Api,
    namespace: str,
    config_map_name,
) -> None:
    """Store the state of the orchestrator.

    Args:
        state: The state to store.
    """
    try:
        kube_utils.update_config_map(
            core_api=core_api,
            namespace=namespace,
            name=config_map_name,
            data={"state": state.model_dump_json()},
        )
    except ApiException as e:
        if e.status == 404:
            kube_utils.create_config_map(
                core_api=core_api,
                namespace=namespace,
                name=config_map_name,
                data={"state": state.model_dump_json()},
            )


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Kubernetes orchestrator pod started.")

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

    pod = kube_utils.get_pod(
        core_api, pod_name=orchestrator_pod_name, namespace=namespace
    )
    # We use the orchestrator pod name as fallback, but the job name should
    # always be set anyway.
    config_map_name = pod.metadata.labels.get(
        "job-name", orchestrator_pod_name
    )

    existing_logs_response = None

    if existing_state := load_state(core_api, namespace, config_map_name):
        orchestrator_run_id = existing_state.orchestrator_run_id
        nodes = existing_state.nodes
        pipeline_run = client.get_pipeline_run(existing_state.run_id)

        for log_response in pipeline_run.log_collection:
            if log_response.source == "orchestrator":
                existing_logs_response = log_response
                break
    else:
        orchestrator_run_id = orchestrator_pod_name
        nodes = [
            Node(id=step_name, upstream_nodes=step.spec.upstream_steps)
            for step_name, step in deployment.step_configurations.items()
        ]
        if args.run_id:
            pipeline_run = client.get_pipeline_run(args.run_id)
        else:
            pipeline_run = create_placeholder_run(
                deployment=deployment,
                orchestrator_run_id=orchestrator_run_id,
            )
        store_state(
            OrchestratorPodState(
                run_id=pipeline_run.id,
                orchestrator_run_id=orchestrator_run_id,
                nodes=nodes,
            ),
            core_api,
            namespace,
            config_map_name,
        )

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

        def _try_to_cache_step_run(step_name: str) -> bool:
            """Try to cache a step run."""
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

        def start_step_job(node: Node) -> NodeStatus:
            """Run a pipeline step in a separate Kubernetes pod.

            Args:
                step_name: Name of the step.

            Raises:
                Exception: If the pod fails to start.
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
                # TODO: This currently waits for max_parallelism, is that
                # what we want?
                if _try_to_cache_step_run(step_name):
                    return NodeStatus.COMPLETED

            if (
                settings.pod_name_prefix
                and not orchestrator_pod_name.startswith(
                    settings.pod_name_prefix
                )
            ):
                max_length = (
                    kube_utils.calculate_max_pod_name_length_for_namespace(
                        namespace=namespace
                    )
                )
                pod_name_prefix = get_orchestrator_run_name(
                    settings.pod_name_prefix, max_length=max_length
                )
                pod_name = f"{pod_name_prefix}-{step_name}"
            else:
                pod_name = f"{orchestrator_pod_name}-{step_name}"

            pod_name = kube_utils.sanitize_pod_name(
                pod_name, namespace=namespace
            )

            step_labels = base_labels.copy()
            step_labels["step_name"] = kube_utils.sanitize_label(step_name)

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
            pod_settings = (
                KubernetesOrchestrator.apply_default_resource_requests(
                    memory="400Mi",
                    pod_settings=settings.pod_settings,
                )
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
                pod_name=pod_name,
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
            )

            kube_utils.create_job(
                batch_api=batch_api,
                namespace=namespace,
                job_manifest=job_manifest,
            )

            node.metadata["job_name"] = job_name

            return NodeStatus.RUNNING

        def check_job_status(node: Node) -> NodeStatus:
            step_name = node.id
            job_name = node.metadata["job_name"]
            step_config = deployment.step_configurations[step_name].config
            settings = step_config.settings.get(
                "orchestrator.kubernetes", None
            )
            settings = KubernetesOrchestratorSettings.model_validate(
                settings.model_dump() if settings else {}
            )
            try:
                finished = kube_utils.check_job_status(
                    batch_api=batch_api,
                    core_api=core_api,
                    namespace=namespace,
                    job_name=job_name,
                    fail_on_container_waiting_reasons=settings.fail_on_container_waiting_reasons,
                    stream_logs=pipeline_settings.stream_step_logs,
                    backoff_interval=settings.job_monitoring_interval,
                )
                if finished:
                    return NodeStatus.COMPLETED
                else:
                    return NodeStatus.RUNNING
            except Exception:
                reason = "Unknown"
                try:
                    pods = core_api.list_namespaced_pod(
                        label_selector=f"job-name={job_name}",
                        namespace=namespace,
                    ).items
                    # Sort pods by creation timestamp, oldest first
                    pods.sort(
                        key=lambda pod: pod.metadata.creation_timestamp,
                    )
                    if pods:
                        if (
                            termination_reason
                            := kube_utils.get_container_termination_reason(
                                pods[-1], "main"
                            )
                        ):
                            exit_code, reason = termination_reason
                            if exit_code != 0:
                                reason = f"{reason} (exit_code={exit_code})"
                except Exception:
                    pass
                logger.error(
                    f"Job for step `{step_name}` failed. Reason: {reason}"
                )

                raise

        def finalize_run(node_states: Dict[str, NodeStatus]) -> None:
            """Finalize the run.

            Args:
                node_states: The states of the nodes.
            """
            try:
                # Some steps may have failed because the pods could not be created.
                # We need to check for this and mark the step run as failed if so.
                pipeline_failed = False
                failed_step_names = [
                    step_name
                    for step_name, node_state in node_states.items()
                    if node_state == NodeStatus.FAILED
                ]
                step_runs = fetch_step_runs_by_names(
                    step_run_names=failed_step_names, pipeline_run=pipeline_run
                )

                for step_name, node_state in node_states.items():
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

        def should_interrupt_execution() -> bool:
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

                # If the run is STOPPING or STOPPED, we should stop the execution
                if run.status in [
                    ExecutionStatus.STOPPING,
                    ExecutionStatus.STOPPED,
                ]:
                    logger.info(
                        f"Pipeline run is in {run.status} state, stopping execution"
                    )
                    return True

                return False

            except Exception as e:
                # If we can't check the status, assume we should continue
                logger.warning(
                    f"Failed to check pipeline cancellation status: {e}"
                )
                return True

        def state_update_callback(nodes: List[Node]) -> None:
            """Update the state of the nodes.

            Args:
                nodes: The nodes.
            """
            state = OrchestratorPodState(
                run_id=pipeline_run.id,
                orchestrator_run_id=orchestrator_run_id,
                nodes=nodes,
            )
            store_state(state, core_api, namespace, config_map_name)

        try:
            nodes_statuses = DagRunner(
                nodes=nodes,
                startup_function=start_step_job,
                monitoring_function=check_job_status,
                monitoring_interval=1,
                max_parallelism=pipeline_settings.max_parallelism,
                # startup_interval=orchestrator.config.parallel_step_startup_waiting_period,
                startup_interval=0.5,
                interrupt_function=should_interrupt_execution,
                state_update_callback=state_update_callback,
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
                kube_utils.delete_config_map(
                    core_api=core_api,
                    namespace=namespace,
                    name=config_map_name,
                )
            except ApiException as e:
                logger.error(
                    f"Error cleaning up config map {config_map_name}: {e}"
                )

        finalize_run(nodes_statuses)


if __name__ == "__main__":
    main()
