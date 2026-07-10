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
"""Unit tests for the Slurm orchestrator.

The Slurm CLI and SSH are never invoked: the orchestrator is driven through an
in-memory fake command runner, so the tests run without a cluster.
"""

from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import StackComponentType
from zenml.integrations.slurm.flavors import (
    SlurmOrchestratorConfig,
    SlurmOrchestratorFlavor,
    SlurmOrchestratorSettings,
)
from zenml.integrations.slurm.orchestrators import SlurmOrchestrator
from zenml.integrations.slurm.orchestrators.slurm_orchestrator import (
    ENV_ZENML_SLURM_RUN_ID,
)
from zenml.integrations.slurm.slurm_client import (
    CommandResult,
    SlurmClient,
    SlurmCommandRunner,
)

SECRET_TOKEN = "super-secret-zenml-token"
IMAGE = "registry.example.com/zenml:abc123"


class FakeRunner(SlurmCommandRunner):
    """In-memory fake host that hands out incrementing job ids."""

    def __init__(self) -> None:
        """Initialize the fake."""
        self.files: Dict[str, str] = {}
        self.modes: Dict[str, int] = {}
        self.commands: List[str] = []
        self._next_job_id = 1000

    def run(self, command: str) -> CommandResult:
        """Record the command; return a fresh job id for each sbatch.

        Args:
            command: The command line.

        Returns:
            The command result.
        """
        self.commands.append(command)
        if command.startswith("sbatch"):
            job_id = str(self._next_job_id)
            self._next_job_id += 1
            return CommandResult(exit_code=0, stdout=job_id, stderr="")
        return CommandResult(exit_code=0, stdout="", stderr="")

    def put_text(
        self, remote_path: str, content: str, mode: int = 0o600
    ) -> None:
        """Record a written file and its mode.

        Args:
            remote_path: Destination path.
            content: The content written.
            mode: The file mode.
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


def _build_orchestrator(
    config: Optional[SlurmOrchestratorConfig] = None,
) -> SlurmOrchestrator:
    """Construct a Slurm orchestrator.

    Args:
        config: The config for the orchestrator.

    Returns:
        A SlurmOrchestrator instance.
    """
    return SlurmOrchestrator(
        name="",
        id=uuid4(),
        config=config
        or SlurmOrchestratorConfig(transport="local", workdir="/runs"),
        flavor="slurm",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _step(upstream: List[str], gpu: int = 0) -> SimpleNamespace:
    """Build a Step stand-in.

    Args:
        upstream: Invocation ids this step depends on.
        gpu: Number of GPUs the step requests.

    Returns:
        A namespace usable where a Step is expected.
    """
    return SimpleNamespace(
        spec=SimpleNamespace(upstream_steps=upstream),
        config=SimpleNamespace(
            resource_settings=ResourceSettings(gpu_count=gpu or None)
        ),
    )


def _snapshot(steps: Dict[str, SimpleNamespace]) -> SimpleNamespace:
    """Build a PipelineSnapshotResponse stand-in.

    Args:
        steps: The step configurations keyed by invocation id.

    Returns:
        A namespace usable where a snapshot is expected.
    """
    return SimpleNamespace(
        id=uuid4(),
        build=SimpleNamespace(
            get_image=lambda component_key, step: IMAGE,
        ),
        step_configurations=steps,
        pipeline_configuration=SimpleNamespace(name="p"),
        schedule=None,
    )


# --- flavor / config ----------------------------------------------------------


def test_flavor_identity():
    """The flavor identifier and classes are Slurm's."""
    flavor = SlurmOrchestratorFlavor()
    assert flavor.name == "slurm"
    assert flavor.config_class is SlurmOrchestratorConfig
    assert flavor.implementation_class is SlurmOrchestrator


def test_ssh_transport_requires_connection_details():
    """The ssh transport needs hostname and username; local does not."""
    with pytest.raises(ValueError):
        SlurmOrchestratorConfig(transport="ssh", workdir="/s")

    SlurmOrchestratorConfig(transport="local", workdir="/s")
    SlurmOrchestratorConfig(
        transport="ssh", workdir="/s", hostname="h", username="u"
    )


def test_orchestrator_is_remote_and_detached():
    """The orchestrator runs remotely and does not wait for completion."""
    config = SlurmOrchestratorConfig(transport="local", workdir="/s")
    assert config.is_remote is True
    assert config.is_synchronous is False


# --- run id -------------------------------------------------------------------


def test_get_orchestrator_run_id_reads_env(monkeypatch):
    """The run id comes from the injected environment variable."""
    op = _build_orchestrator()
    monkeypatch.setenv(ENV_ZENML_SLURM_RUN_ID, "the-run-id")
    assert op.get_orchestrator_run_id() == "the-run-id"


def test_get_orchestrator_run_id_raises_when_unset(monkeypatch):
    """Without the env var, the run id lookup fails loudly."""
    op = _build_orchestrator()
    monkeypatch.delenv(ENV_ZENML_SLURM_RUN_ID, raising=False)
    with pytest.raises(RuntimeError):
        op.get_orchestrator_run_id()


# --- topological ordering -----------------------------------------------------


def test_sorted_steps_is_topological():
    """Upstream steps are submitted before their dependents."""
    # Declared out of order: a dependent appears before its parent.
    steps = {
        "evaluate": _step(["train"]),
        "train": _step(["load"]),
        "load": _step([]),
    }
    order = SlurmOrchestrator._sorted_step_names(steps)
    assert order.index("load") < order.index("train")
    assert order.index("train") < order.index("evaluate")


