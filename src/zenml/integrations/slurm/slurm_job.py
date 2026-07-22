#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Shared Slurm job-script construction for the step operator and orchestrator.

Both components run a ZenML step as a Slurm batch job: the step's Docker image
is executed on a compute node with a rootless HPC container runtime. The job
script and the per-runtime container command are identical between them, so
they are built here.

Security: the environment file holds the step's credentials (ZenML store
token, etc.). It is passed to the container via ``--env-file`` /
``--container-env`` so the values never appear on a command line visible to
other cluster users, and the job's EXIT trap scrubs it the moment the job
ends - even if the submitting process dies. All interpolated paths and values
go through ``shlex.quote``.
"""

import base64
import json
import math
import posixpath
import re
import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Tuple

from zenml.enums import StackComponentType
from zenml.integrations.slurm.flavors.base import (
    SlurmContainerRuntime,
    SlurmJobSettings,
)

if TYPE_CHECKING:
    from zenml.config.resource_settings import ResourceSettings
    from zenml.integrations.slurm.slurm_client import SlurmClient
    from zenml.stack import Stack

# Files written into a job's per-run directory on the cluster.
ENV_FILE = "env"
EXIT_CODE_FILE = "exit_code"
OUTPUT_FILE = "output.log"
SCRIPT_FILE = "job.sh"
CANCELLED_FILE = "cancelled"
DOCKER_CONFIG_DIR = "docker_config"
ENROOT_CONFIG_DIR = "enroot_config"
REGISTRY_AUTH_FILE = "registry_auth.sh"

_ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# The required stack components shared by both Slurm components.
REQUIRED_COMPONENTS = {
    StackComponentType.CONTAINER_REGISTRY,
    StackComponentType.IMAGE_BUILDER,
}


@dataclass(frozen=True)
class SlurmRegistryAuth:
    """Files and shell setup required for a private registry pull."""

    files: Dict[str, str] = field(default_factory=dict, repr=False)
    shell_setup: str = ""
    sensitive_paths: List[str] = field(default_factory=list)


def serialize_environment(
    environment: Mapping[str, str], runtime: SlurmContainerRuntime
) -> str:
    """Serialize a step environment safely for the selected runtime.

    Args:
        environment: Environment variables passed to the step.
        runtime: Container runtime that consumes the environment file.

    Returns:
        Serialized environment file content.

    Raises:
        ValueError: If an environment variable name is invalid.
    """
    for key in environment:
        if not _ENV_NAME_PATTERN.fullmatch(key):
            raise ValueError(f"Invalid environment variable name: {key!r}.")

    if runtime == SlurmContainerRuntime.PYXIS:
        return "".join(
            f"export {key}={shlex.quote(value)}\n"
            for key, value in sorted(environment.items())
        )

    from zenml.integrations.ssh.utils import serialize_env_for_docker_env_file

    return serialize_env_for_docker_env_file(environment)


def build_registry_auth(
    runtime: SlurmContainerRuntime,
    run_dir: str,
    registry_uri: Optional[str],
    credentials: Optional[Tuple[str, str]],
) -> SlurmRegistryAuth:
    """Build owner-only registry authentication files for a Slurm job.

    Args:
        runtime: Container runtime that pulls the image.
        run_dir: Per-job staging directory.
        registry_uri: Registry URI from the active stack.
        credentials: Registry username and password.

    Returns:
        Authentication files and shell setup for the selected runtime.

    Raises:
        ValueError: If an enroot registry hostname or username contains
            whitespace.
    """
    if not registry_uri or not credentials:
        return SlurmRegistryAuth()

    username, password = credentials
    if runtime == SlurmContainerRuntime.DOCKER:
        config_dir = f"{run_dir}/{DOCKER_CONFIG_DIR}"
        config_path = f"{config_dir}/config.json"
        encoded = base64.b64encode(
            f"{username}:{password}".encode("utf-8")
        ).decode("ascii")
        content = json.dumps(
            {"auths": {registry_uri: {"auth": encoded}}}, sort_keys=True
        )
        return SlurmRegistryAuth(
            files={config_path: content},
            shell_setup=f"export DOCKER_CONFIG={shlex.quote(config_dir)}\n",
            sensitive_paths=[config_dir],
        )

    if runtime == SlurmContainerRuntime.PYXIS:
        config_dir = f"{run_dir}/{ENROOT_CONFIG_DIR}"
        credentials_path = f"{config_dir}/.credentials"
        registry = registry_uri.removeprefix("https://").removeprefix(
            "http://"
        )
        registry = registry.rstrip("/").split("/", 1)[0]
        if any(character.isspace() for character in registry + username):
            raise ValueError(
                "Enroot registry hostnames and usernames cannot contain "
                "whitespace."
            )

        def _netrc_quote(value: str) -> str:
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

        # Enroot matches these fields textually to infer the registry user, so
        # only the password can use netrc quoting here.
        content = (
            f"machine {registry} "
            f"login {username} "
            f"password {_netrc_quote(password)}\n"
        )
        return SlurmRegistryAuth(
            files={credentials_path: content},
            shell_setup=f"export ENROOT_CONFIG_PATH={shlex.quote(config_dir)}\n",
            sensitive_paths=[config_dir],
        )

    auth_path = f"{run_dir}/{REGISTRY_AUTH_FILE}"
    content = "".join(
        [
            f"export APPTAINER_DOCKER_USERNAME={shlex.quote(username)}\n",
            f"export APPTAINER_DOCKER_PASSWORD={shlex.quote(password)}\n",
            f"export SINGULARITY_DOCKER_USERNAME={shlex.quote(username)}\n",
            f"export SINGULARITY_DOCKER_PASSWORD={shlex.quote(password)}\n",
        ]
    )
    return SlurmRegistryAuth(
        files={auth_path: content},
        shell_setup=f"source {shlex.quote(auth_path)}\n",
        sensitive_paths=[auth_path],
    )


def validate_remote_stack(stack: "Stack") -> Tuple[bool, str]:
    """Ensure the stack can feed a step running on a remote Slurm cluster.

    The cluster reads inputs and writes outputs to the artifact store and
    pulls the step image from the container registry, so both must be remote.

    Args:
        stack: The stack to validate.

    Returns:
        Whether the stack is valid and an error message if it is not.
    """
    if stack.artifact_store.config.is_local:
        return False, (
            "The Slurm integration runs steps on a remote cluster that must "
            "read inputs and write outputs to a shared artifact store, but "
            f"the artifact store '{stack.artifact_store.name}' is local. "
            "Please use a remote artifact store (S3, GCS, Azure Blob, etc.)."
        )

    container_registry = stack.container_registry
    assert container_registry is not None
    if container_registry.config.is_local:
        return False, (
            "The Slurm integration runs the step's image on a remote cluster, "
            "which must pull it from a registry, but the container registry "
            f"'{container_registry.name}' is local. Please use a remote "
            "container registry (ECR, GCR, ACR, DockerHub, etc.)."
        )
    return True, ""


def build_container_command(
    runtime: SlurmContainerRuntime,
    image: str,
    entrypoint_command: List[str],
    env_file: str,
    env_keys: List[str],
    use_gpu: bool,
    settings: SlurmJobSettings,
    registry_auth: Optional[SlurmRegistryAuth] = None,
) -> str:
    """Build the shell snippet that runs the step image on the node.

    Secrets are passed only via the env file (or, for pyxis, via
    ``--container-env`` variable names whose values are sourced from the 0600
    env file), never on the command line.

    Contract: the returned snippet is one self-contained foreground command
    that must stay wrappable with ``srun --nodes=N --ntasks-per-node=1`` (the
    planned multi-node mode for command steps), so it must not assume it runs
    exactly once on the batch node. The pyxis runtime already executes
    through ``srun``.

    Args:
        runtime: The container runtime to use.
        image: Fully-qualified image reference to run.
        entrypoint_command: The full step command (entrypoint + arguments).
        env_file: Path to the owner-only environment file on the cluster.
        env_keys: Names of the environment variables (for pyxis).
        use_gpu: Whether the step requested GPUs.
        settings: The resolved step settings (mounts, extra run args).
        registry_auth: Optional private-registry authentication setup.

    Returns:
        A shell snippet that runs the container in the foreground.
    """
    entrypoint = " ".join(shlex.quote(p) for p in entrypoint_command)
    extra = " ".join(shlex.quote(a) for a in settings.container_run_args)
    shell_setup = registry_auth.shell_setup if registry_auth else ""

    if runtime in (
        SlurmContainerRuntime.APPTAINER,
        SlurmContainerRuntime.SINGULARITY,
    ):
        binary = runtime.value  # "apptainer" or "singularity"
        parts = [binary, "exec", "--no-eval"]
        if use_gpu:
            parts.append("--nv")
        parts += ["--env-file", shlex.quote(env_file)]
        for host, container in settings.container_mounts.items():
            parts += ["--bind", shlex.quote(f"{host}:{container}")]
        if extra:
            parts.append(extra)
        parts.append(shlex.quote(f"docker://{image}"))
        return f"{shell_setup}{' '.join(parts)} {entrypoint}"

    if runtime == SlurmContainerRuntime.DOCKER:
        parts = ["docker", "run", "--rm"]
        if use_gpu:
            parts += ["--gpus", "all"]
        parts += ["--env-file", shlex.quote(env_file)]
        for host, container in settings.container_mounts.items():
            parts += ["-v", shlex.quote(f"{host}:{container}")]
        if extra:
            parts.append(extra)
        parts.append(shlex.quote(image))
        return f"{shell_setup}{' '.join(parts)} {entrypoint}"

    # Pyxis / enroot via srun. `--container-env` takes variable *names*; the
    # values are sourced from the 0600 env file into the job shell, so they
    # are not exposed on the command line.
    srun = ["srun", f"--container-image={shlex.quote(image)}"]
    if settings.container_mounts:
        mounts = ",".join(
            f"{host}:{container}"
            for host, container in settings.container_mounts.items()
        )
        srun.append(f"--container-mounts={shlex.quote(mounts)}")
    if env_keys:
        srun.append(f"--container-env={','.join(env_keys)}")
    if extra:
        srun.append(extra)
    source_env = f"set -a\nsource {shlex.quote(env_file)}\nset +a\n"
    return f"{shell_setup}{source_env}{' '.join(srun)} {entrypoint}"


def build_sbatch_script(
    job_name: str,
    run_dir: str,
    container_command: str,
    resources: "ResourceSettings",
    settings: SlurmJobSettings,
    sensitive_paths: Optional[List[str]] = None,
) -> str:
    """Render the sbatch job script for a step.

    Args:
        job_name: The Slurm job name.
        run_dir: The per-run staging directory on the cluster.
        container_command: The shell snippet that runs the step container.
        resources: The step's resource settings (cpu/mem/gpu).
        settings: The resolved Slurm job settings (partition, time, ...).
        sensitive_paths: Credential-bearing paths removed when the job exits.

    Returns:
        The job script content.
    """
    directives = [
        f"#SBATCH --job-name={job_name}",
        f"#SBATCH --output={run_dir}/{OUTPUT_FILE}",
    ]
    if settings.partition:
        directives.append(f"#SBATCH --partition={settings.partition}")
    if settings.time_limit:
        directives.append(f"#SBATCH --time={settings.time_limit}")
    if settings.account:
        directives.append(f"#SBATCH --account={settings.account}")
    if settings.qos:
        directives.append(f"#SBATCH --qos={settings.qos}")
    if resources.cpu_count:
        directives.append(
            f"#SBATCH --cpus-per-task={math.ceil(resources.cpu_count)}"
        )
    if memory_mb := resources.get_memory(unit="MB"):
        directives.append(f"#SBATCH --mem={math.ceil(memory_mb)}M")
    if resources.gpu_count:
        directives.append(f"#SBATCH --gres=gpu:{resources.gpu_count}")
    for directive in settings.extra_sbatch_directives:
        directives.append(f"#SBATCH {directive}")

    # The EXIT trap records the job outcome in a sentinel file that the caller
    # reads after the job leaves the queue (so no dependency on Slurm
    # accounting) and scrubs the credential-bearing env file, so secrets never
    # outlive the job even if the submitting process dies. `set -e` aborts the
    # job (with the failing code captured) if the container runtime fails.
    cleanup_paths = [f"{run_dir}/{ENV_FILE}", *(sensitive_paths or [])]
    cleanup_command = "rm -rf -- " + " ".join(
        shlex.quote(path) for path in cleanup_paths
    )
    exit_code_path = shlex.quote(f"{run_dir}/{EXIT_CODE_FILE}")

    return f"""#!/bin/bash
{chr(10).join(directives)}

