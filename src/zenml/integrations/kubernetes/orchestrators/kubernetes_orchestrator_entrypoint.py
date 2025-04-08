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
import socket
import time
from typing import Any, Dict
from uuid import UUID

from kubernetes import client as k8s_client

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
    build_pod_manifest,
)
from zenml.logger import get_logger
from zenml.orchestrators import publish_utils
from zenml.orchestrators.dag_runner import NodeStatus, ThreadedDagRunner
from zenml.orchestrators.utils import get_config_environment_vars

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--kubernetes_namespace", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Kubernetes orchestrator pod started.")

    # Parse / extract args.
    args = parse_args()

    orchestrator_run_id = socket.gethostname()

    client = Client()

    deployment_config = client.get_deployment(args.deployment_id)

    pipeline_dag = {
        step_name: step.spec.upstream_steps
        for step_name, step in deployment_config.step_configurations.items()
    }
    step_command = StepEntrypointConfiguration.get_entrypoint_command()

    active_stack = client.active_stack
    mount_local_stores = active_stack.orchestrator.config.is_local

    # Get a Kubernetes client from the active Kubernetes orchestrator, but
    # override the `incluster` setting to `True` since we are running inside
    # the Kubernetes cluster.
    orchestrator = active_stack.orchestrator
    assert isinstance(orchestrator, KubernetesOrchestrator)
    kube_client = orchestrator.get_kube_client(incluster=True)
    core_api = k8s_client.CoreV1Api(kube_client)

    env = get_config_environment_vars()
    env[ENV_ZENML_KUBERNETES_RUN_ID] = orchestrator_run_id

    def run_step_on_kubernetes(step_name: str) -> None:
        """Run a pipeline step in a separate Kubernetes pod.

        Args:
            step_name: Name of the step.

        Raises:
            Exception: If the pod fails to start.
            TimeoutError: If the pod is still in a pending state after the
                maximum wait time has elapsed.
        """
        # Define Kubernetes pod name.
        pod_name = f"{orchestrator_run_id}-{step_name}"
        pod_name = kube_utils.sanitize_pod_name(
            pod_name, namespace=args.kubernetes_namespace
        )

        image = KubernetesOrchestrator.get_image(
            deployment=deployment_config, step_name=step_name
        )
        step_args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name, deployment_id=deployment_config.id
        )

        step_config = deployment_config.step_configurations[step_name].config

        kubernetes_settings = step_config.settings.get(
            "orchestrator.kubernetes", None
        )

        orchestrator_settings = {}
        if kubernetes_settings is not None:
            orchestrator_settings = kubernetes_settings.model_dump()

        settings = KubernetesOrchestratorSettings.model_validate(
            orchestrator_settings
        )

        # We set some default minimum memory resource requests for the step pod
        # here if the user has not specified any, because the step pod takes up
        # some memory resources itself and, if not specified, the pod will be
        # scheduled on any node regardless of available memory and risk
        # negatively impacting or even crashing the node due to memory pressure.
        pod_settings = KubernetesOrchestrator.apply_default_resource_requests(
            memory="400Mi",
            pod_settings=settings.pod_settings,
        )

        if orchestrator.config.pass_zenml_token_as_secret:
            env.pop("ZENML_STORE_API_TOKEN", None)
            secret_name = orchestrator.get_token_secret_name(
                deployment_config.id
            )
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

        # Define Kubernetes pod manifest.
        pod_manifest = build_pod_manifest(
            pod_name=pod_name,
            run_name=args.run_name,
            pipeline_name=deployment_config.pipeline_configuration.name,
            image_name=image,
            command=step_command,
            args=step_args,
            env=env,
            privileged=settings.privileged,
            pod_settings=pod_settings,
            service_account_name=settings.step_pod_service_account_name
            or settings.service_account_name,
            mount_local_stores=mount_local_stores,
        )

        retries = 0
        max_retries = settings.pod_failure_max_retries
        delay: float = settings.pod_failure_retry_delay
        backoff = settings.pod_failure_backoff

        while retries < max_retries:
            try:
                # Create and run pod.
                core_api.create_namespaced_pod(
                    namespace=args.kubernetes_namespace,
                    body=pod_manifest,
                )
                break
            except Exception as e:
                retries += 1
                if retries < max_retries:
                    logger.debug(
                        f"Pod for step `{step_name}` failed to start: {e}"
                    )
                    logger.error(
                        f"Failed to create pod for step `{step_name}`. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                    delay *= backoff
                else:
                    logger.error(
                        f"Failed to create pod for step `{step_name}` after "
                        f"{max_retries} retries. Exiting."
                    )
                    raise

        # Wait for pod to start
        max_wait = settings.pod_startup_timeout
        total_wait: float = 0
        delay = settings.pod_failure_retry_delay
        while True:
            pod = kube_utils.get_pod(
                core_api, pod_name, args.kubernetes_namespace
            )
            if not pod or kube_utils.pod_is_not_pending(pod):
                break
            if total_wait >= max_wait:
                # Have to delete the pending pod so it doesn't start running
                # later on.
                try:
                    core_api.delete_namespaced_pod(
                        name=pod_name,
                        namespace=args.kubernetes_namespace,
                    )
                except Exception:
                    pass
                raise TimeoutError(
                    f"Pod for step `{step_name}` is still in a pending state "
                    f"after {total_wait} seconds. Exiting."
                )

            if total_wait + delay > max_wait:
                delay = max_wait - total_wait
            total_wait += delay
            time.sleep(delay)
            delay *= backoff

        # Wait for pod to finish.
        logger.info(f"Waiting for pod of step `{step_name}` to finish...")
        try:
            kube_utils.wait_pod(
                kube_client_fn=lambda: orchestrator.get_kube_client(
                    incluster=True
                ),
                pod_name=pod_name,
                namespace=args.kubernetes_namespace,
                exit_condition_lambda=kube_utils.pod_is_done,
                stream_logs=True,
            )

            logger.info(f"Pod for step `{step_name}` completed.")
        except Exception:
            logger.error(f"Pod for step `{step_name}` failed.")

            raise

    def finalize_run(node_states: Dict[str, NodeStatus]) -> None:
        """Finalize the run.

        Args:
            node_states: The states of the nodes.
        """
        try:
            # Some steps may have failed because the pods could not be created.
            # We need to check for this and mark the step run as failed if so.

            # Fetch the pipeline run using any means possible.
            list_args: Dict[str, Any] = {}
            if args.run_id:
                # For a run triggered outside of a schedule, we can use the
                # placeholder run ID to find the pipeline run.
                list_args = dict(id=UUID(args.run_id))
            else:
                # For a run triggered by a schedule, we can only use the
                # orchestrator run ID to find the pipeline run.
                list_args = dict(orchestrator_run_id=orchestrator_run_id)

            pipeline_runs = client.list_pipeline_runs(
                hydrate=True,
                project=deployment_config.project.id,
                deployment_id=deployment_config.id,
                **list_args,
            )
            if not len(pipeline_runs):
                # No pipeline run found, so we can't mark any step runs as failed.
                return

            pipeline_run = pipeline_runs[0]
            pipeline_failed = False

            for step_name, node_state in node_states.items():
                if node_state != NodeStatus.FAILED:
                    continue

                pipeline_failed = True

                # If steps failed for any reason, we need to mark the step run as
                # failed, if it exists and it wasn't already in a final state.

                step_run = pipeline_run.steps.get(step_name)

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

    parallel_node_startup_waiting_period = (
        orchestrator.config.parallel_step_startup_waiting_period or 0.0
    )
    try:
        ThreadedDagRunner(
            dag=pipeline_dag,
            run_fn=run_step_on_kubernetes,
            finalize_fn=finalize_run,
            parallel_node_startup_waiting_period=parallel_node_startup_waiting_period,
        ).run()
        logger.info("Orchestration pod completed.")
    finally:
        if (
            orchestrator.config.pass_zenml_token_as_secret
            and deployment_config.schedule is None
        ):
            secret_name = orchestrator.get_token_secret_name(
                deployment_config.id
            )
            try:
                kube_utils.delete_secret(
                    core_api=core_api,
                    namespace=args.kubernetes_namespace,
                    secret_name=secret_name,
                )
            except k8s_client.rest.ApiException as e:
                logger.error(f"Error cleaning up secret {secret_name}: {e}")


if __name__ == "__main__":
    main()