# --- submit -------------------------------------------------------------------


def _use_fake_client(monkeypatch, runner: FakeRunner) -> None:
    """Route the orchestrator's client factory to the fake runner.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        runner: The fake runner to hand back.
    """
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".build_slurm_client",
        lambda config: SlurmClient(runner),
    )


def _placeholder_run() -> SimpleNamespace:
    """Build a PipelineRunResponse stand-in with a unique id.

    Returns:
        A namespace usable where a placeholder run is expected.
    """
    return SimpleNamespace(id=uuid4())


def _submit_two_step_dag(monkeypatch) -> "tuple[FakeRunner, str]":
    """Submit a load -> train DAG and return the fake host and run id.

    Args:
        monkeypatch: The pytest monkeypatch fixture.

    Returns:
        The fake runner recording everything the submission did, and the
        orchestrator run id (the placeholder run id).
    """
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)

    snapshot = _snapshot({"load": _step([]), "train": _step(["load"], gpu=1)})
    placeholder = _placeholder_run()
    op.submit_pipeline(
        snapshot=snapshot,
        stack=None,
        base_environment={},
        step_environments={
            "load": {"ZENML_STORE_API_KEY": SECRET_TOKEN},
            "train": {"ZENML_STORE_API_KEY": SECRET_TOKEN},
        },
        placeholder_run=placeholder,
    )
    return runner, str(placeholder.id)


def test_submit_wires_dependencies_in_topological_order(monkeypatch):
    """The dependent step's job waits on the parent's job id."""
    runner, _ = _submit_two_step_dag(monkeypatch)
    sbatch = [c for c in runner.commands if c.startswith("sbatch")]
    assert len(sbatch) == 2
    # load submitted first (job id 1000, no dependency), train second.
    assert "--dependency" not in sbatch[0]
    assert "--dependency=afterok:1000" in sbatch[1]
    assert "--kill-on-invalid-dep=yes" in sbatch[1]


def test_submit_injects_placeholder_run_id_into_step_env(monkeypatch):
    """Each step's env file carries the placeholder run id as the run id."""
    runner, run_id = _submit_two_step_dag(monkeypatch)
    env_files = [c for p, c in runner.files.items() if p.endswith("/env")]
    assert env_files
    # The run id is the placeholder run id (unique per run), not the snapshot
    # id (which repeats across runs of the same snapshot).
    assert all(
        f"{ENV_ZENML_SLURM_RUN_ID}={run_id}" in content
        for content in env_files
    )


def test_submit_uses_placeholder_run_id_for_paths(monkeypatch):
    """Staging paths are namespaced by the placeholder run id."""
    runner, run_id = _submit_two_step_dag(monkeypatch)
    assert all(f"/{run_id}/" in path for path in runner.files)


def test_submit_requires_a_placeholder_run(monkeypatch):
    """Submission without a placeholder run is rejected (no run id)."""
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()
    _use_fake_client(monkeypatch, FakeRunner())
    with pytest.raises(AssertionError):
        op.submit_pipeline(
            snapshot=_snapshot({"load": _step([])}),
            stack=None,
            base_environment={},
            step_environments={"load": {}},
            placeholder_run=None,
        )


def test_submit_rejects_scheduled_pipelines(monkeypatch):
    """The orchestrator refuses scheduled pipelines with a clear error."""
    op = _build_orchestrator()
    _use_fake_client(monkeypatch, FakeRunner())
    snapshot = _snapshot({"load": _step([])})
    snapshot.schedule = SimpleNamespace(name="daily")
    with pytest.raises(RuntimeError, match="does not support scheduled"):
        op.submit_pipeline(
            snapshot=snapshot,
            stack=None,
            base_environment={},
            step_environments={"load": {}},
            placeholder_run=_placeholder_run(),
        )


def test_submit_keeps_secrets_off_the_command_line(monkeypatch):
    """Secrets live only in the 0600 env file, never on a command line."""
    runner, _ = _submit_two_step_dag(monkeypatch)
    assert all(SECRET_TOKEN not in c for c in runner.commands)

    env_files = {p: c for p, c in runner.files.items() if p.endswith("/env")}
    assert env_files
    for path, content in env_files.items():
        assert SECRET_TOKEN in content
        assert runner.modes[path] == 0o600
    scripts = {p: m for p, m in runner.modes.items() if p.endswith("job.sh")}
    assert scripts
    assert all(mode == 0o700 for mode in scripts.values())


def test_submit_cancels_queued_jobs_on_failure(monkeypatch):
    """A mid-DAG failure cancels the jobs already queued for the run."""
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()

    class FailingRunner(FakeRunner):
        def put_text(self, remote_path, content, mode=0o600):
            # Fail while staging the second step, after the first is queued.
            if remote_path.endswith("/env") and self._next_job_id > 1000:
                raise RuntimeError("disk full")
            super().put_text(remote_path, content, mode=mode)

    runner = FailingRunner()
    _use_fake_client(monkeypatch, runner)
    snapshot = _snapshot({"load": _step([]), "train": _step(["load"])})
    with pytest.raises(RuntimeError):
        op.submit_pipeline(
            snapshot=snapshot,
            stack=None,
            base_environment={},
            step_environments={"load": {}, "train": {}},
            placeholder_run=_placeholder_run(),
        )
    assert any(c.startswith("scancel 1000") for c in runner.commands)


# --- validator ----------------------------------------------------------------


def test_validator_rejects_local_components():
    """The orchestrator needs a remote registry and artifact store."""
    op = _build_orchestrator()
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
