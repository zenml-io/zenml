"""Utility functions for Skypilot orchestrators."""

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import sky

from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorSettings,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from sky.clouds.cloud import Cloud


def sanitize_cluster_name(name: str) -> str:
    """Sanitize the value to be used in a cluster name.

    Args:
        name: Arbitrary input cluster name.

    Returns:
        Sanitized cluster name.
    """
    name = re.sub(
        r"[^a-z0-9-]", "-", name.lower()
    )  # replaces any character that is not a lowercase letter, digit, or hyphen with a hyphen
    name = re.sub(r"^[-]+", "", name)  # trim leading hyphens
    name = re.sub(r"[-]+$", "", name)  # trim trailing hyphens
    return name


def prepare_docker_setup(
    container_registry_uri: str,
    credentials: Optional[Tuple[str, str]] = None,
    use_sudo: bool = True,
) -> Tuple[Optional[str], Dict[str, str]]:
    """Prepare Docker login setup command and environment variables.

    Args:
        container_registry_uri: URI of the container registry.
        credentials: Optional credentials (username, password) tuple.
        use_sudo: Whether to use sudo prefix in docker commands.

    Returns:
        Tuple of (setup command, environment variables)
    """
    if credentials:
        docker_username, docker_password = credentials
        sudo_prefix = "sudo " if use_sudo else ""
        setup = (
            f"{sudo_prefix}docker login --username $DOCKER_USERNAME --password "
            f"$DOCKER_PASSWORD {container_registry_uri}"
        )
        task_envs = {
            "DOCKER_USERNAME": docker_username,
            "DOCKER_PASSWORD": docker_password,
        }
    else:
        setup = None
        task_envs = {}

    return setup, task_envs


def create_docker_run_command(
    image: str,
    entrypoint_str: str,
    arguments_str: str,
    environment: Dict[str, str],
    docker_run_args: List[str],
    use_sudo: bool = True,
) -> str:
    """Create a Docker run command string.

    Args:
        image: Docker image to run.
        entrypoint_str: Entrypoint command.
        arguments_str: Command arguments.
        environment: Environment variables.
        docker_run_args: Additional Docker run arguments.
        use_sudo: Whether to use sudo prefix in docker commands.

    Returns:
        Docker run command as string.
    """
    docker_environment_str = " ".join(
        f"-e {k}={v}" for k, v in environment.items()
    )
    custom_run_args = " ".join(docker_run_args)
    if custom_run_args:
        custom_run_args += " "

    sudo_prefix = "sudo " if use_sudo else ""
    return f"{sudo_prefix}docker run --rm {custom_run_args}{docker_environment_str} {image} {entrypoint_str} {arguments_str}"


def prepare_task_kwargs(
    settings: SkypilotBaseOrchestratorSettings,
    run_command: str,
    setup: Optional[str],
    task_envs: Dict[str, str],
    task_name: str,
) -> Dict[str, Any]:
    """Prepare task keyword arguments for sky.Task.

    Args:
        settings: Skypilot orchestrator settings.
        run_command: Command to run.
        setup: Setup command.
        task_envs: Task environment variables.
        task_name: Task name.

    Returns:
        Task keyword arguments dictionary.
    """
    # Merge envs from settings with existing task_envs
    merged_envs = {}

    # First add user-provided envs
    if settings.envs:
        merged_envs.update(settings.envs)

    # Then add task_envs which take precedence
    if task_envs:
        merged_envs.update(task_envs)

    task_kwargs = {
        "run": run_command,
        "setup": setup,
        "envs": merged_envs,
        "name": settings.task_name or task_name,
        "workdir": settings.workdir,
        "file_mounts_mapping": settings.file_mounts,
        **settings.task_settings,  # Add any arbitrary task settings
    }

    # Remove None values to avoid overriding SkyPilot defaults
    return {k: v for k, v in task_kwargs.items() if v is not None}


