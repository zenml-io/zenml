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
"""Unit tests for the Slurm integration.

The Slurm CLI and SSH are never invoked: the client and step operator are
driven through an in-memory fake command runner, so the tests run without a
cluster.
"""

from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.slurm.flavors import (
    SlurmStepOperatorConfig,
    SlurmStepOperatorFlavor,
    SlurmStepOperatorSettings,
)
from zenml.integrations.slurm.slurm_client import (
    CommandResult,
    SlurmClient,
    SlurmCommandRunner,
)
from zenml.integrations.slurm.slurm_job import (
    build_container_command,
    build_registry_auth,
    build_sbatch_script,
    serialize_environment,
)
from zenml.integrations.slurm.step_operators import SlurmStepOperator
from zenml.integrations.slurm.step_operators.slurm_step_operator import (
    SLURM_JOB_ID_METADATA_KEY,
    SLURM_STATE_METADATA_KEY,
)

SECRET_TOKEN = "super-secret-zenml-token"
IMAGE = "registry.example.com/zenml:abc123"


class FakeRunner(SlurmCommandRunner):
    """In-memory fake of the Slurm submission host."""

    def __init__(
        self,
        queue_state: Optional[str] = None,
        files: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize the fake.

        Args:
            queue_state: State reported by the fake squeue, None = not queued.
            files: Initial files present on the fake host.
        """
        self.queue_state = queue_state
        self.files = files or {}
        self.modes: Dict[str, int] = {}
        self.commands: List[str] = []

    def run(self, command: str) -> CommandResult:
        """Fake command execution.

        Args:
            command: The command line.

        Returns:
            A canned result per Slurm command.
        """
        self.commands.append(command)
        if command.startswith("sbatch"):
            return CommandResult(exit_code=0, stdout="12345\n", stderr="")
        if command.startswith("squeue"):
            stdout = f"12345|{self.queue_state}\n" if self.queue_state else ""
            return CommandResult(exit_code=0, stdout=stdout, stderr="")
        return CommandResult(exit_code=0, stdout="", stderr="")

    def put_text(
        self, remote_path: str, content: str, mode: int = 0o600
    ) -> None:
        """Record a text upload with its mode.

        Args:
            remote_path: Destination path.
            content: The text content.
            mode: File permissions.
        """
        self.files[remote_path] = content
        self.modes[remote_path] = mode

    def read_text(self, remote_path: str) -> str:
        """Read a recorded file.

        Args:
            remote_path: Path to read.

        Returns:
            The recorded content.

        Raises:
            FileNotFoundError: If nothing was recorded at that path.
        """
        if remote_path not in self.files:
            raise FileNotFoundError(remote_path)
        return self.files[remote_path]


def _build_operator(
    config: Optional[SlurmStepOperatorConfig] = None,
) -> SlurmStepOperator:
    """Construct a Slurm step operator.

    Args:
        config: The config for the operator.

    Returns:
        A SlurmStepOperator instance.
    """
    return SlurmStepOperator(
        name="",
        id=uuid4(),
        config=config
        or SlurmStepOperatorConfig(
            transport="local", workdir="/shared/zenml-runs"
        ),
        flavor="slurm",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _fake_info(
    step_run_id: Optional[UUID] = None, gpu: int = 0
) -> SimpleNamespace:
    """Build a StepRunInfo stand-in.

    Args:
        step_run_id: The step run id.
        gpu: Number of GPUs the step requests.

    Returns:
        A namespace usable where StepRunInfo is expected.
    """
    return SimpleNamespace(
        step_run_id=step_run_id or uuid4(),
        pipeline_step_name="trainer",
        config=SimpleNamespace(
            resource_settings=ResourceSettings(
                cpu_count=4, gpu_count=gpu or None, memory="16GB"
            )
        ),
        step_run=SimpleNamespace(run_metadata={}),
        get_image=lambda key: IMAGE,
    )


# --- config validation --------------------------------------------------------


def test_ssh_transport_requires_connection_details():
    """The ssh transport needs hostname and username; local does not."""
    with pytest.raises(ValueError):
        SlurmStepOperatorConfig(transport="ssh", workdir="/s")

    SlurmStepOperatorConfig(transport="local", workdir="/s")
    SlurmStepOperatorConfig(
        transport="ssh", workdir="/s", hostname="h", username="u"
    )


def test_flavor_identity():
    """The flavor identifier and config class are Slurm's."""
    flavor = SlurmStepOperatorFlavor()
    assert flavor.name == "slurm"
    assert flavor.display_name == "Slurm"
    assert flavor.config_class is SlurmStepOperatorConfig
    assert flavor.implementation_class is SlurmStepOperator


def test_default_container_runtime_is_apptainer():
    """Apptainer is the default (rootless, HPC-safe)."""
    config = SlurmStepOperatorConfig(transport="local", workdir="/s")
    assert config.container_runtime.value == "apptainer"


def test_operator_config_is_remote():
    """Steps execute on the cluster, so the config is remote."""
    config = SlurmStepOperatorConfig(transport="local", workdir="/s")
    assert config.is_remote is True


# --- validator ----------------------------------------------------------------


def test_validator_requires_remote_registry_and_artifact_store():
    """The operator needs a remote registry, image builder, artifact store."""
    op = _build_operator()
    validator = op.validator
    assert validator is not None
    assert validator._required_components == {
        StackComponentType.CONTAINER_REGISTRY,
        StackComponentType.IMAGE_BUILDER,
    }
    check = validator._custom_validation_function
    assert check is not None

    def _stack(artifact_local: bool, registry_local: bool) -> SimpleNamespace:
        return SimpleNamespace(
            artifact_store=SimpleNamespace(
                name="a", config=SimpleNamespace(is_local=artifact_local)
            ),
            container_registry=SimpleNamespace(
                name="r", config=SimpleNamespace(is_local=registry_local)
            ),
        )

    assert check(_stack(True, False))[0] is False
    assert check(_stack(False, True))[0] is False
    assert check(_stack(False, False)) == (True, "")


# --- slurm client -------------------------------------------------------------


def test_client_submit_parses_job_id():
    """`sbatch --parsable` output is parsed into a job id."""
    runner = FakeRunner()
    assert SlurmClient(runner).submit("/s/job.sh") == "12345"
    assert runner.commands == ["sbatch --parsable /s/job.sh"]


def test_client_state_and_cancel_use_job_id():
    """Status lookup and cancellation address the exact job ID."""
    runner = FakeRunner(queue_state="RUNNING")
    client = SlurmClient(runner)
    assert client.get_job_state("12345") == "RUNNING"
    client.cancel("12345")
    assert runner.commands[-1] == "scancel 12345"


def test_client_batches_job_state_lookup():
    """Multiple job states are fetched with one squeue call."""

    class BatchRunner(FakeRunner):
        def run(self, command: str) -> CommandResult:
            self.commands.append(command)
            if (
                command.startswith("squeue --noheader")
                and "--states=all" in command
            ):
                return CommandResult(
                    exit_code=0,
                    stdout="34567|COMPLETED\n45678|FAILED\n",
                    stderr="",
                )
            if command.startswith("squeue"):
                return CommandResult(
                    exit_code=0,
                    stdout="12345|RUNNING\n23456|PENDING\n",
                    stderr="",
                )
            return CommandResult(exit_code=0, stdout="", stderr="")

    runner = BatchRunner()
    states = SlurmClient(runner).get_job_states(
        ["12345", "23456", "34567", "45678"]
    )

    assert states == {
        "12345": "RUNNING",
        "23456": "PENDING",
        "34567": "COMPLETED",
        "45678": "FAILED",
    }
    assert runner.commands == [
        "squeue --noheader --format='%i|%T' --jobs=12345,23456,34567,45678",
        "squeue --noheader --format='%i|%T' --states=all --jobs=34567,45678",
    ]


# --- container command rendering (per runtime) --------------------------------


def _container_cmd(runtime: str, gpu: bool = False) -> str:
    config = SlurmStepOperatorConfig(
        transport="local", workdir="/s", container_runtime=runtime
    )
    return build_container_command(
        runtime=config.container_runtime,
        image=IMAGE,
        entrypoint_command=["python", "-m", "zenml.entrypoint"],
        env_file="/s/zenml-x/env",
        env_keys=["ZENML_STORE_API_KEY", "ZENML_STORE_URL"],
        use_gpu=gpu,
        settings=SlurmStepOperatorSettings(
            container_mounts={"/scratch": "/scratch"}
        ),
    )


def test_apptainer_command():
    """Apptainer exec pulls the docker image and passes the env file."""
    cmd = _container_cmd("apptainer", gpu=True)
    assert cmd.startswith("apptainer exec --no-eval")
    assert "--nv" in cmd
    assert "--env-file" in cmd and "/s/zenml-x/env" in cmd
    assert "docker://registry.example.com/zenml:abc123" in cmd
    assert "--bind" in cmd and "/scratch:/scratch" in cmd
    assert "python -m zenml.entrypoint" in cmd


def test_docker_command():
    """The docker runtime runs a foreground --rm container with the env file."""
    cmd = _container_cmd("docker", gpu=True)
    assert cmd.startswith("docker run --rm")
    assert "--gpus all" in cmd
    assert "--env-file" in cmd and "/s/zenml-x/env" in cmd
    assert "-v" in cmd and "/scratch:/scratch" in cmd


def test_pyxis_command_passes_env_names_not_values():
    """Pyxis sources the env file and passes only variable names to srun."""
    cmd = _container_cmd("pyxis")
    assert "srun --container-image=" in cmd
    assert "--container-env=ZENML_STORE_API_KEY,ZENML_STORE_URL" in cmd
    assert "source /s/zenml-x/env" in cmd
    assert "--container-mounts=/scratch:/scratch" in cmd


def test_pyxis_environment_is_shell_escaped():
    """Pyxis can source values without executing shell substitutions."""
    content = serialize_environment(
        {"TOKEN": "value with spaces $(touch /tmp/unsafe)"},
        runtime=SlurmStepOperatorConfig(
            transport="local", workdir="/s", container_runtime="pyxis"
        ).container_runtime,
    )
    assert content == "export TOKEN='value with spaces $(touch /tmp/unsafe)'\n"


@pytest.mark.parametrize(
    "runtime", ["apptainer", "singularity", "pyxis", "docker"]
)
def test_registry_auth_keeps_password_out_of_shell_command(runtime):
    """Runtime-specific registry auth is staged instead of passed in argv."""
    config = SlurmStepOperatorConfig(
        transport="local", workdir="/s", container_runtime=runtime
    )
    auth = build_registry_auth(
        runtime=config.container_runtime,
        run_dir="/s/run",
        registry_uri="registry.example.com",
        credentials=("user", SECRET_TOKEN),
    )
    assert auth.files
    assert SECRET_TOKEN not in auth.shell_setup
    if runtime == "docker":
        assert all(
            SECRET_TOKEN not in content for content in auth.files.values()
        )
    else:
        assert any(SECRET_TOKEN in content for content in auth.files.values())


# --- sbatch script ------------------------------------------------------------


def test_sbatch_script_directives_and_scrub():
    """The script carries directives, fails fast, and scrubs the env file."""
    sid = uuid4()
    script = build_sbatch_script(
        job_name=f"zenml-{sid}",
        run_dir="/s/zenml-x",
        container_command="RUN_THE_CONTAINER",
        resources=ResourceSettings(cpu_count=4, gpu_count=2, memory="16GB"),
        settings=SlurmStepOperatorSettings(
            partition="gpu", time_limit="2:00:00"
        ),
    )
    assert f"#SBATCH --job-name=zenml-{sid}" in script
    assert "#SBATCH --partition=gpu" in script
    assert "#SBATCH --gres=gpu:2" in script
    assert "#SBATCH --mem=16000M" in script
    assert "set -eo pipefail" in script
    assert "RUN_THE_CONTAINER" in script
    # the EXIT trap records the outcome AND scrubs the credential env file
    assert 'echo "$ec" > /s/zenml-x/exit_code' in script
    assert "rm -rf -- /s/zenml-x/env" in script


def test_sbatch_resources_round_up():
    """Fractional CPUs and sub-GB memory never become zero requests."""
    script = build_sbatch_script(
        job_name="zenml-small",
        run_dir="/s/small",
        container_command="true",
        resources=ResourceSettings(cpu_count=0.5, memory="500MB"),
        settings=SlurmStepOperatorSettings(),
    )
    assert "#SBATCH --cpus-per-task=1" in script
    assert "#SBATCH --mem=500M" in script


# --- submit: security-sensitive handling --------------------------------------


def test_submit_writes_secret_env_file_owner_only(monkeypatch):
    """The env file is written 0600, the script 0700, and no secret leaks."""
    op = _build_operator()
    op.get_settings = lambda _i: SlurmStepOperatorSettings()
    runner = FakeRunner()
    monkeypatch.setattr(
        "zenml.integrations.slurm.step_operators.slurm_step_operator"
        ".build_slurm_client",
        lambda config: SlurmClient(runner),
    )
    monkeypatch.setattr(
        "zenml.integrations.slurm.step_operators.slurm_step_operator"
        ".publish_step_run_metadata",
        lambda **kwargs: None,
    )
    fake_registry = SimpleNamespace(
        config=SimpleNamespace(uri="registry.example.com"),
        credentials=("registry-user", "registry-password"),
    )
    monkeypatch.setattr(
        "zenml.client.Client",
        lambda: SimpleNamespace(
            active_stack=SimpleNamespace(container_registry=fake_registry)
        ),
    )

    sid = uuid4()
    info = _fake_info(sid)
    op.submit(
        info=info,
        entrypoint_command=["python", "-m", "zenml.entrypoint"],
        environment={
            "ZENML_STORE_API_KEY": SECRET_TOKEN,
            "ZENML_STORE_URL": "https://z.example.com",
        },
    )
    run_dir = f"/shared/zenml-runs/zenml-{sid}"

    # env file present, contains the secret, and is owner-only
    assert runner.modes[f"{run_dir}/env"] == 0o600
    assert SECRET_TOKEN in runner.files[f"{run_dir}/env"]
    auth_path = f"{run_dir}/registry_auth.sh"
    assert runner.modes[auth_path] == 0o600
    assert "registry-password" in runner.files[auth_path]

    # the run directory is created owner-only
    assert any("chmod 700" in c for c in runner.commands)
    # the job script is written owner-only
    assert runner.modes[f"{run_dir}/job.sh"] == 0o700

    # the secret value is NOT baked into the job script (only the env-file ref)
    assert SECRET_TOKEN not in runner.files[f"{run_dir}/job.sh"]
    assert "registry-password" not in runner.files[f"{run_dir}/job.sh"]
    # the secret value is NOT on any command line issued to the host
    assert all(SECRET_TOKEN not in c for c in runner.commands)
    assert all("registry-password" not in c for c in runner.commands)
    assert info.step_run.run_metadata[SLURM_JOB_ID_METADATA_KEY] == "12345"


# --- status mapping -----------------------------------------------------------


@pytest.fixture
def op_and_runner(monkeypatch):
    """A local operator whose runner is the in-memory fake."""
    op = _build_operator()
    runner = FakeRunner()
    monkeypatch.setattr(
        "zenml.integrations.slurm.step_operators.slurm_step_operator"
        ".build_slurm_client",
        lambda config: SlurmClient(runner),
    )
    monkeypatch.setattr(
        "zenml.integrations.slurm.step_operators.slurm_step_operator"
        ".publish_step_run_metadata",
        lambda **kwargs: None,
    )
    return op, runner


@pytest.mark.parametrize(
    "queue_state,expected",
    [
        ("PENDING", ExecutionStatus.QUEUED),
        ("RUNNING", ExecutionStatus.RUNNING),
        ("CANCELLED", ExecutionStatus.CANCELLED),
        ("FAILED", ExecutionStatus.FAILED),
    ],
)
def test_get_status_maps_queue_states(op_and_runner, queue_state, expected):
    """Queue states map onto ZenML execution statuses."""
    op, runner = op_and_runner
    runner.queue_state = queue_state
    assert (
        op.get_status(
            SimpleNamespace(
                id=uuid4(),
                run_metadata={SLURM_JOB_ID_METADATA_KEY: "12345"},
            )
        )
        is expected
    )


def test_get_status_reads_sentinel_after_queue(op_and_runner):
    """After the job leaves the queue, the sentinel file decides the status."""
    op, runner = op_and_runner
    step_run = SimpleNamespace(
        id=uuid4(), run_metadata={SLURM_JOB_ID_METADATA_KEY: "12345"}
    )
    run_dir = op._run_dir(step_run.id)
    runner.files[f"{run_dir}/exit_code"] = "0\n"
    assert op.get_status(step_run) is ExecutionStatus.COMPLETED
    runner.files[f"{run_dir}/exit_code"] = "1\n"
    assert op.get_status(step_run) is ExecutionStatus.FAILED


def test_get_status_without_queue_or_sentinel_fails(op_and_runner):
    """A vanished job without a sentinel is treated as failed."""
    op, runner = op_and_runner
    assert (
        op.get_status(
            SimpleNamespace(
                id=uuid4(),
                run_metadata={SLURM_JOB_ID_METADATA_KEY: "12345"},
            )
        )
        is ExecutionStatus.FAILED
    )


def test_get_status_publishes_raw_terminal_state(op_and_runner, monkeypatch):
    """Scheduler-observed terminal states land in step metadata exactly once.

    A scheduler kill (TIMEOUT, NODE_FAIL, OOM, PREEMPTED) leaves no exit-code
    sentinel; the raw state is the only record of why the step failed.
    """
    op, runner = op_and_runner
    published = []
    monkeypatch.setattr(
        "zenml.integrations.slurm.step_operators.slurm_step_operator"
        ".publish_step_run_metadata",
        lambda **kwargs: published.append(kwargs),
    )
    step_run = SimpleNamespace(
        id=uuid4(), run_metadata={SLURM_JOB_ID_METADATA_KEY: "12345"}
    )
    runner.queue_state = "TIMEOUT"

    assert op.get_status(step_run) is ExecutionStatus.FAILED
    assert published == [
        {
            "step_run_id": step_run.id,
            "step_run_metadata": {
                op.id: {SLURM_STATE_METADATA_KEY: "TIMEOUT"}
            },
        }
    ]

    # A state already recorded on the step run is not re-published.
    step_run.run_metadata[SLURM_STATE_METADATA_KEY] = "TIMEOUT"
    assert op.get_status(step_run) is ExecutionStatus.FAILED
    assert len(published) == 1


def test_get_status_reads_cancelled_marker(op_and_runner):
    """A cancelled-before-start marker produces a terminal status."""
    op, runner = op_and_runner
    step_run = SimpleNamespace(
        id=uuid4(), run_metadata={SLURM_JOB_ID_METADATA_KEY: "12345"}
    )
    run_dir = op._run_dir(step_run.id)
    runner.files[f"{run_dir}/cancelled"] = "1\n"

    assert op.get_status(step_run) is ExecutionStatus.CANCELLED


def test_cleanup_removes_run_dir(op_and_runner):
    """Cleanup removes the whole per-run directory."""
    op, runner = op_and_runner
    step_run = SimpleNamespace(id=uuid4())
    op.cleanup_step_submission(step_run)
    run_dir = op._run_dir(step_run.id)
    assert any(f"rm -rf -- {run_dir}" in c for c in runner.commands)


# --- integration registration -------------------------------------------------


def test_integration_registered():
    """The Slurm integration is discoverable in the registry."""
    from zenml.integrations.registry import integration_registry
    from zenml.integrations.slurm import SlurmIntegration

    integration_registry._initialize()
    assert integration_registry.integrations["slurm"] is SlurmIntegration
    assert {f().name for f in SlurmIntegration.flavors()} == {"slurm"}
