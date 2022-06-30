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
import json
import socket
from typing import List

from kubernetes import client as k8s_client

from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.dag_runner import (
    ThreadedDagRunner,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_pod_manifest,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--pipeline_name", type=str, required=True)
    parser.add_argument("--image_name", type=str, required=True)
    parser.add_argument("--kubernetes_namespace", type=str, required=True)
    parser.add_argument("--pipeline_config", type=json.loads, required=True)
    return parser.parse_args()


def patch_run_name_for_cron_scheduling(
    run_name: str, fixed_step_args: List[str]
) -> str:
    """Adjust run name according to the Kubernetes orchestrator pod name.

    This is required for scheduling via CRON jobs, since each job would
    otherwise have the same run name, which zenml does not support.

    Args:
        run_name: Initial run name.
        fixed_step_args: Fixed entrypoint args for the step pods.
            We also need to patch the run name in there.

    Returns:
        New unique run name.
    """
    # Get name of the orchestrator pod.
    host_name = socket.gethostname()

    # If we are not running as CRON job, we don't need to do anything.
    if host_name == kube_utils.sanitize_pod_name(run_name):
        return run_name

    # Otherwise, define new run_name.
    job_id = host_name.split("-")[-1]
    run_name = f"{run_name}-{job_id}"

    # Then also adjust run_name in fixed_step_args.
    for i, arg in enumerate(fixed_step_args):
        if arg == "--run_name":
            fixed_step_args[i + 1] = run_name

    return run_name


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Kubernetes orchestrator pod started.")

    # Parse / extract args.
    args = parse_args()
    pipeline_config = args.pipeline_config
    step_command = pipeline_config["step_command"]
    fixed_step_args = pipeline_config["fixed_step_args"]
    step_specific_args = pipeline_config["step_specific_args"]
    pipeline_dag = pipeline_config["pipeline_dag"]

    # Get Kubernetes Core API for running kubectl commands later.
    kube_utils.load_kube_config()
    core_api = k8s_client.CoreV1Api()

    # Patch run name (only needed for CRON scheduling)
    run_name = patch_run_name_for_cron_scheduling(
        args.run_name, fixed_step_args
    )

    def run_step_on_kubernetes(step_name: str) -> None:
        """Run a pipeline step in a separate Kubernetes pod.

        Args:
            step_name: Name of the step.
        """
        # Define Kubernetes pod name.
        pod_name = f"{run_name}-{step_name}"
        pod_name = kube_utils.sanitize_pod_name(pod_name)

        # Build list of args for this step.
        step_args = [*fixed_step_args, *step_specific_args[step_name]]

        # Define Kubernetes pod manifest.
        pod_manifest = build_pod_manifest(
            pod_name=pod_name,
            run_name=run_name,
            pipeline_name=args.pipeline_name,
            image_name=args.image_name,
            command=step_command,
            args=step_args,
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
