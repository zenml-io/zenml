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

from kubernetes import client as k8s_client

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator import (
    ENV_ZENML_KUBERNETES_RUN_ID,
    KubernetesOrchestrator,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_pod_manifest,
)
from zenml.logger import get_logger
from zenml.orchestrators.dag_runner import ThreadedDagRunner
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
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Kubernetes orchestrator pod started.")

    # Parse / extract args.
    args = parse_args()

    orchestrator_run_id = socket.gethostname()

    deployment_config = Client().get_deployment(args.deployment_id)

    pipeline_dag = {
        step_name: step.spec.upstream_steps
        for step_name, step in deployment_config.step_configurations.items()
    }
    step_command = StepEntrypointConfiguration.get_entrypoint_command()

    active_stack = Client().active_stack
    mount_local_stores = active_stack.orchestrator.config.is_local

    # Get a Kubernetes client from the active Kubernetes orchestrator, but
    # override the `incluster` setting to `True` since we are running inside
    # the Kubernetes cluster.
    orchestrator = active_stack.orchestrator
    assert isinstance(orchestrator, KubernetesOrchestrator)
    kube_client = orchestrator.get_kube_client(incluster=True)
    core_api = k8s_client.CoreV1Api(kube_client)

    def run_step_on_kubernetes(step_name: str) -> None:
        """Run a pipeline step in a separate Kubernetes pod.

        Args:
            step_name: Name of the step.
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

        env = get_config_environment_vars()
        env[ENV_ZENML_KUBERNETES_RUN_ID] = orchestrator_run_id

        # We set some default minimum memory resource requests for the step pod
        # here if the user has not specified any, because the step pod takes up
        # some memory resources itself and, if not specified, the pod will be
        # scheduled on any node regardless of available memory and risk
        # negatively impacting or even crashing the node due to memory pressure.
        pod_settings = KubernetesOrchestrator.apply_default_resource_requests(
            memory="400Mi",
            pod_settings=settings.pod_settings,
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

        # Create and run pod.
        core_api.create_namespaced_pod(
            namespace=args.kubernetes_namespace,
            body=pod_manifest,
        )

        # Wait for pod to finish.
        logger.info(f"Waiting for pod of step `{step_name}` to start...")
        kube_utils.wait_pod(
            kube_client_fn=lambda: orchestrator.get_kube_client(
                incluster=True
            ),
            pod_name=pod_name,
            namespace=args.kubernetes_namespace,
            exit_condition_lambda=kube_utils.pod_is_done,
            stream_logs=True,
        )
        logger.info(f"Pod of step `{step_name}` completed.")

    parallel_node_startup_waiting_period = (
        orchestrator.config.parallel_step_startup_waiting_period or 0.0
    )
    ThreadedDagRunner(
        dag=pipeline_dag,
        run_fn=run_step_on_kubernetes,
        parallel_node_startup_waiting_period=parallel_node_startup_waiting_period,
    ).run()

    logger.info("Orchestration pod completed.")


if __name__ == "__main__":
    main()
