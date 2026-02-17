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
import hashlib
import json
import shlex
import socket
import time
from typing import Any, Dict, Optional, cast

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
from zenml.utils import env_utils

logger = get_logger(__name__)

_MAX_CLUSTER_NAME_LENGTH = 63
_CLUSTER_HASH_LENGTH = 16


def parse_args() -> argparse.Namespace:
    """Parse entrypoint arguments.

    Returns:
        Parsed args.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, required=True)
    parser.add_argument("--snapshot_id", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=False)
    return parser.parse_args()


def _normalize_for_json(value: Any) -> Any:
    """Converts nested values into deterministic JSON-serializable objects.

    Args:
        value: Value to normalize.

    Returns:
        A normalized representation safe for deterministic JSON serialization.
    """
    if isinstance(value, dict):
        return {
            str(key): _normalize_for_json(item)
            for key, item in sorted(
                value.items(), key=lambda entry: str(entry[0])
            )
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, set):
        normalized_items = [_normalize_for_json(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    return value


def _resource_config_digest(
    settings: SkypilotBaseOrchestratorSettings,
    default_instance_type: Optional[str],
) -> str:
    """Builds a stable digest for resource-affecting settings.

    Args:
        settings: Step-specific SkyPilot settings.
        default_instance_type: Default instance type of the orchestrator.

    Returns:
        A short deterministic hash for the resource configuration.
    """
    resource_config = {
        "instance_type": settings.instance_type or default_instance_type,
        "cpus": settings.cpus,
        "memory": settings.memory,
        "accelerators": settings.accelerators,
        "accelerator_args": settings.accelerator_args,
        "use_spot": settings.use_spot,
        "job_recovery": settings.job_recovery,
        "region": settings.region,
        "zone": settings.zone,
        "image_id": settings.image_id,
        "disk_size": settings.disk_size,
        "disk_tier": settings.disk_tier,
        "network_tier": settings.network_tier,
        "infra": settings.infra,
        "num_nodes": settings.num_nodes,
        "ports": settings.ports,
        "labels": settings.labels,
        "any_of": settings.any_of,
        "ordered": settings.ordered,
        "resources_settings": settings.resources_settings,
    }
    serialized = json.dumps(
        _normalize_for_json(resource_config),
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[
        :_CLUSTER_HASH_LENGTH
    ]


def _generate_cluster_name(
    orchestrator_run_id: str,
    settings: SkypilotBaseOrchestratorSettings,
    default_instance_type: Optional[str],
) -> str:
    """Generates a deterministic cluster name for a resource configuration.

    Args:
        orchestrator_run_id: Orchestrator run identifier.
        settings: Step-specific SkyPilot settings.
        default_instance_type: Default instance type of the orchestrator.

    Returns:
        Deterministic cluster name within the configured max length.
    """
    run_part = sanitize_cluster_name(orchestrator_run_id) or "run"
    digest = _resource_config_digest(settings, default_instance_type)

    max_run_part_len = (
        _MAX_CLUSTER_NAME_LENGTH - len("cluster--") - _CLUSTER_HASH_LENGTH
    )
    if max_run_part_len < 1:
        raise RuntimeError("Invalid SkyPilot cluster naming constraints.")
    run_part = run_part[:max_run_part_len]

    return sanitize_cluster_name(f"cluster-{run_part}-{digest}")


def _resolve_pipeline_run(
    client: Client,
    run_name: str,
    snapshot_id: str,
    run_id: Optional[str],
) -> Any:
    """Resolves the pipeline run for the orchestrator entrypoint.

    Args:
        client: Active ZenML client.
        run_name: Name passed to the entrypoint.
        snapshot_id: Snapshot ID of the run.
        run_id: Optional concrete run ID.

    Returns:
        The resolved pipeline run object.

    Raises:
        RuntimeError: If no matching run can be found.
    """
    if run_id:
        try:
            return client.get_pipeline_run(run_id)
        except Exception as e:
            raise RuntimeError(
                f"Unable to fetch pipeline run `{run_id}` passed via --run_id."
            ) from e

    runs = client.list_pipeline_runs(
        sort_by="desc:created",
        size=1,
        snapshot_id=snapshot_id,
        status=ExecutionStatus.INITIALIZING,
    )

    if getattr(runs, "total", None) == 0:
        raise RuntimeError(
            "Unable to resolve a pipeline run for snapshot "
            f"`{snapshot_id}` (run name `{run_name}`). Pass --run_id to "
            "the entrypoint to avoid race conditions."
        )

    try:
        return runs[0]
    except IndexError as e:
        raise RuntimeError(
            "Unable to resolve a pipeline run from the initializing run list. "
            "Pass --run_id to the entrypoint to avoid race conditions."
        ) from e


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
    logger.info("Skypilot orchestrator VM started.")

    args = parse_args()
    orchestrator_run_id = socket.gethostname()

    run = None

    try:
        client = Client()
        snapshot = client.get_snapshot(args.snapshot_id)

        pipeline_dag = {
            step_name: step.spec.upstream_steps
            for step_name, step in snapshot.step_configurations.items()
        }
        step_command = StepEntrypointConfiguration.get_entrypoint_command()
        entrypoint_str = " ".join(shlex.quote(token) for token in step_command)

        active_stack = client.active_stack

        orchestrator = active_stack.orchestrator
        if not isinstance(orchestrator, SkypilotBaseOrchestrator):
            raise TypeError(
                "The active stack's orchestrator is not an instance of SkypilotBaseOrchestrator."
            )

        orchestrator.setup_credentials()

        orchestrator.prepare_environment_variable(set=True)

        container_registry = active_stack.container_registry
        if container_registry is None:
            raise ValueError("Container registry cannot be None.")

        setup, task_envs = prepare_docker_setup(
            container_registry_uri=container_registry.config.uri,
            credentials=container_registry.credentials,
            use_sudo=False,  # Entrypoint doesn't use sudo
        )

        unique_resource_configs: Dict[str, str] = {}
        for step_name, step in snapshot.step_configurations.items():
            settings = cast(
                SkypilotBaseOrchestratorSettings,
                orchestrator.get_settings(step),
            )
            cluster_name = _generate_cluster_name(
                orchestrator_run_id=orchestrator_run_id,
                settings=settings,
                default_instance_type=orchestrator.DEFAULT_INSTANCE_TYPE,
            )
            unique_resource_configs[step_name] = cluster_name

        run = _resolve_pipeline_run(
            client=client,
            run_name=args.run_name,
            snapshot_id=args.snapshot_id,
            run_id=args.run_id,
        )

        logger.info("Fetching pipeline run: %s", run.id)

        shared_env, secrets = get_config_environment_vars()
        shared_env[ENV_ZENML_SKYPILOT_ORCHESTRATOR_RUN_ID] = (
            orchestrator_run_id
        )

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
                    snapshot=snapshot, step_name=step_name
                )

                step_args = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, snapshot_id=snapshot.id
                    )
                )
                arguments_str = " ".join(
                    shlex.quote(token) for token in step_args
                )

                step = snapshot.step_configurations[step_name]
                settings = cast(
                    SkypilotBaseOrchestratorSettings,
                    orchestrator.get_settings(step),
                )
                step_env = shared_env.copy()
                step_env.update(
                    env_utils.get_runtime_environment(
                        config=step.config, stack=active_stack
                    )
                )
                step_env.update(secrets)

                run_command = create_docker_run_command(
                    image=image,
                    entrypoint_str=entrypoint_str,
                    arguments_str=arguments_str,
                    environment=step_env,
                    docker_run_args=settings.docker_run_args,
                    use_sudo=False,  # Entrypoint doesn't use sudo
                )

                task_name = f"{snapshot.id}-{step_name}-{time.time()}"

                step_task_envs = step_env.copy()
                step_task_envs.update(task_envs)
                task_kwargs = prepare_task_kwargs(
                    settings=settings,
                    run_command=run_command,
                    setup=setup,
                    task_envs=step_task_envs,
                    task_name=task_name,
                )

                task = sky.Task(**task_kwargs)

                resources_kwargs = prepare_resources_kwargs(
                    cloud=orchestrator.cloud,
                    settings=settings,
                    default_instance_type=orchestrator.DEFAULT_INSTANCE_TYPE,
                )

                task = task.set_resources(sky.Resources(**resources_kwargs))

                launch_kwargs = prepare_launch_kwargs(settings=settings)

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
                    logger.info(
                        f"Resource configuration for cluster '{cluster_name}' "
                        "is used by subsequent steps. Skipping the deprovisioning of "
                        "the cluster."
                    )
                else:
                    logger.info(
                        f"Resource configuration for cluster '{cluster_name}' "
                        "is not used by subsequent steps. deprovisioning the cluster."
                    )
                    try:
                        down_request_id = sky.down(cluster_name)
                        sky.stream_and_get(down_request_id)
                    except Exception as cleanup_error:
                        logger.error(
                            "Failed to deprovision cluster "
                            f"'{cluster_name}': {cleanup_error}. "
                            f"Resources may still be running. Run `sky down "
                            f"{cluster_name}` manually to clean up."
                        )

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