cleanup() {{
    ec=$?
    trap - EXIT
    echo "$ec" > {exit_code_path}
    {cleanup_command}
    exit "$ec"
}}
trap cleanup EXIT
set -eo pipefail

{container_command}
"""


def stage_and_submit(
    client: "SlurmClient",
    run_dir: str,
    env_content: str,
    script: str,
    dependencies: Optional[List[str]] = None,
    extra_files: Optional[Dict[str, str]] = None,
) -> str:
    """Stage a job's files on the cluster and submit it.

    This owns the security-sensitive part both components share: the run
    directory is created owner-only and atomically (``mkdir -m 700``, so it is
    never briefly readable by other cluster users), the credential-bearing
    environment file is written owner-only (0600), and the job script 0700.

    Args:
        client: The Slurm client for the cluster.
        run_dir: The per-job staging directory on the cluster.
        env_content: The serialized environment file content (holds secrets).
        script: The sbatch job script content.
        dependencies: Slurm job ids this job must wait for (for DAG edges).
        extra_files: Additional owner-only files to stage for the job.

    Returns:
        The submitted Slurm job id.

    Raises:
        RuntimeError: If the run directory cannot be created on the cluster.
        Exception: Re-raised after cleaning up staged files if staging or
            submission fails.
    """
    runner = client.runner
    result = runner.run(
        f"umask 077 && mkdir -p {shlex.quote(run_dir)} && "
        f"chmod 700 {shlex.quote(run_dir)}"
    )
    if result.exit_code != 0:
        raise RuntimeError(
            f"Failed to create run directory `{run_dir}` on the cluster: "
            f"{result.stderr.strip()}"
        )

    try:
        runner.put_text(f"{run_dir}/{ENV_FILE}", env_content, mode=0o600)
        for path, content in (extra_files or {}).items():
            parent = posixpath.dirname(path)
            if parent != run_dir:
                result = runner.run(
                    f"umask 077 && mkdir -p {shlex.quote(parent)} && "
                    f"chmod 700 {shlex.quote(parent)}"
                )
                if result.exit_code != 0:
                    raise RuntimeError(
                        f"Failed to create registry auth directory `{parent}`: "
                        f"{result.stderr.strip()}"
                    )
            runner.put_text(path, content, mode=0o600)

        script_path = f"{run_dir}/{SCRIPT_FILE}"
        runner.put_text(script_path, script, mode=0o700)
        return client.submit(script_path, dependencies=dependencies)
    except Exception:
        runner.run(f"rm -rf -- {shlex.quote(run_dir)}")
        raise
