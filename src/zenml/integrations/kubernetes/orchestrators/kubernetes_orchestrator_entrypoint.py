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
import logging
import sys

from zenml.integrations.kubernetes.orchestrators import tfx_kube_utils
from zenml.integrations.kubernetes.orchestrators.utils import (
    build_base_pod_manifest,
    update_pod_manifest,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--pipeline_name", type=str, required=True)
    parser.add_argument("--image_name", type=str, required=True)
    parser.add_argument("--kubernetes_namespace", type=str, required=True)
    parser.add_argument("--pipeline_config", type=json.loads, required=True)
    return parser.parse_args()


def main():
    # Log to the container's stdout so it can be streamed by the client.
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)

    args = parse_args()
    core_api = tfx_kube_utils.make_core_v1_api()

    logging.info("Starting orchestration...")

    pipeline_config = args.pipeline_config
    step_command = pipeline_config["step_command"]
    sorted_steps = pipeline_config["sorted_steps"]
    fixed_step_args = pipeline_config["fixed_step_args"]

    base_pod_manifest = build_base_pod_manifest(
        run_name=args.run_name,
        pipeline_name=args.pipeline_name,
        image_name=args.image_name,
    )

    for step_name in sorted_steps:
        # Define k8s pod name.
        pod_name = f"{args.run_name}-{step_name}"
        pod_name = tfx_kube_utils.sanitize_pod_name(pod_name)

        # Build list of args for this step.
        step_specific_args = pipeline_config["step_specific_args"][step_name]
        step_args = [*fixed_step_args, *step_specific_args]

        # Define k8s pod manifest.
        pod_manifest = update_pod_manifest(
            base_pod_manifest=base_pod_manifest,
            pod_name=pod_name,
            command=step_command,
            args=step_args,
        )
        logging.info(f"Running step {step_name}...")

        # Create and run pod.
        core_api.create_namespaced_pod(
            namespace=args.kubernetes_namespace,
            body=pod_manifest,
        )
        logging.info(f"Waiting for step {step_name}...")

        # Wait for pod to finish.
        tfx_kube_utils.wait_pod(
            core_api,
            pod_name,
            namespace=args.kubernetes_namespace,
            exit_condition_lambda=tfx_kube_utils.pod_is_done,
            condition_description="done state",
        )
        logging.info(f"Step {step_name} finished.")

    logging.info("Orchestration complete.")


if __name__ == "__main__":
    main()
