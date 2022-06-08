"""Entrypoint of the k8s master/orchestrator pod."""

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

import argparse
import json

from zenml.integrations.kubernetes.orchestrators import kube_utils
from zenml.integrations.kubernetes.orchestrators.dag_runner import (
    ThreadedDagRunner,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_base_pod_manifest,
    update_pod_manifest,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        argparse.Namespace: Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--pipeline_name", type=str, required=True)
    parser.add_argument("--image_name", type=str, required=True)
    parser.add_argument("--kubernetes_namespace", type=str, required=True)
    parser.add_argument("--pipeline_config", type=json.loads, required=True)
    return parser.parse_args()


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

    # Get k8s Core API for running kubectl commands later.
    core_api = kube_utils.make_core_v1_api()

    # Build base pod manifest.
    base_pod_manifest = build_base_pod_manifest(
        run_name=args.run_name,
        pipeline_name=args.pipeline_name,
        image_name=args.image_name,
    )

    def run_step_on_kubernetes(step_name: str) -> None:
        """Run a pipeline step in a separate Kubernetes pod.

        Args:
            step_name (str): Name of the step.
        """
        # Define k8s pod name.
        pod_name = f"{args.run_name}-{step_name}"
        pod_name = kube_utils.sanitize_pod_name(pod_name)

        # Build list of args for this step.
        step_args = [*fixed_step_args, *step_specific_args[step_name]]

        # Define k8s pod manifest.
        pod_manifest = update_pod_manifest(
            base_pod_manifest=base_pod_manifest,
            pod_name=pod_name,
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
            core_api,
            pod_name,
            namespace=args.kubernetes_namespace,
            exit_condition_lambda=kube_utils.pod_is_done,
            stream_logs=True,
        )
        logger.info(f"Pod of step `{step_name}` completed.")

    ThreadedDagRunner(dag=pipeline_dag, run_fn=run_step_on_kubernetes).run()

    logger.info("Orchestration pod completed.")


if __name__ == "__main__":
    main()
