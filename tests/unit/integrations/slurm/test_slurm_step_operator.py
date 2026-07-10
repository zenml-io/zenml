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

The Slurm CLI is never invoked: all tests drive the client and step operator
through a fake in-memory command runner, so they run without a cluster.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.slurm.flavors import (
    SlurmStepOperatorConfig,
    SlurmStepOperatorFlavor,
)
from zenml.integrations.slurm.slurm_client import (
    CommandResult,
    SlurmClient,
    SlurmCommandRunner,
)
from zenml.integrations.slurm.step_operators import SlurmStepOperator


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
        self.commands: list[str] = []

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
            stdout = f"{self.queue_state}\n" if self.queue_state else ""
            return CommandResult(exit_code=0, stdout=stdout, stderr="")
        if command.startswith("scancel"):
            return CommandResult(exit_code=0, stdout="", stderr="")
        return CommandResult(exit_code=0, stdout="", stderr="")

    def put_file(self, local_path: str, remote_path: str) -> None:
        """Record a file upload.

        Args:
            local_path: Source path.
            remote_path: Destination path.
        """
        self.files[remote_path] = f"<binary from {local_path}>"

    def put_text(self, content: str, remote_path: str) -> None:
        """Record a text upload.

        Args:
            content: The text content.
            remote_path: Destination path.
        """
        self.files[remote_path] = content

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
    return SlurmStepOperator(
        name="",
        id=uuid4(),
        config=config
        or SlurmStepOperatorConfig(
            transport="local",
            workdir="/shared/zenml-runs",
            env_setup_command="source /shared/venv/bin/activate",
        ),
        flavor="slurm",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


# --- config validation --------------------------------------------------------


def test_ssh_transport_requires_connection_details():
    """The ssh transport needs hostname and username; local does not."""
    with pytest.raises(ValueError):
        SlurmStepOperatorConfig(
            transport="ssh",
            workdir="/shared/zenml-runs",
            env_setup_command="true",
        )

    # local transport without connection details is fine
    SlurmStepOperatorConfig(
        transport="local",
        workdir="/shared/zenml-runs",
        env_setup_command="true",
    )

    # ssh transport with connection details is fine
    SlurmStepOperatorConfig(
        transport="ssh",
        workdir="/shared/zenml-runs",
        env_setup_command="true",
        hostname="login.example.com",
        username="mlops",
    )


def test_flavor_identity():
    """The flavor identifier and config class are Slurm's."""
    flavor = SlurmStepOperatorFlavor()
    assert flavor.name == "slurm"
    assert flavor.display_name == "Slurm"
    assert flavor.config_class is SlurmStepOperatorConfig
    assert flavor.implementation_class is SlurmStepOperator


# --- slurm client -------------------------------------------------------------


def test_client_submit_parses_job_id():
    """`sbatch --parsable` output is parsed into a job id."""
    runner = FakeRunner()
    client = SlurmClient(runner)
    assert client.submit("/shared/job.sh") == "12345"
    assert runner.commands == ["sbatch --parsable /shared/job.sh"]


def test_client_job_state_and_cancel_use_job_name():
    """Status lookup and cancellation address the job by name."""
    runner = FakeRunner(queue_state="RUNNING")
    client = SlurmClient(runner)
    assert client.get_job_state("zenml-abc") == "RUNNING"
    client.cancel("zenml-abc")
    assert runner.commands[-1] == "scancel --name zenml-abc"


def test_client_job_state_returns_none_when_not_queued():
    """A job absent from squeue returns None (terminal, see sentinel)."""
    runner = FakeRunner(queue_state=None)
    client = SlurmClient(runner)
    assert client.get_job_state("zenml-abc") is None


# --- step operator status mapping ---------------------------------------------


class _FakeStepRun:
    """Minimal stand-in for a StepRunResponse."""

    def __init__(self) -> None:
        """Initialize with a random id."""
        self.id = uuid4()


@pytest.fixture
def operator_with_fake_runner(monkeypatch):
    """A local-transport operator whose runner is the in-memory fake."""
    operator = _build_operator()
    runner = FakeRunner()
    monkeypatch.setattr(
        operator,
        "_get_client",
        lambda: (SlurmClient(runner), runner),
    )
    return operator, runner


@pytest.mark.parametrize(
    "queue_state,expected",
    [
        ("PENDING", ExecutionStatus.QUEUED),
        ("CONFIGURING", ExecutionStatus.QUEUED),
        ("RUNNING", ExecutionStatus.RUNNING),
        ("COMPLETING", ExecutionStatus.RUNNING),
        ("CANCELLED", ExecutionStatus.CANCELLED),
        ("FAILED", ExecutionStatus.FAILED),
    ],
)
def test_get_status_maps_queue_states(
    operator_with_fake_runner, queue_state, expected
):
    """Queue states map onto ZenML execution statuses."""
    operator, runner = operator_with_fake_runner
    runner.queue_state = queue_state
    assert operator.get_status(_FakeStepRun()) is expected


def test_get_status_reads_sentinel_after_queue(operator_with_fake_runner):
    """After the job leaves the queue, the sentinel file decides the status."""
    operator, runner = operator_with_fake_runner
    step_run = _FakeStepRun()
    run_dir = operator._run_dir(step_run.id)

    runner.files[f"{run_dir}/exit_code"] = "0\n"
    assert operator.get_status(step_run) is ExecutionStatus.COMPLETED

    runner.files[f"{run_dir}/exit_code"] = "1\n"
    assert operator.get_status(step_run) is ExecutionStatus.FAILED


def test_get_status_without_queue_entry_or_sentinel_is_cancelled(
    operator_with_fake_runner,
):
    """No queue entry and no sentinel means the job was torn down early."""
    operator, runner = operator_with_fake_runner
    assert operator.get_status(_FakeStepRun()) is ExecutionStatus.CANCELLED


# --- sbatch script rendering ----------------------------------------------------


def test_sbatch_script_rendering(monkeypatch):
    """The generated script carries directives, env setup, and the command."""
    from types import SimpleNamespace

    from zenml.config.resource_settings import ResourceSettings

    operator = _build_operator()
    step_run_id = uuid4()

    fake_info = SimpleNamespace(
        step_run_id=step_run_id,
        pipeline_step_name="trainer",
        config=SimpleNamespace(
            resource_settings=ResourceSettings(
                cpu_count=4, gpu_count=2, memory="16GB"
            )
        ),
        step_run=None,
    )

    from zenml.integrations.slurm.flavors import SlurmStepOperatorSettings

    monkeypatch.setattr(
        operator,
        "get_settings",
        lambda _: SlurmStepOperatorSettings(
            partition="gpu",
            time_limit="2:00:00",
            extra_sbatch_directives=["--constraint=a100"],
        ),
    )

    script = operator._build_sbatch_script(
        info=fake_info,
        entrypoint_command=["python", "-m", "zenml.entrypoint"],
        environment={"ZENML_STORE_URL": "https://z.example.com"},
        run_dir="/shared/zenml-runs/zenml-x",
    )

    assert f"#SBATCH --job-name=zenml-{step_run_id}" in script
    assert "#SBATCH --partition=gpu" in script
    assert "#SBATCH --time=2:00:00" in script
    assert "#SBATCH --cpus-per-task=4" in script
    assert "#SBATCH --mem=16G" in script
    assert "#SBATCH --gres=gpu:2" in script
    assert "#SBATCH --constraint=a100" in script
    assert "source /shared/venv/bin/activate" in script
    assert "export ZENML_STORE_URL=https://z.example.com" in script
    assert "python -m zenml.entrypoint" in script
    assert (
        "trap 'echo $? > /shared/zenml-runs/zenml-x/exit_code' EXIT" in script
    )


# --- integration registration ---------------------------------------------------


def test_integration_registered():
    """The Slurm integration is discoverable in the registry."""
    from zenml.integrations.registry import integration_registry
    from zenml.integrations.slurm import SlurmIntegration

    integration_registry._initialize()
    assert integration_registry.integrations["slurm"] is SlurmIntegration
    flavors = {f().name for f in SlurmIntegration.flavors()}
    assert flavors == {"slurm"}
