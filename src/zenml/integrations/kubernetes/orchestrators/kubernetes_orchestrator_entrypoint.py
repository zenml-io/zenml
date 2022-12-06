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

from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.constants import DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.kubernetes_orchestrator import (
    ENV_ZENML_KUBERNETES_RUN_ID,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_pod_manifest,
)
from zenml.logger import get_logger
from zenml.orchestrators.dag_runner import ThreadedDagRunner
from zenml.utils import yaml_utils

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--image_name", type=str, required=True)
    parser.add_argument("--kubernetes_namespace", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Kubernetes orchestrator pod started.")

    # Parse / extract args.
    args = parse_args()

    # Get Kubernetes Core API for running kubectl commands later.
    kube_utils.load_kube_config()
    core_api = k8s_client.CoreV1Api()

    orchestrator_run_id = socket.gethostname()

    config_dict = yaml_utils.read_yaml(DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE)
    deployment_config = PipelineDeployment.parse_obj(config_dict)

    pipeline_dag = {}
    step_name_to_pipeline_step_name = {}
    for name_in_pipeline, step in deployment_config.steps.items():
        step_name_to_pipeline_step_name[step.config.name] = name_in_pipeline
        pipeline_dag[step.config.name] = step.spec.upstream_steps

    step_command = StepEntrypointConfiguration.get_entrypoint_command()

    def run_step_on_kubernetes(step_name: str) -> None:
        """Run a pipeline step in a separate Kubernetes pod.

        Args:
            step_name: Name of the step.
        """
        # Define Kubernetes pod name.
        pod_name = f"{orchestrator_run_id}-{step_name}"
        pod_name = kube_utils.sanitize_pod_name(pod_name)

        pipeline_step_name = step_name_to_pipeline_step_name[step_name]
        step_args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=pipeline_step_name
        )

        step_config = deployment_config.steps[pipeline_step_name].config
        settings = KubernetesOrchestratorSettings.parse_obj(
            step_config.settings.get("orchestrator.kubernetes", {})
        )

        # Define Kubernetes pod manifest.
        pod_manifest = build_pod_manifest(
            pod_name=pod_name,
            run_name=args.run_name,
            pipeline_name=deployment_config.pipeline.name,
            image_name=args.image_name,
            command=step_command,
            args=step_args,
            env={ENV_ZENML_KUBERNETES_RUN_ID: orchestrator_run_id},
            settings=settings,
        )

        # Create and run pod.
        core_api.create_namespaced_pod(
            namespace=args.kubernetes_namespace,
            body=pod_manifest,
        )

        # Wait for pod to finish.
        logger.info(f"Waiting for pod of step `{step_name}` to start...")
        kube_utils.wait_pod(
            core_api=core_api,
            pod_name=pod_name,
            namespace=args.kubernetes_namespace,
            exit_condition_lambda=kube_utils.pod_is_done,
            stream_logs=True,
        )
        logger.info(f"Pod of step `{step_name}` completed.")

    ThreadedDagRunner(dag=pipeline_dag, run_fn=run_step_on_kubernetes).run()

    logger.info("Orchestration pod completed.")


if __name__ == "__main__":
    main()
