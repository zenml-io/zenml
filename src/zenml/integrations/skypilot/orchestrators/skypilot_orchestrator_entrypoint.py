#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Entrypoint of the Skypilot master/orchestrator VM."""

import argparse
import socket
import time
from typing import Dict, cast

import sky

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import ExecutionStatus
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorSettings,
)
from zenml.integrations.skypilot.orchestrators.skypilot_base_vm_orchestrator import (
    ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID,
    SkypilotBaseOrchestrator,
)
from zenml.integrations.skypilot.utils import (
    create_docker_run_command,
    prepare_docker_setup,
    prepare_launch_kwargs,
    prepare_resources_kwargs,
    prepare_task_kwargs,
    sanitize_cluster_name,
    sky_job_get,
)
from zenml.logger import get_logger
from zenml.orchestrators.dag_runner import NodeStatus, ThreadedDagRunner
from zenml.orchestrators.publish_utils import (
    publish_failed_pipeline_run,
)
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
    """Entrypoint of the Skypilot master/orchestrator VM.

    This is the entrypoint of the Skypilot master/orchestrator VM. It is
    responsible for provisioning the VM and running the pipeline steps in
    separate VMs.

    The VM is provisioned using the `sky` library. The pipeline steps are run
    using the `sky` library as well.

    Raises:
        TypeError: If the active stack's orchestrator is not an instance of
            SkypilotBaseOrchestrator.
        ValueError: If the active stack's container registry is None.
        Exception: If the orchestration or one of the steps fails.
    """
    # Log to the container's stdout so it can be streamed by the client.
    logger.info("Skypilot orchestrator VM started.")

    # Parse / extract args.
    args = parse_args()
    orchestrator_run_id = socket.gethostname()

    run = None

    try:
        deployment = Client().get_deployment(args.deployment_id)

        pipeline_dag = {
            step_name: step.spec.upstream_steps
            for step_name, step in deployment.step_configurations.items()
        }
        step_command = StepEntrypointConfiguration.get_entrypoint_command()
        entrypoint_str = " ".join(step_command)

        active_stack = Client().active_stack

        orchestrator = active_stack.orchestrator
        if not isinstance(orchestrator, SkypilotBaseOrchestrator):
            raise TypeError(
                "The active stack's orchestrator is not an instance of SkypilotBaseOrchestrator."
            )

        # Set up credentials
        orchestrator.setup_credentials()

        # Set the service connector AWS profile ENV variable
        orchestrator.prepare_environment_variable(set=True)

        # get active container registry
        container_registry = active_stack.container_registry
        if container_registry is None:
            raise ValueError("Container registry cannot be None.")

        # Prepare Docker setup
        setup, task_envs = prepare_docker_setup(
            container_registry_uri=container_registry.config.uri,
            credentials=container_registry.credentials,
            use_sudo=False,  # Entrypoint doesn't use sudo
        )

        unique_resource_configs: Dict[str, str] = {}
        for step_name, step in deployment.step_configurations.items():
            settings = cast(
                SkypilotBaseOrchestratorSettings,
                orchestrator.get_settings(step),
            )
            # Handle both str and Dict[str, int] types for accelerators
            if isinstance(settings.accelerators, dict):
                accelerators_hashable = frozenset(
                    settings.accelerators.items()
                )
            elif isinstance(settings.accelerators, str):
                accelerators_hashable = frozenset({(settings.accelerators, 1)})
            else:
                accelerators_hashable = None
            resource_config = (
                settings.instance_type,
                settings.cpus,
                settings.memory,
                settings.disk_size,  # Assuming disk_size is part of the settings
                settings.disk_tier,  # Assuming disk_tier is part of the settings
                settings.use_spot,
                settings.job_recovery,
                settings.region,
                settings.zone,
                accelerators_hashable,
            )
            cluster_name_parts = [
                sanitize_cluster_name(str(part))
                for part in resource_config
                if part is not None
            ]
            cluster_name = f"cluster-{orchestrator_run_id}" + "-".join(
                cluster_name_parts
            )
            unique_resource_configs[step_name] = cluster_name

        run = Client().list_pipeline_runs(
            sort_by="asc:created",
            size=1,
            deployment_id=args.deployment_id,
            status=ExecutionStatus.INITIALIZING,
        )[0]

        logger.info("Fetching pipeline run: %s", run.id)

        def run_step_on_skypilot_vm(step_name: str) -> None:
            """Run a pipeline step in a separate Skypilot VM.

            Args:
                step_name: Name of the step.

            Raises:
                Exception: If the step execution fails.
            """
            logger.info(f"Running step `{step_name}` on a VM...")
            try:
                cluster_name = unique_resource_configs[step_name]

                image = SkypilotBaseOrchestrator.get_image(
                    deployment=deployment, step_name=step_name
                )

                step_args = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, deployment_id=deployment.id
                    )
                )
                arguments_str = " ".join(step_args)

                step = deployment.step_configurations[step_name]
                settings = cast(
                    SkypilotBaseOrchestratorSettings,
                    orchestrator.get_settings(step),
                )
                env = get_config_environment_vars()
                env[ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID] = (
                    orchestrator_run_id
                )

                # Create the Docker run command
                run_command = create_docker_run_command(
                    image=image,
                    entrypoint_str=entrypoint_str,
                    arguments_str=arguments_str,
                    environment=env,
                    docker_run_args=settings.docker_run_args,
                    use_sudo=False,  # Entrypoint doesn't use sudo
                )

                task_name = f"{deployment.id}-{step_name}-{time.time()}"

                # Create task kwargs
                task_kwargs = prepare_task_kwargs(
                    settings=settings,
                    run_command=run_command,
                    setup=setup,
                    task_envs=task_envs,
                    task_name=task_name,
                )

                task = sky.Task(**task_kwargs)

                # Set resources
                resources_kwargs = prepare_resources_kwargs(
                    cloud=orchestrator.cloud,
                    settings=settings,
                    default_instance_type=orchestrator.DEFAULT_INSTANCE_TYPE,
                )

                task = task.set_resources(sky.Resources(**resources_kwargs))

                # Prepare launch parameters
                launch_kwargs = prepare_launch_kwargs(
                    settings=settings,
                )

                # sky.launch now returns a request ID (async). Capture it so we can
                # optionally stream logs and block until completion when desired.
                launch_request_id = sky.launch(
                    task,
                    cluster_name,
                    **launch_kwargs,
                )
                sky_job_get(launch_request_id, True, cluster_name)

                # Pop the resource configuration for this step
                unique_resource_configs.pop(step_name)

                if cluster_name in unique_resource_configs.values():
                    # If there are more steps using this configuration, skip deprovisioning the cluster
                    logger.info(
                        f"Resource configuration for cluster '{cluster_name}' "
                        "is used by subsequent steps. Skipping the deprovisioning of "
                        "the cluster."
                    )
                else:
                    # If there are no more steps using this configuration, down the cluster
                    logger.info(
                        f"Resource configuration for cluster '{cluster_name}' "
                        "is not used by subsequent steps. deprovisioning the cluster."
                    )
                    down_request_id = sky.down(cluster_name)
                    # Wait for the cluster to be terminated
                    sky.stream_and_get(down_request_id)

                logger.info(
                    f"Running step `{step_name}` on a VM is completed."
                )

            except Exception as e:
                logger.error(f"Failed while launching step `{step_name}`: {e}")
                raise

        dag_runner = ThreadedDagRunner(
            dag=pipeline_dag, run_fn=run_step_on_skypilot_vm
        )
        dag_runner.run()

        failed_nodes = []
        for node in dag_runner.nodes:
            if dag_runner.node_states[node] == NodeStatus.FAILED:
                failed_nodes.append(node)

        if failed_nodes:
            raise Exception(f"One or more steps failed: {failed_nodes}")

    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")

        # Try to mark the pipeline run as failed
        if run:
            publish_failed_pipeline_run(run.id)
            logger.info("Marked pipeline run as failed in ZenML.")
        raise


if __name__ == "__main__":
    main()
