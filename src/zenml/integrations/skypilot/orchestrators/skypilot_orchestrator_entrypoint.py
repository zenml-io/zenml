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
"""Entrypoint of the Skypilot master/orchestrator pod."""

import argparse
import socket

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotOrchestratorSettings,
)
from zenml.integrations.skypilot.orchestrators import kube_utils
from zenml.integrations.skypilot.orchestrators.skypilot_base_vm_orchestrator import (
    SkypilotBaseOrchestrator,
    ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID
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
    return parser.parse_args()


def main() -> None:
    """Entrypoint of the k8s master/orchestrator pod."""
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Skypilot orchestrator pod started.")

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

    # Get a Skypilot client from the active Skypilot orchestrator, but
    # override the `incluster` setting to `True` since we are running inside
    # the Skypilot cluster.
    orchestrator = active_stack.orchestrator
    assert isinstance(orchestrator, SkypilotBaseOrchestrator)

    def run_step_on_skypilot(step_name: str) -> None:
        """Run a pipeline step in a separate Skypilot pod.

        Args:
            step_name: Name of the step.
        """
        # Define Skypilot pod name.
        pod_name = f"{orchestrator_run_id}-{step_name}"
        pod_name = kube_utils.sanitize_pod_name(pod_name)

        image = SkypilotBaseOrchestrator.get_image(
            deployment=deployment_config, step_name=step_name
        )
        step_args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name, deployment_id=deployment_config.id
        )

        step_config = deployment_config.step_configurations[step_name].config
        settings = SkypilotOrchestratorSettings.parse_obj(
            step_config.settings.get("orchestrator.skypilot", {})
        )

        env = get_config_environment_vars()
        env[ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID] = orchestrator_run_id

        # Define Skypilot pod manifest.
        # pod_manifest = build_pod_manifest(
        #     pod_name=pod_name,
        #     run_name=args.run_name,
        #     pipeline_name=deployment_config.pipeline_configuration.name,
        #     image_name=image,
        #     command=step_command,
        #     args=step_args,
        #     env=env,
        #     settings=settings,
        #     service_account_name=settings.service_account_name,
        #     mount_local_stores=mount_local_stores,
        # )

        # Create and run pod.
        # core_api.create_namespaced_pod(
        #     namespace=args.skypilot_namespace,
        #     body=pod_manifest,
        # )

        # Wait for pod to finish.
        logger.info(f"Waiting for pod of step `{step_name}` to start...")
        # kube_utils.wait_pod(
        #     core_api=core_api,
        #     pod_name=pod_name,
        #     namespace=args.skypilot_namespace,
        #     exit_condition_lambda=kube_utils.pod_is_done,
        #     stream_logs=True,
        # )
        logger.info(f"Pod of step `{step_name}` completed.")

    ThreadedDagRunner(dag=pipeline_dag, run_fn=run_step_on_skypilot).run()

    logger.info("Orchestration pod completed.")


if __name__ == "__main__":
    main()