def prepare_resources_kwargs(
    cloud: "Cloud",
    settings: SkypilotBaseOrchestratorSettings,
    default_instance_type: Optional[str] = None,
    kubernetes_image: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare resources keyword arguments for sky.Resources.

    Args:
        cloud: Skypilot cloud.
        settings: Skypilot orchestrator settings.
        default_instance_type: Default instance type.
        kubernetes_image: Image to use for Kubernetes (if applicable).

    Returns:
        Resources keyword arguments dictionary.
    """
    resources_kwargs = {
        "cloud": cloud,
        "instance_type": settings.instance_type or default_instance_type,
        "cpus": settings.cpus,
        "memory": settings.memory,
        "accelerators": settings.accelerators,
        "accelerator_args": settings.accelerator_args,
        "use_spot": settings.use_spot,
        "job_recovery": settings.job_recovery,
        "region": settings.region,
        "zone": settings.zone,
        "image_id": kubernetes_image
        if kubernetes_image
        else settings.image_id,
        "disk_size": settings.disk_size,
        "disk_tier": settings.disk_tier,
        "ports": settings.ports,
        "labels": settings.labels,
        "any_of": settings.any_of,
        "ordered": settings.ordered,
        **settings.resources_settings,  # Add any arbitrary resource settings
    }

    # Remove None values to avoid overriding SkyPilot defaults
    return {k: v for k, v in resources_kwargs.items() if v is not None}


def prepare_launch_kwargs(
    settings: SkypilotBaseOrchestratorSettings,
    down: Optional[bool] = None,
    idle_minutes_to_autostop: Optional[int] = None,
) -> Dict[str, Any]:
    """Prepare launch keyword arguments for sky.launch.

    Args:
        settings: Skypilot orchestrator settings.
        down: Whether to tear down the cluster after job completion.
        idle_minutes_to_autostop: Minutes to autostop after idleness.

    Returns:
        Launch keyword arguments dictionary.
    """
    # Determine values falling back to settings where applicable
    down_value = down if down is not None else settings.down
    idle_value = (
        idle_minutes_to_autostop
        if idle_minutes_to_autostop is not None
        else settings.idle_minutes_to_autostop
    )

    # The following parameters were removed from sky.launch in versions > 0.8.
    # We therefore no longer include them in the kwargs passed to the call.
    # • stream_logs – handled by explicitly calling sky.stream_and_get
    # • detach_setup / detach_run – setup/run are now detached by default

    launch_kwargs = {
        "retry_until_up": settings.retry_until_up,
        "idle_minutes_to_autostop": idle_value,
        "down": down_value,
        "backend": None,
        **settings.launch_settings,  # Keep user-provided extras
    }

    # Remove keys that are no longer supported by sky.launch.
    for _deprecated in (
        "stream_logs",
        "detach_setup",
        "detach_run",
        "num_nodes",
    ):
        launch_kwargs.pop(_deprecated, None)

    # Remove None values to avoid overriding SkyPilot defaults
    return {k: v for k, v in launch_kwargs.items() if v is not None}


def sky_job_get(request_id: str, stream_logs: bool, cluster_name: str) -> Any:
    """Handle SkyPilot request results based on stream_logs setting.

    SkyPilot API exec and launch methods are asynchronous and return a request ID.
    This method waits for the operation to complete and returns the result.
    If stream_logs is True, it will also stream the logs and wait for the
    job to complete.

    Args:
        request_id: The request ID returned from a SkyPilot operation.
        stream_logs: Whether to stream logs while waiting for completion.
        cluster_name: The name of the cluster to tail logs for.

    Returns:
        The result of the SkyPilot operation.

    Raises:
        Exception: If the SkyPilot job fails.
    """
    if stream_logs:
        # Stream logs and wait for completion
        job_id, _ = sky.stream_and_get(request_id)
    else:
        # Just wait for completion without streaming logs
        job_id, _ = sky.get(request_id)

    status = 0  # 0=Successful, 100=Failed
    if stream_logs:
        status = sky.tail_logs(
            cluster_name=cluster_name, job_id=job_id, follow=True
        )

    if status != 0:
        raise Exception(f"SkyPilot job {job_id} failed with status {status}")

    return job_id
